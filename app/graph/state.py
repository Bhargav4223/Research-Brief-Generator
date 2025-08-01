from typing import TypedDict, List, Optional, Annotated
from app.schemas import (
    BriefRequest, ContextSummary, ResearchPlan, 
    SearchResult, SourceSummary, FinalBrief
)
import operator

class ResearchBriefState(TypedDict):
    """Typed state for the research brief generation workflow"""
    request: BriefRequest
    context_summary: Optional[ContextSummary]
    research_plan: Optional[ResearchPlan]
    search_results: Annotated[List[SearchResult], operator.add]
    source_summaries: Annotated[List[SourceSummary], operator.add]
    final_brief: Optional[FinalBrief]
    error: Optional[str]
    retry_count: int
    
    # Additional metadata
    total_sources_processed: int
    processing_stage: str