from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class BriefRequest(BaseModel):
    topic: str = Field(..., description="Research topic")
    depth: int = Field(default=3, ge=1, le=5, description="Research depth (1-5)")
    follow_up: bool = Field(default=False, description="Is this a follow-up query")
    user_id: str = Field(..., description="User identifier")

class ResearchPlan(BaseModel):
    topic: str
    subtopics: List[str] = Field(..., min_items=1, max_items=10)
    search_queries: List[str] = Field(..., min_items=1, max_items=15)
    focus_areas: List[str] = Field(..., min_items=1, max_items=8)
    estimated_sources: int = Field(..., ge=1, le=20)

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)

class SourceSummary(BaseModel):
    url: str
    title: str
    key_points: List[str] = Field(..., min_items=1, max_items=10)
    relevance_to_topic: str
    credibility_assessment: str
    summary: str = Field(..., min_length=50, max_length=5000)
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class Reference(BaseModel):
    title: str
    url: Optional[str] = None 
    summary: str
    relevance: str

class FinalBrief(BaseModel):
    topic: str
    executive_summary: str = Field(..., min_length=100, max_length=5000)
    key_findings: List[str] = Field(..., min_items=3, max_items=10)
    detailed_analysis: str = Field(..., min_length=300, max_length=5000)
    recommendations: List[str] = Field(..., min_items=2, max_items=8)
    references: List[Reference] = Field(..., min_items=1, max_items=15)
    confidence_level: float = Field(..., ge=0.0, le=1.0)
    generated_at: datetime = Field(default_factory=datetime.now)
    context_used: bool = Field(default=False)

class ContextSummary(BaseModel):
    user_id: str
    previous_topics: List[str]
    key_insights: List[str]
    related_findings: List[str]
    context_relevance: float = Field(..., ge=0.0, le=1.0)

class GraphState(BaseModel):
    request: BriefRequest
    context_summary: Optional[ContextSummary] = None
    research_plan: Optional[ResearchPlan] = None
    search_results: List[SearchResult] = []
    source_summaries: List[SourceSummary] = []
    final_brief: Optional[FinalBrief] = None
    error: Optional[str] = None
    retry_count: int = 0
    
    class Config:
        arbitrary_types_allowed = True