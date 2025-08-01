from typing import Dict, List, Optional
from app.schemas import FinalBrief, ContextSummary
from datetime import datetime, timedelta
import logging
import threading
_user_histories: Dict[str, List[FinalBrief]] = {}
_lock = threading.Lock()

class ContextService:
    """Service for managing user context and history"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # In-memory storage for development (should be replaced with database in production)
        self.user_histories = _user_histories
        self._lock = _lock
        self.max_history_items = 10  # Keep last 10 briefs per user
        self.max_history_age_days = 30  # Keep history for 30 days
    
    def store_brief(self, user_id: str, brief: FinalBrief) -> None:
        """Store a completed brief in user's history"""
        
        if user_id not in self.user_histories:
            self.user_histories[user_id] = []
        
        # Add the new brief
        self.user_histories[user_id].append(brief)
        # print(f"Stored Content:{brief}")
        
        # Clean up old entries
        # self._cleanup_user_history(user_id)
        
        self.logger.info(f"Stored brief for user {user_id}. History size: {len(self.user_histories[user_id])}")
    
    def get_context_summary(self, user_id: str, current_topic: str) -> Optional[ContextSummary]:
        """Generate context summary from user's history"""
        
        if user_id not in self.user_histories or not self.user_histories[user_id]:
            return None
        
        history = self.user_histories[user_id]
        
        # Extract relevant information from history
        previous_topics = [brief.topic for brief in history]
        
        # Collect key insights from previous briefs
        all_key_findings = []
        all_recommendations = []
        
        for brief in history:
            all_key_findings.extend(brief.key_findings)
            all_recommendations.extend(brief.recommendations)
        
        # Find most relevant insights (simple keyword matching for now)
        relevant_insights = self._find_relevant_insights(
            current_topic, all_key_findings, all_recommendations
        )
        
        # Calculate context relevance
        relevance = self._calculate_context_relevance(current_topic, previous_topics)
        
        return ContextSummary(
            user_id=user_id,
            previous_topics=previous_topics[-5:],  # Last 5 topics
            key_insights=relevant_insights[:8],     # Top 8 relevant insights
            related_findings=all_key_findings[-10:],  # Last 10 findings
            context_relevance=relevance
        )
    
    def _cleanup_user_history(self, user_id: str) -> None:
        """Clean up old history entries"""
        
        history = self.user_histories[user_id]
        cutoff_date = datetime.now() - timedelta(days=self.max_history_age_days)
        
        # Remove old entries
        recent_history = [
            brief for brief in history 
            if brief.generated_at >= cutoff_date
        ]
        
        # Keep only the most recent entries
        if len(recent_history) > self.max_history_items:
            recent_history = recent_history[-self.max_history_items:]
        
        self.user_histories[user_id] = recent_history
    
    def _find_relevant_insights(
        self, 
        current_topic: str, 
        key_findings: List[str], 
        recommendations: List[str]
    ) -> List[str]:
        """Find insights relevant to current topic using keyword matching"""
        
        current_keywords = set(current_topic.lower().split())
        relevant_insights = []
        
        # Score insights based on keyword overlap
        all_insights = key_findings + recommendations
        scored_insights = []
        
        for insight in all_insights:
            insight_keywords = set(insight.lower().split())
            overlap = len(current_keywords.intersection(insight_keywords))
            if overlap > 0:
                scored_insights.append((insight, overlap))
        
        # Sort by relevance score and return top insights
        scored_insights.sort(key=lambda x: x[1], reverse=True)
        return [insight for insight, score in scored_insights[:8]]
    
    def _calculate_context_relevance(self, current_topic: str, previous_topics: List[str]) -> float:
        """Calculate how relevant the context is to the current topic"""
        
        if not previous_topics:
            return 0.0
        
        current_keywords = set(current_topic.lower().split())
        total_relevance = 0.0
        
        for topic in previous_topics:
            topic_keywords = set(topic.lower().split())
            overlap = len(current_keywords.intersection(topic_keywords))
            topic_relevance = overlap / len(current_keywords.union(topic_keywords))
            total_relevance += topic_relevance
        
        return min(total_relevance / len(previous_topics), 1.0)
    
    def get_user_history_summary(self, user_id: str) -> Dict:
        """Get a summary of user's research history"""
        
        if user_id not in self.user_histories:
            return {"total_briefs": 0, "topics": [], "recent_activity": None}
        
        history = self.user_histories[user_id]
        
        return {
            "total_briefs": len(history),
            "topics": [brief.topic for brief in history],
            "recent_activity": history[-1].generated_at if history else None,
            "avg_confidence": sum(brief.confidence_level for brief in history) / len(history) if history else 0.0
        }