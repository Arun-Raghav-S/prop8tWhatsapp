"""
🤖 SOPHISTICATED RESPONSE GENERATOR
Converts search results and alternatives into intelligent, actionable WhatsApp messages

Author: AI Assistant  
Purpose: Generate helpful responses that guide users to better property matches
"""

import json
from typing import Dict, Any, List, Optional
from tools.sophisticated_search_pipeline import SearchResult, SearchTier, SearchCriteria
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SophisticatedResponseGenerator:
    """
    🎯 Generates intelligent responses for sophisticated search results
    Converts technical search data into user-friendly WhatsApp messages
    """
    
    def __init__(self):
        pass
    
    def generate_response(self, search_result: SearchResult, original_criteria: SearchCriteria) -> str:
        """
        🧠 Main method to generate intelligent response based on search results
        
        Args:
            search_result: Result from sophisticated search pipeline
            original_criteria: Original search criteria from user
        
        Returns:
            Formatted WhatsApp message with actionable suggestions
        """
        try:
            if search_result.tier == SearchTier.EXACT_MATCH:
                return self._generate_exact_match_response(search_result, original_criteria)
            
            elif search_result.tier == SearchTier.SINGLE_CONSTRAINT_RELAXATION:
                return self._generate_alternative_response(search_result, original_criteria)
            
            elif search_result.tier == SearchTier.MULTI_CONSTRAINT_RELAXATION:
                return self._generate_multi_constraint_response(search_result, original_criteria)
            
            elif search_result.tier == SearchTier.MARKET_INTELLIGENCE:
                return self._generate_market_intelligence_response(search_result, original_criteria)
            
            else:
                return self._generate_fallback_response(original_criteria)
                
        except Exception as e:
            logger.error(f"❌ Response generation failed: {e}")
            return "I found some interesting properties for you, but had trouble formatting the response. Let me know what specific details you'd like to know!"
    
    def _generate_exact_match_response(self, search_result: SearchResult, criteria: SearchCriteria) -> str:
        """Generate response for exact matches"""
        properties = search_result.properties[:5]  # Show top 5
        
        # Create header based on criteria
        header = self._create_search_summary(criteria, exact_match=True)
        header += f" ✅ Found {search_result.count} perfect matches!\n\n"
        
        # Format properties
        properties_text = ""
        for i, prop in enumerate(properties, 1):
            properties_text += self._format_property_item(prop, i)
        
        # Add interaction prompts
        footer = self._create_interaction_prompts(search_result.count)
        
        return header + properties_text + footer
    
    def _generate_alternative_response(self, search_result: SearchResult, criteria: SearchCriteria) -> str:
        """Generate response for single-constraint alternatives"""
        strategy = search_result.strategy_used
        alternatives = search_result.alternatives_found
        
        # Create explanatory header
        header = f"🔍 No exact matches for your search, but I found great alternatives!\n\n"
        header += self._create_search_summary(criteria, exact_match=False)
        
        # Explain what alternatives were found
        explanation = self._explain_alternatives(alternatives, criteria, strategy)
        
        # Show properties
        properties_text = "\n🏠 **Here are the best options:**\n\n"
        for i, prop in enumerate(search_result.properties[:5], 1):
            properties_text += self._format_property_item(prop, i)
        
        # Add specific suggestions
        suggestions_text = "\n💡 **Other options you might consider:**\n"
        for suggestion in search_result.suggestions[:3]:
            suggestions_text += f"• {suggestion}\n"
        
        footer = "\n👉 Click 'Know More' on any property card for details\n📞 Book viewing for any property\n🔍 Adjust my search criteria"
        
        return header + explanation + properties_text + suggestions_text + footer
    
    def _generate_multi_constraint_response(self, search_result: SearchResult, criteria: SearchCriteria) -> str:
        """Generate response for multi-constraint relaxation"""
        # First, explicitly state no matches found
        header = f"❌ *No exact matches found for your criteria*\n\n"
        header += self._create_search_summary(criteria, exact_match=False)
        
        # Explain the specific issue
        issue_explanation = self._explain_specific_issues(search_result.alternatives_found, criteria)
        
        # Explain how search was broadened with specific details
        broadening_explanation = self._explain_search_broadening(search_result.alternatives_found, criteria)
        
        suggestions_text = "\n💡 *Recommendations:*\n"
        for suggestion in search_result.suggestions:
            suggestions_text += f"• {suggestion}\n"
        
        footer = "\n🔍 Refine my search criteria\n👉 Click 'Know More' on any property card for details"
        
        return header + issue_explanation + broadening_explanation + suggestions_text + footer
    
    def _generate_market_intelligence_response(self, search_result: SearchResult, criteria: SearchCriteria) -> str:
        """Generate response for market intelligence"""
        header = f"📊 **Market Analysis for Your Search**\n\n"
        header += self._create_search_summary(criteria, exact_match=False)
        
        # Explain the situation
        explanation = "I've analyzed the current market and here's what I found:\n\n"
        
        # Show market insights
        insights_text = self._format_detailed_market_insights(search_result.alternatives_found, criteria)
        
        # Show actionable suggestions
        suggestions_text = "\n🎯 **Here's what I recommend:**\n"
        for suggestion in search_result.suggestions:
            suggestions_text += f"• {suggestion}\n"
        
        # Show sample properties if available
        properties_text = ""
        if search_result.properties:
            properties_text = f"\n🏠 **Sample properties currently available:**\n\n"
            for i, prop in enumerate(search_result.properties[:3], 1):
                properties_text += self._format_property_item(prop, i)
        
        footer = "\n🔍 Adjust my search criteria\n📞 Speak with a property consultant\n💬 Get personalized recommendations"
        
        return header + explanation + insights_text + suggestions_text + properties_text + footer
    
    def _generate_fallback_response(self, criteria: SearchCriteria) -> str:
        """Generate fallback response when all else fails"""
        return f"""🤔 I'm having trouble finding properties that match your specific criteria right now.

🔍 **Your search:** {self._create_search_summary(criteria, exact_match=False)}

💡 **Let me help you differently:**
• Broaden your search criteria (location, budget, or property type)
• Get a market analysis for your preferred area
• Speak with our property consultants for personalized assistance
• Browse our most popular properties

What would you like to do next?"""
    
    def _create_search_summary(self, criteria: SearchCriteria, exact_match: bool = False) -> str:
        """Create a summary of the search criteria"""
        parts = []
        
        if criteria.transaction_type:
            parts.append(f"looking to {criteria.transaction_type}")
        
        # Format property details
        property_details = []
        if criteria.bedrooms:
            property_details.append(f"{criteria.bedrooms}BR")
        if criteria.property_type:
            property_details.append(criteria.property_type.lower())
        
        if property_details:
            parts.append(" ".join(property_details))
        
        if criteria.location:
            parts.append(f"in {criteria.location}")
        
        # Format budget
        if criteria.budget_min or criteria.budget_max:
            budget_parts = []
            if criteria.budget_min:
                budget_parts.append(f"{criteria.budget_min/1000:.0f}k")
            if criteria.budget_max and criteria.budget_max != criteria.budget_min:
                budget_parts.append(f"{criteria.budget_max/1000:.0f}k")
            
            budget_str = "-".join(budget_parts) if len(budget_parts) > 1 else budget_parts[0]
            parts.append(f"under {budget_str} AED")
        
        summary = "🔍 You're " + ", ".join(parts)
        
        if exact_match:
            summary += ""
        else:
            summary += "\n"
        
        return summary
    
    def _format_property_item(self, prop: Dict[str, Any], index: int) -> str:
        """Format a single property for display"""
        try:
            # Extract basic info
            property_type = prop.get('property_type', 'Property')
            bedrooms = prop.get('bedrooms', 0)
            bathrooms = prop.get('bathrooms', 0)
            
            # Format price
            price = "Price on request"
            if prop.get('sale_price_aed'):
                price = f"AED {prop['sale_price_aed']:,}"
            elif prop.get('rent_price_aed'):
                price = f"AED {prop['rent_price_aed']:,}/year"
            
            # Extract location
            address = prop.get('address', {})
            if isinstance(address, str):
                try:
                    address = json.loads(address)
                except:
                    address = {}
            
            location = "Dubai"
            if address and address.get('locality'):
                location = address['locality']
            
            building_name = prop.get('building_name', '')
            if building_name:
                location = f"{building_name}, {location}"
            
            # Format size
            size_text = ""
            if prop.get('bua_sqft'):
                size_text = f" • 📐 {prop['bua_sqft']:,} sqft"
            
            # Format features
            features = []
            if prop.get('study'):
                features.append('Study')
            if prop.get('maid_room'):
                features.append('Maid room')
            if prop.get('park_pool_view'):
                features.append('Pool view')
            if prop.get('landscaped_garden'):
                features.append('Garden')
            
            features_text = ""
            if features:
                features_text = f" • ✨ {', '.join(features[:2])}"  # Show max 2 features
            
            return f"""{index}. 🏠 **{bedrooms}BR {property_type}**
💰 {price}
📍 {location}
🚿 {bathrooms} Bath{size_text}{features_text}

"""
        
        except Exception as e:
            logger.error(f"❌ Property formatting error: {e}")
            return f"{index}. Property details available - ask for more info!\n\n"
    
    def _explain_alternatives(self, alternatives: Dict[str, Any], criteria: SearchCriteria, strategy: str) -> str:
        """Explain what alternatives were found and why"""
        explanations = {
            'budget_expansion': f"💰 I found properties by expanding your budget slightly:",
            'location_alternatives': f"📍 I found properties in nearby areas to {criteria.location}:",
            'property_type_alternatives': f"🏠 I found similar property types to {criteria.property_type}:",
            'bedroom_alternatives': f"🛏️ I found properties with different bedroom counts:"
        }
        
        explanation = explanations.get(strategy, "🔍 I found some great alternatives:")
        explanation += "\n\n"
        
        return explanation
    
    def _explain_specific_issues(self, alternatives_found: Dict[str, Any], criteria: SearchCriteria) -> str:
        """Explain what specifically caused no matches"""
        issues = set()  # Use set to avoid duplicates
        
        # Check if location is the issue
        location_issue = False
        budget_issue = False
        
        for key, data in alternatives_found.items():
            if 'analysis' in data:
                analysis = data['analysis']
                
                # Check location availability
                if 'locations' in analysis and criteria.location:
                    location_found = any(criteria.location.lower() in loc.lower() for loc in analysis['locations'].keys())
                    if not location_found:
                        location_issue = True
                
                # Check budget constraints
                if 'price_ranges' in analysis and (criteria.budget_min or criteria.budget_max):
                    budget_max = criteria.budget_max or criteria.budget_min
                    if budget_max:
                        has_affordable_properties = False
                        for price_range in analysis['price_ranges'].keys():
                            if 'k' in price_range.lower():
                                try:
                                    range_parts = price_range.replace('k', '').replace('K', '').split('-')
                                    range_min = float(range_parts[0]) * 1000
                                    if range_min <= budget_max:
                                        has_affordable_properties = True
                                        break
                                except:
                                    continue
                        
                        if not has_affordable_properties:
                            budget_issue = True
        
        # Add issues in priority order - budget first, then location
        if budget_issue and (criteria.budget_min or criteria.budget_max):
            budget_max = criteria.budget_max or criteria.budget_min
            issues.add(f"💰 No properties available under {budget_max/1000:.0f}k AED budget")
        
        if location_issue and criteria.location:
            issues.add(f"📍 No {criteria.property_type or 'properties'} available in {criteria.location}")
        
        if issues:
            return "\n".join(sorted(issues)) + "\n\n"
        else:
            return "No properties match your exact combination of criteria.\n\n"
    
    def _explain_search_broadening(self, alternatives_found: Dict[str, Any], criteria: SearchCriteria) -> str:
        """Explain how exactly the search was broadened with sophisticated priority logic and exact counts"""
        explanation = "*How I broadened your search:*\n"
        
        # Analyze budget expansion results first
        budget_results = self._analyze_budget_expansion(alternatives_found, criteria)
        
        # Priority 1: Show budget expansion results with exact counts
        if budget_results['expanded']:
            explanation += budget_results['explanation']
            
            # Only expand location if budget expansion didn't give enough results (< 10 properties)
            if budget_results['total_properties'] < 10:
                location_results = self._analyze_location_expansion(alternatives_found, criteria)
                if location_results['expanded']:
                    explanation += location_results['explanation']
            else:
                explanation += f"✅ *Found sufficient properties ({budget_results['total_properties']}) with budget increase alone*\n"
        else:
            # If no budget expansion, try location expansion
            location_results = self._analyze_location_expansion(alternatives_found, criteria)
            if location_results['expanded']:
                explanation += location_results['explanation']
        
        # Show property type expansion if it happened
        property_type_results = self._analyze_property_type_expansion(alternatives_found, criteria)
        if property_type_results['expanded']:
            explanation += property_type_results['explanation']
        
        return explanation + "\n"
    
    def _analyze_budget_expansion(self, alternatives_found: Dict[str, Any], criteria: SearchCriteria) -> Dict[str, Any]:
        """Analyze budget expansion with exact property counts per range"""
        if not (criteria.budget_min or criteria.budget_max):
            return {'expanded': False, 'explanation': '', 'total_properties': 0}
        
        budget_max = criteria.budget_max or criteria.budget_min
        # Use dict to aggregate counts for duplicate ranges
        range_aggregation = {}
        total_properties = 0
        
        for key, data in alternatives_found.items():
            if 'analysis' in data and 'price_ranges' in data['analysis']:
                price_ranges = data['analysis']['price_ranges']
                
                for price_range, count in price_ranges.items():
                    if 'k' in price_range.lower():
                        try:
                            range_parts = price_range.replace('k', '').replace('K', '').split('-')
                            range_min = float(range_parts[0]) * 1000
                            
                            # Only count ranges above original budget
                            if range_min > budget_max:
                                if price_range in range_aggregation:
                                    # Aggregate counts for duplicate ranges
                                    range_aggregation[price_range]['count'] += count
                                else:
                                    range_aggregation[price_range] = {
                                        'count': count,
                                        'min_price': range_min
                                    }
                        except:
                            continue
        
        if not range_aggregation:
            return {'expanded': False, 'explanation': '', 'total_properties': 0}
        
        # Convert to list and sort by price range
        expansion_details = []
        for price_range, data in range_aggregation.items():
            expansion_details.append({
                'range': price_range,
                'count': data['count'],
                'min_price': data['min_price']
            })
            total_properties += data['count']
        
        expansion_details.sort(key=lambda x: x['min_price'])
        explanation = "💰 *Budget expansion results:*\n"
        
        for detail in expansion_details[:3]:
            explanation += f"   • {detail['range']} AED: **{detail['count']} properties**\n"
        
        explanation += f"💡 *Total with increased budget: {total_properties} properties*\n"
        
        return {
            'expanded': True,
            'explanation': explanation,
            'total_properties': total_properties
        }
    
    def _analyze_location_expansion(self, alternatives_found: Dict[str, Any], criteria: SearchCriteria) -> Dict[str, Any]:
        """Analyze location expansion with minimum budget info per area"""
        if not criteria.location:
            return {'expanded': False, 'explanation': ''}
        
        location_details = []
        
        for key, data in alternatives_found.items():
            if 'analysis' in data:
                analysis = data['analysis']
                
                if 'locations' in analysis:
                    locations = analysis['locations']
                    
                    for location, count in locations.items():
                        # Skip original location
                        if criteria.location.lower() not in location.lower():
                            # Get minimum price for this location from price ranges
                            min_budget = self._get_min_budget_for_location(data, location)
                            
                            location_details.append({
                                'location': location,
                                'count': count,
                                'min_budget': min_budget
                            })
        
        if not location_details:
            return {'expanded': False, 'explanation': ''}
        
        # Sort by property count (descending) and show top 3
        location_details.sort(key=lambda x: x['count'], reverse=True)
        explanation = "📍 *Location expansion (since budget increase gave limited results):*\n"
        
        for detail in location_details[:3]:
            min_budget_text = f"from {detail['min_budget']/1000:.0f}k AED" if detail['min_budget'] else "various budgets"
            explanation += f"   • **{detail['location']}**: {detail['count']} properties ({min_budget_text})\n"
        
        return {
            'expanded': True,
            'explanation': explanation
        }
    
    def _analyze_property_type_expansion(self, alternatives_found: Dict[str, Any], criteria: SearchCriteria) -> Dict[str, Any]:
        """Analyze property type expansion with counts"""
        if not criteria.property_type:
            return {'expanded': False, 'explanation': ''}
        
        type_details = []
        
        for key, data in alternatives_found.items():
            if 'analysis' in data and 'property_types' in data['analysis']:
                property_types = data['analysis']['property_types']
                
                for ptype, count in property_types.items():
                    # Skip original property type
                    if ptype.lower() != criteria.property_type.lower():
                        type_details.append({
                            'type': ptype,
                            'count': count
                        })
        
        if not type_details:
            return {'expanded': False, 'explanation': ''}
        
        # Sort by count and show top 2
        type_details.sort(key=lambda x: x['count'], reverse=True)
        explanation = "🏠 *Property type expansion:*\n"
        
        for detail in type_details[:2]:
            explanation += f"   • **{detail['type']}**: {detail['count']} properties\n"
        
        return {
            'expanded': True,
            'explanation': explanation
        }
    
    def _get_min_budget_for_location(self, data: Dict[str, Any], location: str) -> float:
        """Get minimum budget required for properties in a specific location"""
        if 'analysis' not in data or 'price_ranges' not in data['analysis']:
            return 0
        
        min_budget = float('inf')
        price_ranges = data['analysis']['price_ranges']
        
        for price_range in price_ranges.keys():
            if 'k' in price_range.lower():
                try:
                    range_parts = price_range.replace('k', '').replace('K', '').split('-')
                    range_min = float(range_parts[0]) * 1000
                    min_budget = min(min_budget, range_min)
                except:
                    continue
        
        return min_budget if min_budget != float('inf') else 0

    
    def _format_detailed_market_insights(self, market_insights: Dict[str, Any], criteria: SearchCriteria) -> str:
        """Format detailed market intelligence insights"""
        insights_text = ""
        
        # Location analysis
        if 'location_analysis' in market_insights:
            location_data = market_insights['location_analysis']
            target_count = location_data.get('target_location_count', 0)
            
            if target_count == 0:
                insights_text += f"📍 **{criteria.location}:** No properties currently available\n"
                top_locations = list(location_data.get('available_locations', {}).keys())[:3]
                if top_locations:
                    insights_text += f"   ↳ **Alternative areas:** {', '.join(top_locations)}\n\n"
            else:
                percentage = location_data.get('location_availability_percentage', 0)
                insights_text += f"📍 **{criteria.location}:** {target_count} properties available ({percentage:.1f}% of market)\n\n"
        
        # Budget analysis
        if 'budget_analysis' in market_insights:
            budget_data = market_insights['budget_analysis']
            in_budget = budget_data.get('in_budget_count', 0)
            
            if in_budget == 0:
                insights_text += f"💰 **Your budget range:** No properties currently available\n"
                price_dist = budget_data.get('price_distribution', {})
                if price_dist:
                    popular_ranges = list(price_dist.keys())[:3]
                    insights_text += f"   ↳ **Popular price ranges:** {', '.join(popular_ranges)}\n\n"
            else:
                percentage = budget_data.get('budget_availability_percentage', 0)
                insights_text += f"💰 **Your budget range:** {in_budget} properties available ({percentage:.1f}% of market)\n\n"
        
        # Property type analysis
        if 'property_type_analysis' in market_insights:
            type_data = market_insights['property_type_analysis']
            type_count = type_data.get('target_type_count', 0)
            
            if type_count == 0:
                insights_text += f"🏠 **{criteria.property_type}s:** No properties currently available\n"
                type_dist = type_data.get('type_distribution', {})
                if type_dist:
                    available_types = list(type_dist.keys())[:3]
                    insights_text += f"   ↳ **Available types:** {', '.join(available_types)}\n\n"
            else:
                percentage = type_data.get('type_availability_percentage', 0)
                insights_text += f"🏠 **{criteria.property_type}s:** {type_count} properties available ({percentage:.1f}% of market)\n\n"
        
        return insights_text
    
    def _create_interaction_prompts(self, property_count: int) -> str:
        """Create interaction prompts based on results"""
        if property_count > 5:
            return f"\n👉 Click 'Know More' on any property card for details\n📅 Book viewing for any property\n🔍 Show me more properties\n\n💬 Which property interests you most?"
        elif property_count > 0:
            return f"\n👉 Click 'Know More' on any property card for details\n📅 Book viewing for any property\n🔍 Adjust my search criteria\n\n💬 Which property would you like to know more about?"
        else:
            return f"\n🔍 Broaden my search\n📞 Speak with a consultant\n💬 Get personalized recommendations"


# Global instance for easy import
sophisticated_response_generator = SophisticatedResponseGenerator()


def generate_sophisticated_response(search_result: SearchResult, criteria: SearchCriteria) -> str:
    """
    🚀 Public interface for generating sophisticated responses
    
    Args:
        search_result: Result from sophisticated search pipeline
        criteria: Original search criteria
    
    Returns:
        Formatted WhatsApp message with intelligent suggestions
    """
    return sophisticated_response_generator.generate_response(search_result, criteria)
