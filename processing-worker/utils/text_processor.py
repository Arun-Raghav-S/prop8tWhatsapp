"""
Professional Text Processing Utilities
Handles spell checking, typo correction, and message normalization
"""

import re
from typing import Dict, List, Tuple, Optional

class MessageProcessor:
    """
    Professional message processor that handles typos, spell checking, 
    and message normalization for real estate chatbot
    """
    
    def __init__(self):
        # Common real estate and booking typos
        self.typo_corrections = {
            # Time/date typos
            'tyomorrow': 'tomorrow',
            'tomorow': 'tomorrow', 
            'tommorow': 'tomorrow',
            'tomarrow': 'tomorrow',
            'tonorrow': 'tomorrow',
            'tomorow': 'tomorrow',
            'tommorrow': 'tomorrow',
            'tomorow': 'tomorrow',
            
            # Booking related
            'boook': 'book',
            'scedule': 'schedule',
            'schedual': 'schedule',
            'shedule': 'schedule',
            'shcedule': 'schedule',
            'appointment': 'appointment',
            'appointement': 'appointment',
            'apointment': 'appointment',
            
            # Property related
            'apartement': 'apartment',
            'appartment': 'apartment',
            'appartement': 'apartment',
            'proeprties': 'properties',
            'proerpty': 'property',
            'propertie': 'property',
            'propery': 'property',
            'properites': 'properties',
            'propertes': 'properties',
            
            # Common general typos
            'i want to': 'i want to',
            'wnat': 'want',
            'waht': 'what',
            'teh': 'the',
            'adn': 'and',
            'wiht': 'with',
            'frist': 'first',
            'fisrt': 'first',
            'secod': 'second',
            'secon': 'second',
            'thrid': 'third',
            'fourht': 'fourth',
            'fith': 'fifth',
            
            # Location typos
            'dubaii': 'dubai',
            'duabi': 'dubai',
            'dubao': 'dubai',
            'marina': 'marina',
            'marnia': 'marina',
            'jumeirah': 'jumeirah',
            'jumeriah': 'jumeirah',
            'jumerah': 'jumeirah',
            
            # Common chat typos
            'u': 'you',
            'ur': 'your',
            'bro': '',  # Remove casual terms
            'pls': 'please',
            'plz': 'please',
            'thnks': 'thanks',
            'thanx': 'thanks',
            'thx': 'thanks'
        }
        
        # Time patterns for better detection
        self.time_patterns = [
            r'(\d{1,2})\s*(am|pm)',
            r'(\d{1,2}):(\d{2})\s*(am|pm)?',
            r'(\d{1,2})\s*o\'?clock',
            r'(morning|afternoon|evening|night)',
            r'(tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
        ]
        
        # Booking intent patterns
        self.booking_patterns = [
            r'(book|schedule|visit|viewing|appointment|show|see)',
            r'(tomorrow|next\s+\w+|this\s+\w+|\d+\s*(am|pm))',
            r'(available|when|time|date)',
        ]
    
    def process_message(self, message: str) -> Dict[str, any]:
        """
        Comprehensive message processing with professional error handling
        
        Returns:
            {
                'original': original message,
                'corrected': corrected message,
                'has_typos': bool,
                'corrections_made': list of corrections,
                'intent_signals': detected intent signals,
                'confidence': confidence score
            }
        """
        original = message.strip()
        
        # Step 1: Basic cleanup
        cleaned = self._basic_cleanup(original)
        
        # Step 2: Spell correction
        corrected, corrections = self._correct_spelling(cleaned)
        
        # Step 3: Intent detection
        intent_signals = self._detect_intent_signals(corrected)
        
        # Step 4: Calculate confidence
        confidence = self._calculate_confidence(original, corrected, intent_signals)
        
        return {
            'original': original,
            'corrected': corrected,
            'has_typos': len(corrections) > 0,
            'corrections_made': corrections,
            'intent_signals': intent_signals,
            'confidence': confidence
        }
    
    def _basic_cleanup(self, text: str) -> str:
        """Basic text cleanup"""
        # Remove excessive spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that don't add meaning
        text = re.sub(r'[^\w\s:/\-\.]', '', text)
        
        # Handle common contractions
        contractions = {
            "don't": "do not",
            "won't": "will not", 
            "can't": "cannot",
            "i'm": "i am",
            "it's": "it is",
            "that's": "that is"
        }
        
        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)
        
        return text.strip()
    
    def _correct_spelling(self, text: str) -> Tuple[str, List[str]]:
        """Professional spell correction with context awareness"""
        words = text.lower().split()
        corrected_words = []
        corrections = []
        
        for word in words:
            if word in self.typo_corrections:
                corrected_word = self.typo_corrections[word]
                if corrected_word:  # Only add non-empty corrections
                    corrected_words.append(corrected_word)
                    corrections.append(f"'{word}' → '{corrected_word}'")
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words), corrections
    
    def _detect_intent_signals(self, text: str) -> Dict[str, any]:
        """Detect intent signals in the message"""
        signals = {
            'has_time': False,
            'has_booking_intent': False,
            'has_property_reference': False,
            'time_expressions': [],
            'booking_expressions': [],
            'property_references': []
        }
        
        text_lower = text.lower()
        
        # Time detection
        for pattern in self.time_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                signals['has_time'] = True
                signals['time_expressions'].extend([str(m) for m in matches])
        
        # Booking intent detection
        for pattern in self.booking_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                signals['has_booking_intent'] = True
                signals['booking_expressions'].extend([str(m) for m in matches])
        
        # Property reference detection
        property_refs = ['first', 'second', 'third', 'one', 'two', 'three', 'this', 'that', 'it']
        for ref in property_refs:
            if ref in text_lower:
                signals['has_property_reference'] = True
                signals['property_references'].append(ref)
        
        return signals
    
    def _calculate_confidence(self, original: str, corrected: str, intent_signals: Dict) -> float:
        """Calculate confidence score for the processed message"""
        confidence = 1.0
        
        # Reduce confidence for too many corrections
        corrections_ratio = abs(len(original.split()) - len(corrected.split())) / max(len(original.split()), 1)
        confidence -= corrections_ratio * 0.3
        
        # Increase confidence for clear intent signals
        if intent_signals['has_time'] and intent_signals['has_booking_intent']:
            confidence += 0.2
        
        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))
    
    def is_booking_message(self, processed_message: Dict) -> bool:
        """Determine if a processed message is likely a booking request"""
        signals = processed_message['intent_signals']
        
        # High confidence booking indicators
        if signals['has_time'] and signals['has_booking_intent']:
            return True
        
        # Medium confidence - time mentioned with property context
        if signals['has_time'] and len(processed_message['corrected'].split()) <= 5:
            return True
        
        # Look for explicit booking words
        booking_words = ['book', 'schedule', 'visit', 'viewing', 'appointment', 'show', 'see']
        text_lower = processed_message['corrected'].lower()
        
        return any(word in text_lower for word in booking_words)
    
    def extract_property_reference(self, processed_message: Dict) -> str:
        """Extract property reference from processed message"""
        signals = processed_message['intent_signals']
        
        if signals['property_references']:
            # Return the first clear reference
            refs = signals['property_references']
            if 'first' in refs or 'one' in refs:
                return 'first'
            elif 'second' in refs or 'two' in refs:
                return 'second'
            elif 'third' in refs or 'three' in refs:
                return 'third'
            else:
                return refs[0]
        
        # Default to first property for booking requests without explicit reference
        if self.is_booking_message(processed_message):
            return 'first'
        
        return ''