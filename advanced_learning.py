#!/usr/bin/env python3
"""
Advanced Learning Manager
Zaawansowane uczenie AI na podstawie interakcji użytkownika
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio

logger = logging.getLogger(__name__)

class AdvancedLearningManager:
    """Manager for advanced AI learning from user interactions"""
    
    def __init__(self):
        self.learning_data = {}
        self.user_patterns = {}
        self.interaction_history = []
        self.feedback_scores = {}
        
    async def initialize(self):
        """Initialize the learning manager"""
        try:
            logger.info("Initializing Advanced Learning Manager...")
            # Load existing learning data
            await self.load_learning_data()
            logger.info("Advanced Learning Manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Advanced Learning Manager: {e}")
            raise
    
    async def learn_from_interaction(self, user_id: str, interaction_type: str, 
                                   data: Dict[str, Any], feedback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Learn from user interaction"""
        try:
            # Store interaction data
            interaction = {
                "user_id": user_id,
                "interaction_type": interaction_type,
                "data": data,
                "feedback": feedback,
                "timestamp": datetime.now().isoformat()
            }
            
            self.interaction_history.append(interaction)
            
            # Analyze interaction patterns
            patterns = await self.analyze_interaction_patterns(user_id, interaction)
            
            # Update user preferences
            await self.update_user_preferences(user_id, interaction)
            
            # Generate insights
            insights = await self.generate_insights(user_id, interaction)
            
            # Generate recommendations
            recommendations = await self.generate_recommendations(user_id, patterns)
            
            # Store learning data
            await self.store_learning_data(user_id, interaction, patterns, insights)
            
            return {
                "success": True,
                "insights": insights,
                "recommendations": recommendations,
                "patterns": patterns
            }
            
        except Exception as e:
            logger.error(f"Learning from interaction failed: {e}")
            return {
                "success": False,
                "insights": {},
                "recommendations": [],
                "error": str(e)
            }
    
    async def analyze_interaction_patterns(self, user_id: str, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user interaction patterns"""
        try:
            patterns = {
                "frequency": {},
                "preferences": {},
                "behavior": {},
                "context": {}
            }
            
            # Analyze frequency patterns
            user_interactions = [i for i in self.interaction_history if i["user_id"] == user_id]
            interaction_types = [i["interaction_type"] for i in user_interactions]
            
            for interaction_type in set(interaction_types):
                patterns["frequency"][interaction_type] = interaction_types.count(interaction_type)
            
            # Analyze preferences
            if "preferences" in interaction["data"]:
                patterns["preferences"] = interaction["data"]["preferences"]
            
            # Analyze behavior patterns
            if "behavior" in interaction["data"]:
                patterns["behavior"] = interaction["data"]["behavior"]
            
            # Analyze context
            if "context" in interaction["data"]:
                patterns["context"] = interaction["data"]["context"]
            
            return patterns
            
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            return {}
    
    async def update_user_preferences(self, user_id: str, interaction: Dict[str, Any]):
        """Update user preferences based on interaction"""
        try:
            if user_id not in self.user_patterns:
                self.user_patterns[user_id] = {
                    "preferences": {},
                    "behavior": {},
                    "interests": [],
                    "last_updated": datetime.now().isoformat()
                }
            
            # Update preferences
            if "preferences" in interaction["data"]:
                self.user_patterns[user_id]["preferences"].update(interaction["data"]["preferences"])
            
            # Update behavior
            if "behavior" in interaction["data"]:
                self.user_patterns[user_id]["behavior"].update(interaction["data"]["behavior"])
            
            # Update interests
            if "interests" in interaction["data"]:
                interests = interaction["data"]["interests"]
                if isinstance(interests, list):
                    self.user_patterns[user_id]["interests"].extend(interests)
                else:
                    self.user_patterns[user_id]["interests"].append(interests)
            
            # Remove duplicates
            self.user_patterns[user_id]["interests"] = list(set(self.user_patterns[user_id]["interests"]))
            
            # Update timestamp
            self.user_patterns[user_id]["last_updated"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"User preferences update failed: {e}")
    
    async def generate_insights(self, user_id: str, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from interaction"""
        try:
            insights = {
                "user_engagement": 0.0,
                "preference_strength": 0.0,
                "behavior_consistency": 0.0,
                "context_relevance": 0.0,
                "learning_potential": 0.0
            }
            
            # Calculate user engagement
            user_interactions = [i for i in self.interaction_history if i["user_id"] == user_id]
            recent_interactions = [i for i in user_interactions 
                                 if datetime.fromisoformat(i["timestamp"]) > datetime.now() - timedelta(days=7)]
            
            insights["user_engagement"] = min(len(recent_interactions) / 10.0, 1.0)
            
            # Calculate preference strength
            if user_id in self.user_patterns:
                preferences = self.user_patterns[user_id].get("preferences", {})
                insights["preference_strength"] = min(len(preferences) / 20.0, 1.0)
            
            # Calculate behavior consistency
            if len(user_interactions) > 1:
                behavior_types = [i["interaction_type"] for i in user_interactions]
                most_common = max(set(behavior_types), key=behavior_types.count)
                consistency = behavior_types.count(most_common) / len(behavior_types)
                insights["behavior_consistency"] = consistency
            
            # Calculate context relevance
            if "context" in interaction["data"]:
                context = interaction["data"]["context"]
                insights["context_relevance"] = min(len(str(context)) / 100.0, 1.0)
            
            # Calculate learning potential
            insights["learning_potential"] = (
                insights["user_engagement"] * 0.3 +
                insights["preference_strength"] * 0.3 +
                insights["behavior_consistency"] * 0.2 +
                insights["context_relevance"] * 0.2
            )
            
            return insights
            
        except Exception as e:
            logger.error(f"Insights generation failed: {e}")
            return {}
    
    async def generate_recommendations(self, user_id: str, patterns: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on patterns"""
        try:
            recommendations = []
            
            # Based on frequency patterns
            if patterns.get("frequency"):
                most_used = max(patterns["frequency"].items(), key=lambda x: x[1])
                recommendations.append(f"Consider using {most_used[0]} more frequently - you seem to prefer it")
            
            # Based on preferences
            if patterns.get("preferences"):
                pref_count = len(patterns["preferences"])
                if pref_count > 5:
                    recommendations.append("You have diverse preferences - consider exploring new features")
                else:
                    recommendations.append("Try exploring more features to discover new preferences")
            
            # Based on behavior
            if patterns.get("behavior"):
                recommendations.append("Your behavior patterns suggest you might benefit from personalized suggestions")
            
            # Based on context
            if patterns.get("context"):
                recommendations.append("Context-aware features could enhance your experience")
            
            # General recommendations
            if user_id in self.user_patterns:
                user_data = self.user_patterns[user_id]
                if len(user_data.get("interests", [])) > 10:
                    recommendations.append("You have many interests - consider organizing them into categories")
                elif len(user_data.get("interests", [])) < 3:
                    recommendations.append("Try exploring different topics to expand your interests")
            
            return recommendations[:5]  # Limit to 5 recommendations
            
        except Exception as e:
            logger.error(f"Recommendations generation failed: {e}")
            return []
    
    async def store_learning_data(self, user_id: str, interaction: Dict[str, Any], 
                                patterns: Dict[str, Any], insights: Dict[str, Any]):
        """Store learning data for future use"""
        try:
            learning_entry = {
                "user_id": user_id,
                "interaction": interaction,
                "patterns": patterns,
                "insights": insights,
                "timestamp": datetime.now().isoformat()
            }
            
            if user_id not in self.learning_data:
                self.learning_data[user_id] = []
            
            self.learning_data[user_id].append(learning_entry)
            
            # Keep only last 100 entries per user
            if len(self.learning_data[user_id]) > 100:
                self.learning_data[user_id] = self.learning_data[user_id][-100:]
            
        except Exception as e:
            logger.error(f"Learning data storage failed: {e}")
    
    async def load_learning_data(self):
        """Load existing learning data"""
        try:
            # In a real implementation, this would load from a database
            # For now, we'll start with empty data
            self.learning_data = {}
            self.user_patterns = {}
            self.interaction_history = []
            self.feedback_scores = {}
            
        except Exception as e:
            logger.error(f"Learning data loading failed: {e}")
    
    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights for a specific user"""
        try:
            if user_id not in self.learning_data:
                return {"message": "No learning data available for this user"}
            
            user_data = self.learning_data[user_id]
            patterns = self.user_patterns.get(user_id, {})
            
            return {
                "user_id": user_id,
                "total_interactions": len(user_data),
                "patterns": patterns,
                "recent_insights": user_data[-5:] if user_data else [],
                "last_updated": patterns.get("last_updated", "Never")
            }
            
        except Exception as e:
            logger.error(f"Get user insights failed: {e}")
            return {"error": str(e)}
    
    async def cleanup(self):
        """Cleanup learning manager"""
        try:
            # Save learning data
            await self.save_learning_data()
            logger.info("Advanced Learning Manager cleaned up successfully")
        except Exception as e:
            logger.error(f"Learning manager cleanup failed: {e}")
    
    async def save_learning_data(self):
        """Save learning data to persistent storage"""
        try:
            # In a real implementation, this would save to a database
            # For now, we'll just log the data
            logger.info(f"Learning data saved: {len(self.learning_data)} users")
        except Exception as e:
            logger.error(f"Learning data saving failed: {e}")