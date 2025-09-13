"""Fast response optimization service."""

import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

from .advanced_cache import advanced_cache
from .rate_limiter import rate_limiter
from core.models import Context, QueryResponse


@dataclass
class ResponseMetrics:
    """Response performance metrics."""
    total_time: float
    cache_hit: bool
    cache_level: str
    context_retrieval_time: float
    llm_generation_time: float
    cache_storage_time: float


class FastResponseOptimizer:
    """Optimizes response generation for maximum speed."""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.response_cache = {}
        self.similarity_cache = {}
        
        # Performance thresholds
        self.fast_response_threshold = 1.0  # 1 second
        self.cache_boost_threshold = 0.5    # 0.5 seconds
        
        # Pre-computed responses for common queries
        self.common_responses = {
            "tell me about this project": "project_overview",
            "what is this project": "project_overview", 
            "how does this work": "how_it_works",
            "what technologies are used": "technologies",
            "how to run this": "setup_instructions"
        }
    
    async def optimize_query_response(self, question: str, session_id: str, 
                                    contexts: List[Context]) -> Tuple[QueryResponse, ResponseMetrics]:
        """Optimize query response for maximum speed."""
        start_time = time.time()
        metrics = ResponseMetrics(
            total_time=0,
            cache_hit=False,
            cache_level="none",
            context_retrieval_time=0,
            llm_generation_time=0,
            cache_storage_time=0
        )
        
        try:
            # Check for ultra-fast cached response
            cached_response = await self._get_ultra_fast_cache(question, session_id)
            if cached_response:
                metrics.cache_hit = True
                metrics.cache_level = "ultra_fast"
                metrics.total_time = time.time() - start_time
                return cached_response, metrics
            
            # Check for similar cached responses
            similar_response = await self._get_similar_cached_response(question, session_id)
            if similar_response:
                metrics.cache_hit = True
                metrics.cache_level = "similar"
                metrics.total_time = time.time() - start_time
                return similar_response, metrics
            
            # Generate optimized response
            response = await self._generate_optimized_response(question, contexts, session_id, metrics)
            
            # Cache the response for future use
            cache_start = time.time()
            await self._cache_response(question, response, session_id)
            metrics.cache_storage_time = time.time() - cache_start
            
            metrics.total_time = time.time() - start_time
            return response, metrics
            
        except Exception as e:
            # Fallback to basic response
            print(f"⚠️ Fast response optimization failed: {e}")
            return await self._fallback_response(question, contexts, session_id, metrics)
    
    async def _get_ultra_fast_cache(self, question: str, session_id: str) -> Optional[QueryResponse]:
        """Get ultra-fast cached response (exact match)."""
        # Check L1 cache first
        cached = advanced_cache.get("query_response", session_id, question)
        if cached:
            return QueryResponse(**cached)
        
        # Check session cache
        cached = advanced_cache.get_session(session_id, "query_response", question)
        if cached:
            return QueryResponse(**cached)
        
        return None
    
    async def _get_similar_cached_response(self, question: str, session_id: str) -> Optional[QueryResponse]:
        """Get similar cached response for common question patterns."""
        question_lower = question.lower().strip()
        
        # Check for common question patterns
        for pattern, cache_key in self.common_responses.items():
            if pattern in question_lower:
                cached = advanced_cache.get("common_response", session_id, cache_key)
                if cached:
                    # Customize the response slightly
                    response = QueryResponse(**cached)
                    response.answer = self._customize_common_response(response.answer, question)
                    return response
        
        return None
    
    def _customize_common_response(self, base_answer: str, question: str) -> str:
        """Customize common response based on specific question."""
        # Simple customization - in production, use more sophisticated NLP
        if "how to run" in question.lower():
            return base_answer.replace("This project", "To run this project")
        elif "technologies" in question.lower():
            return base_answer.replace("This project", "The technologies used in this project")
        
        return base_answer
    
    async def _generate_optimized_response(self, question: str, contexts: List[Context], 
                                         session_id: str, metrics: ResponseMetrics) -> QueryResponse:
        """Generate response with speed optimizations."""
        # Use parallel processing for context analysis
        context_start = time.time()
        
        # Analyze contexts in parallel
        context_tasks = [
            self._analyze_context_async(ctx) for ctx in contexts[:5]  # Limit to top 5
        ]
        analyzed_contexts = await asyncio.gather(*context_tasks, return_exceptions=True)
        
        metrics.context_retrieval_time = time.time() - context_start
        
        # Generate response with optimized prompt (pass full contexts)
        llm_start = time.time()
        response = await self._generate_fast_llm_response(question, contexts, analyzed_contexts, session_id)
        metrics.llm_generation_time = time.time() - llm_start
        
        return response
    
    async def _analyze_context_async(self, context: Context) -> Dict[str, Any]:
        """Analyze context asynchronously."""
        # Run CPU-intensive analysis in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._analyze_context_sync,
            context
        )
    
    def _analyze_context_sync(self, context: Context) -> Dict[str, Any]:
        """Synchronous context analysis."""
        return {
            "file_path": context.file_path,
            "relevance_score": context.similarity_score,
            "content_length": len(context.content),
            "has_code": "```" in context.content or "def " in context.content,
            "has_config": any(ext in context.file_path for ext in [".yml", ".json", ".env"]),
            "is_documentation": any(ext in context.file_path for ext in [".md", ".txt", "README"])
        }
    
    async def _generate_fast_llm_response(self, question: str, contexts: List[Context], 
                                        analyzed_contexts: List[Dict], session_id: str) -> QueryResponse:
        """Generate LLM response with speed optimizations."""
        # Use optimized prompt for faster generation
        optimized_prompt = self._create_optimized_prompt(question, contexts, analyzed_contexts)
        
        # Use faster LLM parameters
        from openai import OpenAI
        from core.config import settings
        
        client = OpenAI(api_key=settings.openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert code analyst. Provide comprehensive, detailed answers based on the provided code context."},
                {"role": "user", "content": optimized_prompt}
            ],
            max_tokens=1000,  # Increased for better responses
            temperature=0.1,
            top_p=0.8,       # Faster generation
            stream=False
        )
        
        answer = response.choices[0].message.content
        
        # Create response with optimized sources
        sources = self._create_optimized_sources(analyzed_contexts)
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            confidence="high" if len(analyzed_contexts) > 2 else "medium"
        )
    
    def _create_optimized_prompt(self, question: str, contexts: List[Context], analyzed_contexts: List[Dict]) -> str:
        """Create optimized prompt for faster LLM response."""
        # Prioritize high-relevance contexts
        high_relevance = [ctx for ctx in analyzed_contexts if ctx["relevance_score"] > 0.7]
        medium_relevance = [ctx for ctx in analyzed_contexts if 0.4 <= ctx["relevance_score"] <= 0.7]
        
        prompt_parts = [f"Question: {question}\n"]
        
        # Add actual content from high-relevance contexts
        if high_relevance:
            prompt_parts.append("High relevance context:")
            for i, ctx in enumerate(high_relevance[:3]):  # Limit to top 3
                # Find the corresponding full context
                full_context = next((c for c in contexts if c.file_path == ctx['file_path']), None)
                if full_context:
                    prompt_parts.append(f"\n**Context {i+1} - {ctx['file_path']}:**")
                    prompt_parts.append(f"```{ctx['file_path'].split('.')[-1] if '.' in ctx['file_path'] else 'text'}")
                    prompt_parts.append(full_context.content[:800])  # Limit content length
                    prompt_parts.append("```")
        
        # Add medium relevance contexts if needed
        if medium_relevance and len(high_relevance) < 3:
            prompt_parts.append("\nAdditional context:")
            for i, ctx in enumerate(medium_relevance[:2]):  # Limit to top 2
                full_context = next((c for c in contexts if c.file_path == ctx['file_path']), None)
                if full_context:
                    prompt_parts.append(f"\n**Context {i+1} - {ctx['file_path']}:**")
                    prompt_parts.append(f"```{ctx['file_path'].split('.')[-1] if '.' in ctx['file_path'] else 'text'}")
                    prompt_parts.append(full_context.content[:600])  # Shorter for medium relevance
                    prompt_parts.append("```")
        
        prompt_parts.append("\nProvide a comprehensive answer based on the provided code context. Include specific file references and code snippets when relevant.")
        
        return "\n".join(prompt_parts)
    
    def _create_optimized_sources(self, analyzed_contexts: List[Dict]) -> List[Dict]:
        """Create optimized source references."""
        sources = []
        for ctx in analyzed_contexts[:3]:  # Limit to top 3 sources
            sources.append({
                "file": ctx["file_path"],
                "snippet": f"Relevance: {ctx['relevance_score']:.2f}",
                "line_start": 0,
                "line_end": 0
            })
        return sources
    
    async def _cache_response(self, question: str, response: QueryResponse, session_id: str):
        """Cache response for future use."""
        # Cache in multiple levels
        response_data = response.dict()
        
        # L1 cache (fastest)
        advanced_cache.set("query_response", response_data, session_id, question)
        
        # Session cache
        advanced_cache.set_session(session_id, "query_response", response_data, question)
        
        # Cache similar responses for common patterns
        question_lower = question.lower().strip()
        for pattern, cache_key in self.common_responses.items():
            if pattern in question_lower:
                advanced_cache.set("common_response", response_data, session_id, cache_key)
                break
    
    async def _fallback_response(self, question: str, contexts: List[Context], 
                               session_id: str, metrics: ResponseMetrics) -> QueryResponse:
        """Fallback response when optimization fails."""
        # Simple fallback response
        if contexts:
            file_list = [ctx.file_path for ctx in contexts[:3]]
            answer = f"Based on the codebase, I found relevant information in: {', '.join(file_list)}. "
            answer += "The system is currently optimizing responses for better performance."
        else:
            answer = "I'm working on optimizing the response system. Please try again in a moment."
        
        return QueryResponse(
            answer=answer,
            sources=[],
            confidence="low"
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        cache_stats = advanced_cache.get_stats()
        
        return {
            "cache_performance": cache_stats,
            "response_thresholds": {
                "fast_response": self.fast_response_threshold,
                "cache_boost": self.cache_boost_threshold
            },
            "common_responses_cached": len(self.common_responses)
        }


# Global fast response optimizer
fast_response_optimizer = FastResponseOptimizer()
