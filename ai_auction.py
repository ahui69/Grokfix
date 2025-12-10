#!/usr/bin/env python3
"""
AI Auction Manager
Przewidywanie cen, optymalizacja opisów, analiza aukcji
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class AIAuctionManager:
    """Manager for AI auction analysis and optimization"""
    
    def __init__(self):
        self.auction_data = {}
        self.price_history = {}
        self.category_data = {}
        self.optimization_rules = {}
        
    async def initialize(self):
        """Initialize the AI auction manager"""
        try:
            logger.info("Initializing AI Auction Manager...")
            
            # Initialize auction databases
            await self._initialize_auction_databases()
            
            logger.info("AI Auction Manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI Auction Manager: {e}")
            raise
    
    async def predict_price(self, image_file: str, description: str, category: str, condition: str,
                          user_id: Optional[str] = None) -> Dict[str, Any]:
        """Predict optimal auction price"""
        try:
            # Analyze item characteristics
            item_analysis = await self._analyze_item_characteristics(image_file, description, category, condition)
            
            # Calculate base price
            base_price = await self._calculate_base_price(item_analysis)
            
            # Apply market factors
            market_adjustment = await self._apply_market_factors(category, condition)
            
            # Generate price range
            price_range = await self._generate_price_range(base_price, market_adjustment)
            
            # Identify pricing factors
            factors = await self._identify_pricing_factors(item_analysis, market_adjustment)
            
            # Calculate confidence
            confidence = await self._calculate_price_confidence(item_analysis, market_adjustment)
            
            return {
                "predicted_price": base_price * market_adjustment,
                "price_range": price_range,
                "confidence": confidence,
                "factors": factors
            }
            
        except Exception as e:
            logger.error(f"Price prediction failed: {e}")
            raise
    
    async def optimize_description(self, title: str, description: str, category: str, images: List[str],
                                 user_id: Optional[str] = None) -> Dict[str, Any]:
        """Optimize auction description for SEO and attractiveness"""
        try:
            # Analyze current description
            description_analysis = await self._analyze_description(title, description, category)
            
            # Generate optimized title
            optimized_title = await self._optimize_title(title, category, description_analysis)
            
            # Generate optimized description
            optimized_description = await self._optimize_description_text(description, category, description_analysis)
            
            # Calculate SEO score
            seo_score = await self._calculate_seo_score(optimized_title, optimized_description, category)
            
            # Generate suggestions
            suggestions = await self._generate_optimization_suggestions(description_analysis, seo_score)
            
            return {
                "optimized_title": optimized_title,
                "optimized_description": optimized_description,
                "seo_score": seo_score,
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"Description optimization failed: {e}")
            raise
    
    async def enhance_image(self, image_file: str, enhancements: List[str],
                          user_id: Optional[str] = None) -> Dict[str, Any]:
        """Enhance auction images"""
        try:
            # Analyze image quality
            image_analysis = await self._analyze_image_quality(image_file)
            
            # Apply enhancements
            enhanced_image = await self._apply_image_enhancements(image_file, enhancements, image_analysis)
            
            # Calculate quality score
            quality_score = await self._calculate_quality_score(enhanced_image, image_analysis)
            
            # Generate improvements list
            improvements = await self._generate_improvements_list(enhancements, image_analysis)
            
            return {
                "enhanced_image": enhanced_image,
                "improvements": improvements,
                "quality_score": quality_score
            }
            
        except Exception as e:
            logger.error(f"Image enhancement failed: {e}")
            raise
    
    async def analyze_feedback(self, feedback_text: str, rating: int, context: str,
                             user_id: Optional[str] = None) -> Dict[str, Any]:
        """Analyze auction feedback"""
        try:
            # Analyze sentiment
            sentiment_analysis = await self._analyze_sentiment(feedback_text, rating)
            
            # Extract key points
            key_points = await self._extract_key_points(feedback_text, sentiment_analysis)
            
            # Generate suggestions
            suggestions = await self._generate_feedback_suggestions(sentiment_analysis, key_points, context)
            
            return {
                "sentiment": sentiment_analysis["sentiment"],
                "key_points": key_points,
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"Feedback analysis failed: {e}")
            raise
    
    async def optimize_timing(self, category: str, item_value: float, urgency: str = "normal",
                            user_id: Optional[str] = None) -> Dict[str, Any]:
        """Optimize auction timing"""
        try:
            # Analyze category timing patterns
            timing_patterns = await self._analyze_category_timing(category)
            
            # Calculate optimal times
            optimal_times = await self._calculate_optimal_times(category, item_value, urgency, timing_patterns)
            
            # Generate recommendations
            recommendations = await self._generate_timing_recommendations(optimal_times, urgency)
            
            return {
                "best_times": optimal_times,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Timing optimization failed: {e}")
            raise
    
    async def _initialize_auction_databases(self):
        """Initialize auction databases"""
        try:
            # Category data
            self.category_data = {
                "elektronika": {
                    "base_multiplier": 1.0,
                    "peak_hours": ["19:00-21:00", "20:00-22:00"],
                    "best_days": ["niedziela", "poniedziałek"],
                    "seasonal_factors": {"q4": 1.2, "q1": 0.8}
                },
                "moda": {
                    "base_multiplier": 0.8,
                    "peak_hours": ["18:00-20:00", "19:00-21:00"],
                    "best_days": ["piątek", "sobota"],
                    "seasonal_factors": {"q2": 1.1, "q4": 1.3}
                },
                "dom_i_ogrod": {
                    "base_multiplier": 0.9,
                    "peak_hours": ["20:00-22:00", "21:00-23:00"],
                    "best_days": ["sobota", "niedziela"],
                    "seasonal_factors": {"q2": 1.2, "q3": 1.1}
                }
            }
            
            # Optimization rules
            self.optimization_rules = {
                "title_keywords": {
                    "elektronika": ["nowy", "oryginalny", "gwarancja", "kompletny"],
                    "moda": ["markowy", "oryginalny", "nowy", "z metkami"],
                    "dom_i_ogrod": ["używany", "sprawny", "kompletny", "dobry stan"]
                },
                "description_structure": {
                    "min_length": 100,
                    "max_length": 500,
                    "required_sections": ["opis", "stan", "wymiary", "dostawa"]
                }
            }
            
        except Exception as e:
            logger.error(f"Auction databases initialization failed: {e}")
    
    async def _analyze_item_characteristics(self, image_file: str, description: str, category: str, condition: str) -> Dict[str, Any]:
        """Analyze item characteristics for pricing"""
        try:
            analysis = {
                "category": category,
                "condition": condition,
                "description_length": len(description),
                "has_images": bool(image_file),
                "keywords": [],
                "brand_mentioned": False,
                "rarity_indicators": []
            }
            
            # Analyze description
            description_lower = description.lower()
            
            # Check for brand mentions
            brand_keywords = ["markowy", "oryginalny", "oryginał", "autentyczny"]
            analysis["brand_mentioned"] = any(keyword in description_lower for keyword in brand_keywords)
            
            # Extract keywords
            analysis["keywords"] = [word for word in description_lower.split() if len(word) > 3]
            
            # Check rarity indicators
            rarity_keywords = ["rzadki", "limitowany", "kolekcjonerski", "vintage", "antyk"]
            analysis["rarity_indicators"] = [word for word in rarity_keywords if word in description_lower]
            
            return analysis
            
        except Exception as e:
            logger.error(f"Item characteristics analysis failed: {e}")
            return {}
    
    async def _calculate_base_price(self, item_analysis: Dict[str, Any]) -> float:
        """Calculate base price for item"""
        try:
            base_price = 100.0  # Default base price
            
            # Adjust based on category
            category = item_analysis.get("category", "")
            if category in self.category_data:
                base_price *= self.category_data[category]["base_multiplier"]
            
            # Adjust based on condition
            condition = item_analysis.get("condition", "")
            condition_multipliers = {
                "nowy": 1.0,
                "bardzo dobry": 0.8,
                "dobry": 0.6,
                "zadowalający": 0.4,
                "używany": 0.3
            }
            base_price *= condition_multipliers.get(condition, 0.5)
            
            # Adjust based on brand
            if item_analysis.get("brand_mentioned"):
                base_price *= 1.5
            
            # Adjust based on rarity
            rarity_count = len(item_analysis.get("rarity_indicators", []))
            base_price *= (1 + rarity_count * 0.2)
            
            return base_price
            
        except Exception as e:
            logger.error(f"Base price calculation failed: {e}")
            return 100.0
    
    async def _apply_market_factors(self, category: str, condition: str) -> float:
        """Apply market factors to price"""
        try:
            market_factor = 1.0
            
            # Category market factor
            if category in self.category_data:
                market_factor *= self.category_data[category]["base_multiplier"]
            
            # Seasonal factor (simplified)
            current_month = datetime.now().month
            if current_month in [11, 12]:  # Q4
                market_factor *= 1.2
            elif current_month in [1, 2, 3]:  # Q1
                market_factor *= 0.8
            
            return market_factor
            
        except Exception as e:
            logger.error(f"Market factors application failed: {e}")
            return 1.0
    
    async def _generate_price_range(self, base_price: float, market_factor: float) -> Dict[str, float]:
        """Generate price range for item"""
        try:
            adjusted_price = base_price * market_factor
            
            return {
                "min": adjusted_price * 0.8,
                "max": adjusted_price * 1.2,
                "recommended": adjusted_price
            }
            
        except Exception as e:
            logger.error(f"Price range generation failed: {e}")
            return {"min": 0, "max": 0, "recommended": 0}
    
    async def _identify_pricing_factors(self, item_analysis: Dict[str, Any], market_factor: float) -> List[str]:
        """Identify key pricing factors"""
        try:
            factors = []
            
            # Category factor
            category = item_analysis.get("category", "")
            if category in self.category_data:
                factors.append(f"Kategoria: {category} (mnożnik: {self.category_data[category]['base_multiplier']})")
            
            # Condition factor
            condition = item_analysis.get("condition", "")
            factors.append(f"Stan: {condition}")
            
            # Brand factor
            if item_analysis.get("brand_mentioned"):
                factors.append("Marka: Wspomniana w opisie (+50%)")
            
            # Rarity factor
            rarity_count = len(item_analysis.get("rarity_indicators", []))
            if rarity_count > 0:
                factors.append(f"Rzadkość: {rarity_count} wskaźników (+{rarity_count * 20}%)")
            
            # Market factor
            if market_factor != 1.0:
                factors.append(f"Czynnik rynkowy: {market_factor:.2f}")
            
            return factors
            
        except Exception as e:
            logger.error(f"Pricing factors identification failed: {e}")
            return []
    
    async def _calculate_price_confidence(self, item_analysis: Dict[str, Any], market_factor: float) -> float:
        """Calculate confidence in price prediction"""
        try:
            confidence = 0.5  # Base confidence
            
            # Increase confidence based on available data
            if item_analysis.get("has_images"):
                confidence += 0.2
            
            if item_analysis.get("description_length", 0) > 50:
                confidence += 0.1
            
            if item_analysis.get("brand_mentioned"):
                confidence += 0.1
            
            if len(item_analysis.get("keywords", [])) > 5:
                confidence += 0.1
            
            # Decrease confidence for uncertain factors
            if market_factor < 0.8 or market_factor > 1.5:
                confidence -= 0.1
            
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Price confidence calculation failed: {e}")
            return 0.5
    
    async def _analyze_description(self, title: str, description: str, category: str) -> Dict[str, Any]:
        """Analyze current description"""
        try:
            analysis = {
                "title_length": len(title),
                "description_length": len(description),
                "has_keywords": False,
                "seo_score": 0.0,
                "missing_elements": [],
                "improvements": []
            }
            
            # Check for category-specific keywords
            if category in self.optimization_rules["title_keywords"]:
                required_keywords = self.optimization_rules["title_keywords"][category]
                found_keywords = [kw for kw in required_keywords if kw in title.lower() or kw in description.lower()]
                analysis["has_keywords"] = len(found_keywords) > 0
                analysis["found_keywords"] = found_keywords
            
            # Check description structure
            required_sections = self.optimization_rules["description_structure"]["required_sections"]
            for section in required_sections:
                if section not in description.lower():
                    analysis["missing_elements"].append(section)
            
            # Calculate basic SEO score
            seo_factors = 0
            if analysis["title_length"] > 10:
                seo_factors += 1
            if analysis["description_length"] > 100:
                seo_factors += 1
            if analysis["has_keywords"]:
                seo_factors += 1
            if len(analysis["missing_elements"]) == 0:
                seo_factors += 1
            
            analysis["seo_score"] = seo_factors / 4.0
            
            return analysis
            
        except Exception as e:
            logger.error(f"Description analysis failed: {e}")
            return {}
    
    async def _optimize_title(self, title: str, category: str, analysis: Dict[str, Any]) -> str:
        """Optimize auction title"""
        try:
            optimized_title = title
            
            # Add category-specific keywords if missing
            if category in self.optimization_rules["title_keywords"]:
                required_keywords = self.optimization_rules["title_keywords"][category]
                found_keywords = analysis.get("found_keywords", [])
                missing_keywords = [kw for kw in required_keywords if kw not in found_keywords]
                
                if missing_keywords:
                    optimized_title += f" - {missing_keywords[0]}"
            
            # Ensure title length is appropriate
            if len(optimized_title) < 20:
                optimized_title += " - Sprawdź opis!"
            elif len(optimized_title) > 80:
                optimized_title = optimized_title[:77] + "..."
            
            return optimized_title
            
        except Exception as e:
            logger.error(f"Title optimization failed: {e}")
            return title
    
    async def _optimize_description_text(self, description: str, category: str, analysis: Dict[str, Any]) -> str:
        """Optimize description text"""
        try:
            optimized_description = description
            
            # Add missing sections
            missing_elements = analysis.get("missing_elements", [])
            for element in missing_elements:
                if element == "opis":
                    optimized_description += "\n\nOPIS:\nSzczegółowy opis przedmiotu znajduje się powyżej."
                elif element == "stan":
                    optimized_description += "\n\nSTAN:\nPrzedmiot w stanie opisanym w tytule."
                elif element == "wymiary":
                    optimized_description += "\n\nWYMIARY:\nWymiary dostępne na żądanie."
                elif element == "dostawa":
                    optimized_description += "\n\nDOSTAWA:\nWysyłka w ciągu 1-2 dni roboczych."
            
            # Add category-specific improvements
            if category == "elektronika":
                optimized_description += "\n\nUWAGA: Przedmiot testowany i sprawny."
            elif category == "moda":
                optimized_description += "\n\nUWAGA: Rozmiar i wymiary w opisie."
            
            return optimized_description
            
        except Exception as e:
            logger.error(f"Description text optimization failed: {e}")
            return description
    
    async def _calculate_seo_score(self, title: str, description: str, category: str) -> float:
        """Calculate SEO score for optimized content"""
        try:
            score = 0.0
            
            # Title score (40%)
            if 20 <= len(title) <= 80:
                score += 0.4
            elif 10 <= len(title) < 20:
                score += 0.2
            
            # Description score (40%)
            if 100 <= len(description) <= 500:
                score += 0.4
            elif 50 <= len(description) < 100:
                score += 0.2
            
            # Keywords score (20%)
            if category in self.optimization_rules["title_keywords"]:
                required_keywords = self.optimization_rules["title_keywords"][category]
                found_keywords = sum(1 for kw in required_keywords if kw in title.lower() or kw in description.lower())
                score += (found_keywords / len(required_keywords)) * 0.2
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"SEO score calculation failed: {e}")
            return 0.0
    
    async def _generate_optimization_suggestions(self, analysis: Dict[str, Any], seo_score: float) -> List[str]:
        """Generate optimization suggestions"""
        try:
            suggestions = []
            
            # Title suggestions
            if analysis["title_length"] < 20:
                suggestions.append("Dodaj więcej szczegółów do tytułu")
            elif analysis["title_length"] > 80:
                suggestions.append("Skróć tytuł - powinien być zwięzły")
            
            # Description suggestions
            if analysis["description_length"] < 100:
                suggestions.append("Rozszerz opis - dodaj więcej szczegółów")
            elif analysis["description_length"] > 500:
                suggestions.append("Skróć opis - może być zbyt długi")
            
            # Missing elements suggestions
            missing_elements = analysis.get("missing_elements", [])
            for element in missing_elements:
                suggestions.append(f"Dodaj sekcję: {element}")
            
            # SEO score suggestions
            if seo_score < 0.5:
                suggestions.append("Popraw SEO - dodaj więcej słów kluczowych")
            elif seo_score < 0.8:
                suggestions.append("Dobra optymalizacja SEO - możesz jeszcze poprawić")
            else:
                suggestions.append("Doskonała optymalizacja SEO!")
            
            return suggestions[:5]  # Limit to 5 suggestions
            
        except Exception as e:
            logger.error(f"Optimization suggestions generation failed: {e}")
            return []
    
    async def _analyze_image_quality(self, image_file: str) -> Dict[str, Any]:
        """Analyze image quality"""
        try:
            # Simulate image analysis
            analysis = {
                "resolution": "1920x1080",
                "brightness": 0.7,
                "contrast": 0.8,
                "sharpness": 0.6,
                "color_balance": 0.9,
                "overall_quality": 0.75
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Image quality analysis failed: {e}")
            return {}
    
    async def _apply_image_enhancements(self, image_file: str, enhancements: List[str], analysis: Dict[str, Any]) -> str:
        """Apply image enhancements"""
        try:
            # Simulate image enhancement
            enhanced_image = f"enhanced_{image_file}"
            
            # Log applied enhancements
            for enhancement in enhancements:
                logger.info(f"Applied enhancement: {enhancement}")
            
            return enhanced_image
            
        except Exception as e:
            logger.error(f"Image enhancement application failed: {e}")
            return image_file
    
    async def _calculate_quality_score(self, enhanced_image: str, analysis: Dict[str, Any]) -> float:
        """Calculate enhanced image quality score"""
        try:
            base_quality = analysis.get("overall_quality", 0.5)
            
            # Simulate quality improvement
            quality_improvement = 0.2  # 20% improvement
            
            return min(base_quality + quality_improvement, 1.0)
            
        except Exception as e:
            logger.error(f"Quality score calculation failed: {e}")
            return 0.5
    
    async def _generate_improvements_list(self, enhancements: List[str], analysis: Dict[str, Any]) -> List[str]:
        """Generate list of improvements made"""
        try:
            improvements = []
            
            for enhancement in enhancements:
                if enhancement == "brightness":
                    improvements.append("Poprawiono jasność obrazu")
                elif enhancement == "contrast":
                    improvements.append("Zwiększono kontrast")
                elif enhancement == "sharpness":
                    improvements.append("Wyostrzono obraz")
                elif enhancement == "color_balance":
                    improvements.append("Poprawiono balans kolorów")
                elif enhancement == "background_removal":
                    improvements.append("Usunięto tło")
                elif enhancement == "noise_reduction":
                    improvements.append("Usunięto szumy")
            
            return improvements
            
        except Exception as e:
            logger.error(f"Improvements list generation failed: {e}")
            return []
    
    async def _analyze_sentiment(self, feedback_text: str, rating: int) -> Dict[str, Any]:
        """Analyze feedback sentiment"""
        try:
            # Simple sentiment analysis
            positive_words = ["dobry", "świetny", "polecam", "szybko", "sprawnie", "profesjonalnie"]
            negative_words = ["zły", "okropny", "nie polecam", "wolno", "problemy", "nieprofesjonalnie"]
            
            text_lower = feedback_text.lower()
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            if positive_count > negative_count:
                sentiment = "pozytywny"
                confidence = 0.8
            elif negative_count > positive_count:
                sentiment = "negatywny"
                confidence = 0.8
            else:
                sentiment = "neutralny"
                confidence = 0.6
            
            # Adjust based on rating
            if rating >= 4:
                sentiment = "pozytywny"
                confidence = 0.9
            elif rating <= 2:
                sentiment = "negatywny"
                confidence = 0.9
            
            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "positive_indicators": positive_count,
                "negative_indicators": negative_count
            }
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {"sentiment": "neutralny", "confidence": 0.5}
    
    async def _extract_key_points(self, feedback_text: str, sentiment_analysis: Dict[str, Any]) -> List[str]:
        """Extract key points from feedback"""
        try:
            key_points = []
            
            # Extract sentences with key information
            sentences = feedback_text.split('.')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 10:  # Meaningful sentences
                    # Check for key indicators
                    if any(word in sentence.lower() for word in ["szybko", "wolno", "długo", "krótko"]):
                        key_points.append(f"Czas: {sentence}")
                    elif any(word in sentence.lower() for word in ["dobry", "zły", "jakość", "stan"]):
                        key_points.append(f"Jakość: {sentence}")
                    elif any(word in sentence.lower() for word in ["komunikacja", "kontakt", "odpowiedź"]):
                        key_points.append(f"Komunikacja: {sentence}")
                    elif any(word in sentence.lower() for word in ["dostawa", "wysyłka", "paczką"]):
                        key_points.append(f"Dostawa: {sentence}")
            
            return key_points[:5]  # Limit to 5 key points
            
        except Exception as e:
            logger.error(f"Key points extraction failed: {e}")
            return []
    
    async def _generate_feedback_suggestions(self, sentiment_analysis: Dict[str, Any], key_points: List[str], context: str) -> List[str]:
        """Generate suggestions based on feedback analysis"""
        try:
            suggestions = []
            sentiment = sentiment_analysis.get("sentiment", "neutralny")
            
            if sentiment == "pozytywny":
                suggestions.extend([
                    "Kontynuuj obecne praktyki - klienci są zadowoleni",
                    "Rozważ prośbę o więcej szczegółowych opinii",
                    "Wykorzystaj pozytywne opinie w marketingu"
                ])
            elif sentiment == "negatywny":
                suggestions.extend([
                    "Przeanalizuj problemy wspomniane w opiniach",
                    "Popraw komunikację z klientami",
                    "Rozważ wprowadzenie zmian w procesie sprzedaży"
                ])
            else:  # neutralny
                suggestions.extend([
                    "Poproś o bardziej szczegółowe opinie",
                    "Zapytaj klientów o sugestie ulepszeń",
                    "Monitoruj opinie regularnie"
                ])
            
            # Context-specific suggestions
            if "dostawa" in context.lower():
                suggestions.append("Sprawdź proces dostawy i komunikację z kurierami")
            elif "jakość" in context.lower():
                suggestions.append("Przeanalizuj jakość produktów i opisy")
            
            return suggestions[:5]  # Limit to 5 suggestions
            
        except Exception as e:
            logger.error(f"Feedback suggestions generation failed: {e}")
            return []
    
    async def _analyze_category_timing(self, category: str) -> Dict[str, Any]:
        """Analyze timing patterns for category"""
        try:
            if category in self.category_data:
                return self.category_data[category]
            else:
                return {
                    "peak_hours": ["19:00-21:00"],
                    "best_days": ["niedziela"],
                    "seasonal_factors": {}
                }
                
        except Exception as e:
            logger.error(f"Category timing analysis failed: {e}")
            return {}
    
    async def _calculate_optimal_times(self, category: str, item_value: float, urgency: str, timing_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate optimal auction times"""
        try:
            optimal_times = []
            
            # Get peak hours
            peak_hours = timing_patterns.get("peak_hours", ["19:00-21:00"])
            best_days = timing_patterns.get("best_days", ["niedziela"])
            
            # Generate time slots
            for day in best_days:
                for time_slot in peak_hours:
                    # Calculate score based on various factors
                    score = 0.8  # Base score
                    
                    # Adjust for item value
                    if item_value > 1000:
                        score += 0.1  # Higher value items do better in peak times
                    
                    # Adjust for urgency
                    if urgency == "high":
                        score += 0.1
                    elif urgency == "low":
                        score -= 0.1
                    
                    optimal_times.append({
                        "day": day,
                        "time": time_slot,
                        "score": score,
                        "reason": f"Optymalny czas dla kategorii {category}"
                    })
            
            # Sort by score
            optimal_times.sort(key=lambda x: x["score"], reverse=True)
            
            return optimal_times[:5]  # Top 5 times
            
        except Exception as e:
            logger.error(f"Optimal times calculation failed: {e}")
            return []
    
    async def _generate_timing_recommendations(self, optimal_times: List[Dict[str, Any]], urgency: str) -> List[str]:
        """Generate timing recommendations"""
        try:
            recommendations = []
            
            if optimal_times:
                best_time = optimal_times[0]
                recommendations.append(f"Najlepszy czas: {best_time['day']} {best_time['time']}")
            
            # Urgency-based recommendations
            if urgency == "high":
                recommendations.append("Wysoka pilność - rozważ wystawienie w najbliższym możliwym czasie")
            elif urgency == "low":
                recommendations.append("Niska pilność - możesz poczekać na optymalny czas")
            else:
                recommendations.append("Normalna pilność - wybierz jeden z zalecanych terminów")
            
            # General recommendations
            recommendations.extend([
                "Unikaj wystawiania w święta i długie weekendy",
                "Sprawdź kalendarz - unikaj konfliktów z ważnymi wydarzeniami",
                "Rozważ wystawienie na 7 dni - daje więcej czasu na licytację"
            ])
            
            return recommendations[:5]  # Limit to 5 recommendations
            
        except Exception as e:
            logger.error(f"Timing recommendations generation failed: {e}")
            return []
    
    async def cleanup(self):
        """Cleanup AI auction manager"""
        try:
            logger.info("AI Auction Manager cleaned up successfully")
        except Exception as e:
            logger.error(f"AI Auction Manager cleanup failed: {e}")