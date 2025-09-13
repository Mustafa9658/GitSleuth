"""Rate limiting service for GitSleuth."""

import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class RateLimit:
    """Rate limit configuration."""
    requests_per_minute: int = 30
    requests_per_hour: int = 500
    requests_per_day: int = 2000
    burst_limit: int = 10  # Allow burst of requests


class RateLimiter:
    """Advanced rate limiter with multiple time windows and burst protection."""
    
    def __init__(self):
        # Store request timestamps for each client
        self.client_requests: Dict[str, deque] = defaultdict(deque)
        self.client_burst: Dict[str, int] = defaultdict(int)
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
        
        # Rate limit configurations
        self.limits = {
            "query": RateLimit(requests_per_minute=20, requests_per_hour=300, requests_per_day=1000),
            "index": RateLimit(requests_per_minute=5, requests_per_hour=50, requests_per_day=100),
            "health": RateLimit(requests_per_minute=60, requests_per_hour=1000, requests_per_day=5000)
        }
    
    def _get_client_id(self, request) -> str:
        """Extract client identifier from request."""
        # Try to get real IP from headers (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection IP
        return request.client.host if request.client else "unknown"
    
    def _cleanup_old_requests(self):
        """Remove old request timestamps to prevent memory leaks."""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        cutoff_time = current_time - 86400  # 24 hours ago
        
        for client_id in list(self.client_requests.keys()):
            requests = self.client_requests[client_id]
            
            # Remove old timestamps
            while requests and requests[0] < cutoff_time:
                requests.popleft()
            
            # Remove empty entries
            if not requests:
                del self.client_requests[client_id]
                if client_id in self.client_burst:
                    del self.client_burst[client_id]
        
        self.last_cleanup = current_time
    
    def _check_burst_limit(self, client_id: str, limit: RateLimit) -> bool:
        """Check if client is within burst limits."""
        current_burst = self.client_burst[client_id]
        if current_burst >= limit.burst_limit:
            return False
        
        # Increment burst counter
        self.client_burst[client_id] += 1
        
        # Reset burst counter after 1 minute
        asyncio.create_task(self._reset_burst_counter(client_id, 60))
        
        return True
    
    async def _reset_burst_counter(self, client_id: str, delay: int):
        """Reset burst counter after delay."""
        await asyncio.sleep(delay)
        if client_id in self.client_burst:
            self.client_burst[client_id] = max(0, self.client_burst[client_id] - 1)
    
    def is_allowed(self, request, endpoint_type: str = "query") -> tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed based on rate limits.
        
        Returns:
            (is_allowed, rate_info)
        """
        self._cleanup_old_requests()
        
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # Get rate limit for endpoint type
        limit = self.limits.get(endpoint_type, self.limits["query"])
        
        # Check burst limit first
        if not self._check_burst_limit(client_id, limit):
            return False, {
                "error": "Burst limit exceeded",
                "limit": limit.burst_limit,
                "retry_after": 60
            }
        
        # Get client request history
        requests = self.client_requests[client_id]
        
        # Add current request
        requests.append(current_time)
        
        # Check rate limits
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        day_ago = current_time - 86400
        
        # Count requests in each time window
        minute_requests = sum(1 for req_time in requests if req_time > minute_ago)
        hour_requests = sum(1 for req_time in requests if req_time > hour_ago)
        day_requests = sum(1 for req_time in requests if req_time > day_ago)
        
        # Check if any limit is exceeded
        if minute_requests > limit.requests_per_minute:
            return False, {
                "error": "Rate limit exceeded (per minute)",
                "limit": limit.requests_per_minute,
                "current": minute_requests,
                "retry_after": 60
            }
        
        if hour_requests > limit.requests_per_hour:
            return False, {
                "error": "Rate limit exceeded (per hour)",
                "limit": limit.requests_per_hour,
                "current": hour_requests,
                "retry_after": 3600
            }
        
        if day_requests > limit.requests_per_day:
            return False, {
                "error": "Rate limit exceeded (per day)",
                "limit": limit.requests_per_day,
                "current": day_requests,
                "retry_after": 86400
            }
        
        # Request is allowed
        return True, {
            "minute_remaining": limit.requests_per_minute - minute_requests,
            "hour_remaining": limit.requests_per_hour - hour_requests,
            "day_remaining": limit.requests_per_day - day_requests,
            "burst_remaining": limit.burst_limit - self.client_burst[client_id]
        }
    
    def get_rate_limit_headers(self, rate_info: Dict[str, any]) -> Dict[str, str]:
        """Generate rate limit headers for response."""
        headers = {}
        
        if "minute_remaining" in rate_info:
            headers["X-RateLimit-Limit-Minute"] = str(self.limits["query"].requests_per_minute)
            headers["X-RateLimit-Remaining-Minute"] = str(rate_info["minute_remaining"])
        
        if "hour_remaining" in rate_info:
            headers["X-RateLimit-Limit-Hour"] = str(self.limits["query"].requests_per_hour)
            headers["X-RateLimit-Remaining-Hour"] = str(rate_info["hour_remaining"])
        
        if "day_remaining" in rate_info:
            headers["X-RateLimit-Limit-Day"] = str(self.limits["query"].requests_per_day)
            headers["X-RateLimit-Remaining-Day"] = str(rate_info["day_remaining"])
        
        if "retry_after" in rate_info:
            headers["Retry-After"] = str(rate_info["retry_after"])
        
        return headers


# Global rate limiter instance
rate_limiter = RateLimiter()
