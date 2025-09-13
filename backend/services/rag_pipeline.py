"""RAG pipeline service for GitSleuth."""

from typing import List, Dict, Any
from openai import OpenAI

from core.config import settings
from core.models import Context, SourceReference, QueryResponse
from core.exceptions import LLMError, QueryError
from .embedding_service import EmbeddingService
from .vector_store import VectorStore


class RAGPipeline:
    """Handles RAG pipeline for question answering."""
    
    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.llm_client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4"
    
    def retrieve_context(self, query: str, session_id: str, top_k: int = None) -> List[Context]:
        """
        Retrieve relevant context for a query with enhanced project understanding.
        
        Args:
            query: User question
            session_id: Session identifier
            top_k: Number of contexts to retrieve
            
        Returns:
            List of relevant contexts
        """
        try:
            if top_k is None:
                top_k = settings.max_context_chunks
            
            # Create query embedding
            query_embedding = self.embedding_service.create_single_embedding(query)
            
            # Analyze query type for better context retrieval
            query_lower = query.lower()
            is_general_question = any(phrase in query_lower for phrase in [
                "tell me about this project", "what is this project", "describe this project",
                "overview", "summary", "what does this do", "explain this codebase",
                "how does this work", "what is this application", "about this project"
            ])
            
            if is_general_question:
                print(f"🔧 Detected general project question, retrieving comprehensive context")
                # For general questions, get more diverse contexts with lower threshold
                contexts = self.vector_store.search_similar(
                    session_id=session_id,
                    query_embedding=query_embedding,
                    top_k=min(top_k * 3, 20),  # Get more chunks for comprehensive overview
                    threshold=0.05,  # Very low threshold to get diverse content
                    exclude_files=["test", "spec", "__pycache__", "node_modules", ".git"]
                )
                
                # Prioritize important files for project overview
                important_files = ['readme', 'package.json', 'requirements.txt', 'docker', 'config', 'main', 'app', 'index']
                prioritized_contexts = []
                other_contexts = []
                
                for context in contexts:
                    if any(important in context.file_path.lower() for important in important_files):
                        prioritized_contexts.append(context)
                    else:
                        other_contexts.append(context)
                
                # Combine prioritized and other contexts
                final_contexts = prioritized_contexts + other_contexts
                print(f"🔧 Retrieved {len(final_contexts)} contexts for general question (prioritized: {len(prioritized_contexts)})")
                return final_contexts[:top_k * 2]  # Return more contexts for general questions
            else:
                # For specific questions, use normal search
                contexts = self.vector_store.search_similar(
                    session_id=session_id,
                    query_embedding=query_embedding,
                    top_k=top_k,
                    threshold=settings.similarity_threshold
                )
                print(f"🔧 Retrieved {len(contexts)} contexts for specific question")
                return contexts
            
        except Exception as e:
            raise QueryError(f"Failed to retrieve context: {e}")
    
    def generate_prompt(self, query: str, contexts: List[Context]) -> str:
        """
        Generate a comprehensive prompt for the LLM with enhanced context formatting.
        
        Args:
            query: User question
            contexts: Retrieved contexts
            
        Returns:
            Formatted prompt
        """
        # Analyze query type for better prompt customization
        query_lower = query.lower()
        is_general_question = any(phrase in query_lower for phrase in [
            "tell me about this project", "what is this project", "describe this project",
            "overview", "summary", "what does this do", "explain this codebase",
            "how does this work", "what is this application", "about this project"
        ])
        
        # Format contexts with enhanced metadata and organization
        formatted_contexts = []
        context_categories = {
            "documentation": [],
            "configuration": [],
            "source_code": [],
            "other": []
        }
        
        for i, context in enumerate(contexts, 1):
            file_ext = context.file_path.split('.')[-1].lower() if '.' in context.file_path else 'text'
            file_name = context.file_path.split('/')[-1].split('\\')[-1]  # Get just filename
            
            # Categorize contexts
            if file_ext in ['md', 'txt', 'readme']:
                category = "documentation"
            elif file_ext in ['json', 'yml', 'yaml', 'env', 'config', 'ini', 'toml']:
                category = "configuration"
            elif file_ext in ['py', 'js', 'ts', 'jsx', 'tsx', 'java', 'go', 'rs', 'cpp', 'c', 'cs', 'php', 'rb']:
                category = "source_code"
            else:
                category = "other"
            
            # Enhanced context formatting
            relevance_indicator = "🔥" if context.similarity_score > 0.8 else "⭐" if context.similarity_score > 0.6 else "📄"
            
            context_text = f"""
{relevance_indicator} **{file_name}** (lines {context.start_line}-{context.end_line})
**Path:** `{context.file_path}`
**Relevance:** {context.similarity_score:.3f}
**Type:** {file_ext.upper()}

```{file_ext}
{context.content}
```
"""
            context_categories[category].append(context_text)
        
        # Organize contexts by category
        organized_contexts = []
        if context_categories["documentation"]:
            organized_contexts.append("## 📚 DOCUMENTATION & README FILES\n" + "\n".join(context_categories["documentation"]))
        if context_categories["configuration"]:
            organized_contexts.append("## ⚙️ CONFIGURATION FILES\n" + "\n".join(context_categories["configuration"]))
        if context_categories["source_code"]:
            organized_contexts.append("## 💻 SOURCE CODE\n" + "\n".join(context_categories["source_code"]))
        if context_categories["other"]:
            organized_contexts.append("## 📄 OTHER FILES\n" + "\n".join(context_categories["other"]))
        
        # Create dynamic system prompt based on query type
        if is_general_question:
            system_prompt = """You are an expert software engineer and project analyst. Your task is to provide a comprehensive overview of this project based on the provided code context.

## FOR PROJECT OVERVIEW QUESTIONS:
- Provide a detailed analysis of the project's purpose, architecture, and functionality
- Identify the main technologies, frameworks, and tools used
- Explain the project structure and how components interact
- Highlight key features, configuration, and deployment setup
- Mention any important dependencies, APIs, or external services
- Include specific file references and code examples when relevant

## RESPONSE REQUIREMENTS:
1. **Comprehensive Analysis**: Cover all major aspects of the project
2. **Technology Stack**: Identify and explain all technologies used
3. **Architecture Overview**: Explain the overall structure and design
4. **Key Features**: Highlight main functionality and capabilities
5. **Setup & Deployment**: Explain how to run and deploy the project
6. **Specific References**: Include file paths, line numbers, and code snippets
7. **Professional Formatting**: Use clear structure with headers and bullet points

## FORMAT YOUR RESPONSE AS:
- **Project Overview**: Brief description of what the project does
- **Technology Stack**: List of technologies, frameworks, and tools
- **Architecture**: How the project is structured and organized
- **Key Features**: Main functionality and capabilities
- **Setup & Configuration**: How to run and configure the project
- **File Structure**: Important files and their purposes"""
        else:
            system_prompt = """You are an expert code analyst and software engineer. Your task is to answer specific questions about codebases based ONLY on the provided code context.

## CORE PRINCIPLES:
1. **EVIDENCE-BASED**: Answer based ONLY on the provided code context
2. **PRECISE**: Provide specific references to files, functions, classes, and line numbers
3. **COMPREHENSIVE**: Be thorough but concise in your explanations
4. **STRUCTURED**: Use clear formatting and logical organization
5. **HONEST**: If context is insufficient, clearly state what's missing

## RESPONSE FORMAT:
- **Direct Answer**: Start with a clear, direct response to the question
- **Evidence**: Provide specific code references with file paths and line numbers
- **Explanation**: Explain the logic, relationships, and implications
- **Context**: Include relevant code snippets when helpful
- **Limitations**: Mention any gaps in the provided context"""
        
        user_prompt = f"""## QUESTION:
{query}

## PROVIDED CODE CONTEXT:
{chr(10).join(organized_contexts)}

## INSTRUCTIONS:
Please analyze the provided code context and provide a comprehensive answer to the question. Focus on the most relevant contexts (🔥) but consider all provided information. Be specific about file locations, line numbers, and code relationships."""

        return f"{system_prompt}\n\n{user_prompt}"
    
    def synthesize_answer(self, prompt: str) -> QueryResponse:
        """
        Generate a comprehensive answer using the LLM with optimized parameters.
        
        Args:
            prompt: Formatted prompt for the LLM
            
        Returns:
            QueryResponse with answer and sources
        """
        try:
            # Determine if this is a general question for token optimization
            is_general_question = any(phrase in prompt.lower() for phrase in [
                "tell me about this project", "what is this project", "describe this project",
                "overview", "summary", "what does this do", "explain this codebase"
            ])
            
            # Optimize parameters based on question type
            max_tokens = 1500 if is_general_question else 1200  # More tokens for comprehensive overviews
            temperature = 0.1  # Low temperature for consistent, factual responses
            top_p = 0.9  # Good balance between creativity and consistency
            
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert software engineer and project analyst with deep knowledge of modern development practices, frameworks, and architectures."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p
            )
            
            answer = response.choices[0].message.content
            
            # Extract sources from the answer (simplified approach)
            sources = self._extract_sources_from_answer(answer)
            
            # Determine confidence based on answer content
            confidence = self._determine_confidence(answer)
            
            return QueryResponse(
                answer=answer,
                sources=sources,
                confidence=confidence
            )
            
        except Exception as e:
            raise LLMError(f"Failed to generate answer: {e}")
    
    def query(self, question: str, session_id: str) -> QueryResponse:
        """
        Complete RAG pipeline for answering a question.
        
        Args:
            question: User question
            session_id: Session identifier
            
        Returns:
            QueryResponse with answer and sources
        """
        try:
            # Retrieve relevant context
            contexts = self.retrieve_context(question, session_id)
            
            if not contexts:
                return QueryResponse(
                    answer="I couldn't find any relevant code context to answer your question. The repository might not contain information related to your query, or the indexing might not have captured the relevant files.",
                    sources=[],
                    confidence="low"
                )
            
            # Generate prompt
            prompt = self.generate_prompt(question, contexts)
            
            # Generate answer
            response = self.synthesize_answer(prompt)
            
            # Add source references from contexts
            response.sources.extend(self._create_source_references(contexts))
            
            return response
            
        except Exception as e:
            raise QueryError(f"Failed to process query: {e}")
    
    def _extract_sources_from_answer(self, answer: str) -> List[SourceReference]:
        """Extract source references from the answer text."""
        sources = []
        
        # Simple regex to find file references in the answer
        import re
        file_pattern = r'`([^`]+\.(?:py|js|ts|jsx|tsx|java|go|rs|cpp|c|h|hpp|cs|php|rb|swift))`'
        matches = re.findall(file_pattern, answer)
        
        for file_path in matches:
            # Extract snippet around the reference (simplified)
            snippet = f"Referenced in answer: {file_path}"
            sources.append(SourceReference(
                file=file_path,
                snippet=snippet,
                line_start=0,
                line_end=0
            ))
        
        return sources
    
    def _create_source_references(self, contexts: List[Context]) -> List[SourceReference]:
        """Create source references from contexts."""
        sources = []
        
        for context in contexts:
            # Truncate content for snippet
            snippet = context.content
            if len(snippet) > 200:
                snippet = snippet[:200] + "..."
            
            sources.append(SourceReference(
                file=context.file_path,
                snippet=snippet,
                line_start=context.start_line,
                line_end=context.end_line
            ))
        
        return sources
    
    def _determine_confidence(self, answer: str) -> str:
        """Determine confidence level based on answer content."""
        answer_lower = answer.lower()
        
        # High confidence indicators
        if any(phrase in answer_lower for phrase in [
            "based on the code", "in the file", "as shown in", "the function",
            "the class", "line", "defined in"
        ]):
            return "high"
        
        # Low confidence indicators
        if any(phrase in answer_lower for phrase in [
            "i cannot", "not enough information", "unclear", "might be",
            "appears to", "seems like", "i don't see"
        ]):
            return "low"
        
        return "medium"
