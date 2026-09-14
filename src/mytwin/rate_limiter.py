import time
from threading import Lock
from collections import defaultdict
import gradio as gr

class TokenBucketRateLimiter:
    def __init__(self, capacity: float = 5.0, refill_rate: float = 0.2):
        """
        Token Bucket Rate Limiter.
        
        :param capacity: Maximum number of tokens a user can hold (burst capacity).
        :param refill_rate: How many tokens are added back per second (sustained rate).
                            e.g., 0.2 tokens/sec = 1 token every 5 seconds.
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.lock = Lock()
        
        # Stores user data: {ip_address: (current_tokens, last_update_timestamp)}
        self.buckets = defaultdict(lambda: (self.capacity, time.time()))

    def _get_updated_tokens(self, tokens: float, last_update: float) -> float:
        """Calculates refilled tokens based on elapsed time."""
        now = time.time()
        elapsed = now - last_update
        refilled_tokens = tokens + (elapsed * self.refill_rate)
        return min(self.capacity, refilled_tokens)

    def is_allowed(self, user_ip: str) -> bool:
        """
        Checks if a user is allowed to make a request. Consumes 1 token if true.
        """
        if not user_ip:
            return True  # Fallback if IP cannot be resolved

        with self.lock:
            tokens, last_update = self.buckets[user_ip]
            
            # Refill tokens based on time passed
            tokens = self._get_updated_tokens(tokens, last_update)
            
            # Check if there are enough tokens
            if tokens >= 1.0:
                self.buckets[user_ip] = (tokens - 1.0, time.time())
                return True
                
            # Update the timestamp even on failure so refill math stays accurate
            self.buckets[user_ip] = (tokens, time.time())
            return False

# Global instance to share across the application
# Configured for a burst of 5 messages, refilling 1 message every 5 seconds
limiter = TokenBucketRateLimiter(capacity=5.0, refill_rate=0.2)
