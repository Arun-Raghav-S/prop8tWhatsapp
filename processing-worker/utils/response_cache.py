"""
Professional Response Cache System
Eliminates redundant OpenAI calls and provides instant responses for common queries
"""

import time
import json
import hashlib
from typing import Dict, Any, Optional, List
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ResponseCache:
    """
    Professional-grade response cache with intelligent invalidation
    """
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        self.hit_count = 0
        self.miss_count = 0
        
        # Template responses for common queries
        self.templates = {
            'generic_properties': self._get_generic_properties_template(),
            'booking_confirmation': self._get_booking_confirmation_template(),
            'location_info': self._get_location_info_template()
        }
    
    def _generate_cache_key(self, query: str, user_context: Dict = None) -> str:
        """Generate deterministic cache key"""
        # Normalize query
        normalized = query.lower().strip()
        
        # Add context if relevant
        context_str = ""
        if user_context:
            # Only include relevant context for caching
            relevant_keys = ['user_id', 'active_properties_count', 'last_search_type']
            context_data = {k: v for k, v in user_context.items() if k in relevant_keys}
            context_str = json.dumps(context_data, sort_keys=True)
        
        # Create hash
        cache_input = f"{normalized}:{context_str}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if valid"""
        if cache_key not in self.cache:
            self.miss_count += 1
            return None
        
        cached_item = self.cache[cache_key]
        
        # Check if expired
        if time.time() - cached_item['timestamp'] > self.ttl_seconds:
            del self.cache[cache_key]
            self.miss_count += 1
            return None
        
        self.hit_count += 1
        logger.info(f"🎯 CACHE HIT: {cache_key[:8]}... (hit rate: {self.get_hit_rate():.1%})")
        return cached_item['data']
    
    def set(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Cache response data"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        
        # Simple cleanup: remove oldest if cache gets too large
        if len(self.cache) > 1000:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    def can_use_template(self, query: str, search_results: List = None) -> Optional[str]:
        """Determine if we can use a template response"""
        query_lower = query.lower().strip()
        
        # DISABLE templates for carousel-suitable queries
        carousel_keywords = [
            'what all properties', 'cheapest', 'top', 'best', 'tell me', 
            'all properties', 'available properties', 'show me all'
        ]
        
        # If query is suitable for carousel, don't use template - go through full pipeline
        if any(keyword in query_lower for keyword in carousel_keywords):
            logger.info(f"🎠 TEMPLATE_DISABLED: Carousel-suitable query, using full pipeline")
            return None
        
        # Generic property requests (only very basic ones)
        generic_patterns = [
            'properties', 'show me', 'find me',  # Removed patterns that could trigger carousel
            'property options'
        ]
        
        if any(pattern in query_lower for pattern in generic_patterns):
            # But still check if this might be a carousel query
            if not any(keyword in query_lower for keyword in carousel_keywords):
                return 'generic_properties'
        
        # Booking confirmations
        booking_patterns = ['book', 'schedule', 'visit', 'viewing', 'appointment']
        if any(pattern in query_lower for pattern in booking_patterns):
            return 'booking_confirmation'
        
        # Location queries  
        location_patterns = ['where', 'location', 'address', 'area']
        if any(pattern in query_lower for pattern in location_patterns):
            return 'location_info'
        
        return None
    
    def generate_template_response(self, template_type: str, context: Dict[str, Any]) -> str:
        """Generate response from template with context"""
        if template_type not in self.templates:
            return ""
        
        template = self.templates[template_type]
        
        try:
            # Fill template with context data
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Template context missing key: {e}")
            return template  # Return unfilled template as fallback
    
    def _get_generic_properties_template(self) -> str:
        """Template for generic property listings"""
        return """🏠 **Found {property_count} amazing properties for you!**

Let's dive into the details of these fantastic options:

{property_listings}

---

✨ **Industrial Features Used:**
- **Advanced Sorting:** Results organized by relevance and value
- **Intelligent Limits:** Focused results for better decision-making  
- **Real-time Data:** Latest market information

---

🔍 **Next Steps:**
- **Visit:** Schedule a visit to any property that interests you
- **Details:** Ask for more information about specific properties
- **Refine:** Let me know your preferences to narrow down options

Feel free to ask about any property! 😊"""
    
    def _get_booking_confirmation_template(self) -> str:
        """Template for booking confirmations"""
        return """✅ **Visit Scheduled Successfully!**

🎫 **Booking Reference:** {booking_ref}

🏢 **Property Details:**
   • **Name:** {property_name}
   • **Location:** {property_location}
   • **Type:** {property_type}

📅 **Visit Details:**
   • **Date:** {visit_date}
   • **Time:** {visit_time}

📋 **What happens next:**
1. **Confirmation Call:** Our team will call you within 2 hours to confirm details
2. **Agent Assignment:** You'll get your viewing agent's contact info
3. **Meeting Point:** Exact location and parking details will be shared
4. **Property Tour:** Professional guided viewing with all amenities

📱 **Important:**
   • Keep this booking reference: **{booking_ref}**
   • If you need to reschedule, reply with your reference number
   • Arrive 5 minutes early for the best experience

Anything else you'd like to know about this property? 🏠✨"""
    
    def _get_location_info_template(self) -> str:
        """Template for location information"""
        return """📍 **Here's the location information:**

🏢 **Property:** {property_name}
📍 **Address:** {property_address}
🌆 **Area:** {property_area}

🌟 **Nearby Landmarks:**
{nearby_landmarks}

🚇 **Transportation:**
• Metro: {nearest_metro}
• Major Roads: {major_roads}

🛍️ **Amenities:**
• Shopping: {shopping_centers}
• Healthcare: {healthcare}
• Schools: {schools}

Would you like to schedule a visit to see this location? 🏠"""
    
    def invalidate_user_cache(self, user_id: str) -> int:
        """Invalidate all cache entries for a specific user"""
        invalidated = 0
        keys_to_remove = []
        
        for key, value in self.cache.items():
            # Check if this cache entry is for the specific user
            if f'"user_id": "{user_id}"' in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
            invalidated += 1
        
        if invalidated > 0:
            logger.info(f"🧹 Invalidated {invalidated} cache entries for user {user_id}")
        
        return invalidated
    
    def clear_expired(self) -> int:
        """Clear all expired cache entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, value in self.cache.items():
            if current_time - value['timestamp'] > self.ttl_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"🧹 Cleared {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)

# Global cache instance
response_cache = ResponseCache()