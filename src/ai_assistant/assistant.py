from flask import current_app
from sqlalchemy.orm import Session
import numpy as np
from typing import Dict, List, Optional

from src.models import User, Message, Notification, AIInsight
from src.utils.ml_models import TextAnalyzer, InsightGenerator

class AIAssistant:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.text_analyzer = TextAnalyzer()
        self.insight_generator = InsightGenerator()
        
    def deliver_message(self, user_id: int, content: str, priority: str = "normal") -> Message:
        user = self.db.query(User).get(user_id)
        sentiment = self.text_analyzer.analyze_sentiment(content)
        
        message = Message(
            user_id=user_id,
            content=content,
            priority=priority,
            sentiment=sentiment
        )
        self.db.add(message)
        self.db.commit()
        
        return message

    def manage_notifications(self, user_id: int) -> List[Notification]:
        user = self.db.query(User).get(user_id)
        pending_notifications = self.db.query(Notification)\
            .filter_by(user_id=user_id, status="pending")\
            .all()
            
        for notification in pending_notifications:
            notification.status = "delivered"
            
        self.db.commit()
        return pending_notifications

    def provide_ai_insight(self, user_id: int, data_context: Dict) -> AIInsight:
        user = self.db.query(User).get(user_id)
        
        analysis_result = self.insight_generator.generate(
            user_data=data_context.get("user_data"),
            business_context=data_context.get("business_context"),
            historical_data=data_context.get("historical_data")
        )
        
        insight = AIInsight(
            user_id=user_id,
            content=analysis_result["content"],
            confidence_score=analysis_result["confidence"],
            category=analysis_result["category"]
        )
        
        self.db.add(insight)
        self.db.commit()
        
        return insight

    def get_character_model(self, action_type: str) -> str:
        character_models = {
            "message": "postman.glb",
            "notification": "boss.glb",
            "insight": "advisor.glb"
        }
        return character_models.get(action_type, "advisor.glb")

    def get_assistant_state(self, user_id: int) -> Dict:
        return {
            "pending_messages": self.db.query(Message).filter_by(user_id=user_id, status="pending").count(),
            "pending_notifications": self.db.query(Notification).filter_by(user_id=user_id, status="pending").count(),
            "recent_insights": self.db.query(AIInsight).filter_by(user_id=user_id).order_by(AIInsight.created_at.desc()).limit(5).all()
        }