'''
Redis-based idempotency service for Brikk API to prevent duplicate request processing.
'''
import json
import redis
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from flask import current_app
import os


class IdempotencyService:
    '''Redis-based idempotency service with 24-hour TTL.'''
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        '''Initialize idempotency service with Redis client.'''
        if redis_client:
            self.redis = redis_client
        else:
            # Create Redis client from environment variables
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            self.redis = redis.from_url(redis_url, decode_responses=True)
    
    @staticmethod
    def generate_idempotency_key(api_key_id: str, body_hash: str, custom_key: Optional[str] = None) -> str:
        '''
        Generate idempotency key for request.
        
        Format: idem:{key_prefix}:{body_hash_prefix}[:custom]
        '''
        key_prefix = api_key_id[:16] if len(api_key_id) > 16 else api_key_id
        body_prefix = body_hash[:16] if len(body_hash) > 16 else body_hash
        
        base_key = f"idem:{key_prefix}:{body_prefix}"
        
        if custom_key:
            # Allow custom idempotency key from client (e.g., X-Idempotency-Key header)
            custom_suffix = custom_key[:32]  # Limit length
            return f"{base_key}:{custom_suffix}"
        
        return base_key
    
    def store_response(
        self,
        idempotency_key: str,
        response_data: Dict[str, Any],
        status_code: int = 200,
        ttl_hours: int = 24
    ) -> bool:
        '''
        Store response data for idempotency checking.
        
        Returns True if stored successfully, False otherwise.
        '''
        try:
            # Create response record
            record = {
                'response_data': response_data,
                'status_code': status_code,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'ttl_hours': ttl_hours
            }
            
            # Store in Redis with TTL
            ttl_seconds = ttl_hours * 3600
            return self.redis.setex(
                idempotency_key,
                ttl_seconds,
                json.dumps(record)
            )
            
        except Exception as e:
            current_app.logger.error(f"Failed to store idempotency record: {e}")
            return False
    
    def get_cached_response(self, idempotency_key: str) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        '''
        Retrieve cached response for idempotency key.
        
        Returns (response_data, status_code) if found, (None, None) otherwise.
        '''
        try:
            cached_data = self.redis.get(idempotency_key)
            if not cached_data:
                return None, None
            
            record = json.loads(cached_data)
            return record.get('response_data'), record.get('status_code')
            
        except Exception as e:
            current_app.logger.error(f"Failed to retrieve idempotency record: {e}")
            return None, None
    
    def check_request_conflict(
        self,
        api_key_id: str,
        current_body_hash: str,
        custom_idempotency_key: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Tuple[Dict[str, Any], int]]]:
        '''
        Check for idempotency conflicts.
        
        Returns:
        - (False, None, None): No conflict, proceed with request
        - (True, "cached", (response_data, status_code)): Same request, return cached response
        - (True, "conflict", None): Different request with same idempotency key, return 409
        '''
        try:
            if custom_idempotency_key:
                # Check if custom idempotency key is already used with different body
                custom_key = self.generate_idempotency_key(api_key_id, "", custom_idempotency_key)
                response_data, status_code = self.get_cached_response(custom_key)
                cached_response = (response_data, status_code) if response_data else None
                
                if cached_response:
                    # Check if this is the same request (same body hash)
                    stored_body_key = self.generate_idempotency_key(api_key_id, current_body_hash)
                    same_request_response, same_status_code = self.get_cached_response(stored_body_key)
                    same_request_tuple = (same_request_response, same_status_code) if same_request_response else None
                    
                    if same_request_tuple:
                        # Same request, return cached response
                        return True, "cached", same_request_tuple
                    else:
                        # Different request with same custom idempotency key
                        return True, "conflict", None
            
            # Check for exact request match (same API key + body hash)
            request_key = self.generate_idempotency_key(api_key_id, current_body_hash)
            response_data, status_code = self.get_cached_response(request_key)
            cached_response = (response_data, status_code) if response_data else None
            
            if cached_response:
                return True, "cached", cached_response
            
            return False, None, None
            
        except Exception as e:
            current_app.logger.error(f"Failed to check idempotency conflict: {e}")
            # On error, allow request to proceed (fail open)
            return False, None, None
    
    def process_request_idempotency(
        self,
        api_key_id: str,
        body_hash: str,
        custom_idempotency_key: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int]]:
        '''
        Process request idempotency check.
        
        Returns:
        - (True, None, None): Proceed with request processing
        - (False, response_data, status_code): Return cached/error response immediately
        '''
        try:
            is_conflict, conflict_type, cached_response = self.check_request_conflict(
                api_key_id, body_hash, custom_idempotency_key
            )
            
            if is_conflict:
                if conflict_type == "cached":
                    # Return cached response
                    return False, cached_response[0], cached_response[1]
                elif conflict_type == "conflict":
                    # Return 409 Conflict
                    error_response = {
                        'code': 'idempotency_conflict',
                        'message': 'Request with same idempotency key but different body already processed',
                        'request_id': f"req_{api_key_id[:8]}"
                    }
                    return False, error_response, 409
            
            # No conflict, proceed with request
            return True, None, None
            
        except Exception as e:
            current_app.logger.error(f"Failed to process idempotency: {e}")
            # On error, allow request to proceed (fail open)
            return True, None, None
    
    def cleanup_expired_keys(self, batch_size: int = 1000) -> int:
        '''
        Clean up expired idempotency keys (Redis handles TTL automatically).
        
        This method is mainly for monitoring/metrics purposes.
        Returns count of keys that would be cleaned up.
        '''
        try:
            # Get all idempotency keys
            keys = self.redis.keys("idem:*")
            
            # Redis automatically handles TTL cleanup, so this is mainly for metrics
            expired_count = 0
            for key in keys[:batch_size]:  # Process in batches
                ttl = self.redis.ttl(key)
                if ttl == -2:  # Key doesn't exist (expired)
                    expired_count += 1
            
            return expired_count
            
        except Exception as e:
            current_app.logger.error(f"Failed to cleanup expired keys: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        '''Get idempotency service statistics.'''
        try:
            # Get all idempotency keys
            keys = self.redis.keys("idem:*")
            total_keys = len(keys)
            
            # Sample some keys to get average TTL
            sample_size = min(100, total_keys)
            sample_keys = keys[:sample_size] if keys else []
            
            total_ttl = 0
            active_keys = 0
            
            for key in sample_keys:
                ttl = self.redis.ttl(key)
                if ttl > 0:
                    total_ttl += ttl
                    active_keys += 1
            
            avg_ttl = (total_ttl / active_keys) if active_keys > 0 else 0
            
            return {
                'total_keys': total_keys,
                'active_keys': active_keys,
                'average_ttl_seconds': round(avg_ttl, 2),
                'redis_connected': self.redis.ping(),
                'service_status': 'healthy'
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to get idempotency stats: {e}")
            return {
                'total_keys': 0,
                'active_keys': 0,
                'average_ttl_seconds': 0,
                'redis_connected': False,
                'service_status': 'error',
                'error': str(e)
            }
    
    def delete_key(self, idempotency_key: str) -> bool:
        '''
        Delete specific idempotency key (for testing or manual cleanup).
        
        Returns True if deleted, False otherwise.
        '''
        try:
            return bool(self.redis.delete(idempotency_key))
        except Exception as e:
            current_app.logger.error(f"Failed to delete idempotency key: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        '''Perform health check on idempotency service.'''
        try:
            # Test Redis connection
            ping_result = self.redis.ping()
            
            # Test basic operations
            test_key = "idem:health:test"
            test_data = {"test": True, "timestamp": datetime.now(timezone.utc).isoformat()}
            
            # Test set/get/delete
            set_result = self.redis.setex(test_key, 60, json.dumps(test_data))
            get_result = self.redis.get(test_key)
            delete_result = self.redis.delete(test_key)
            
            return {
                'status': 'healthy',
                'redis_ping': ping_result,
                'redis_operations': {
                    'set': bool(set_result),
                    'get': bool(get_result),
                    'delete': bool(delete_result)
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

