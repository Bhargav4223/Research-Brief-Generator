from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.graph.state import ResearchBriefState
from app.graph.nodes import ResearchNodes
from app.schemas import BriefRequest
import logging
import asyncio
from langsmith.run_helpers import traceable   # NEW
from app.services.context_service import ContextService



class ResearchBriefWorkflow:
    """LangGraph workflow for research brief generation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.nodes = ResearchNodes()
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()
        self.context_service = ContextService()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create the state graph
        workflow = StateGraph(ResearchBriefState)
        
        # Add nodes
        workflow.add_node("context_summarization", self.nodes.context_summarization_node)
        workflow.add_node("planning", self.nodes.planning_node)
        workflow.add_node("search", self.nodes.search_node)
        workflow.add_node("source_summarization", self.nodes.source_summarization_node)
        workflow.add_node("synthesis", self.nodes.synthesis_node)
        workflow.add_node("post_processing", self.nodes.post_processing_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Define the workflow flow
        workflow.set_entry_point("context_summarization")
        
        # Context summarization -> Planning
        workflow.add_conditional_edges(
            "context_summarization",
            self._should_continue_after_context,
            {
                "continue": "planning",
                "error": "error_handler"
            }
        )
        
        # Planning -> Search
        workflow.add_conditional_edges(
            "planning",
            self._should_continue_after_planning,
            {
                "continue": "search",
                "error": "error_handler"
            }
        )
        
        # Search -> Source Summarization
        workflow.add_conditional_edges(
            "search",
            self._should_continue_after_search,
            {
                "continue": "source_summarization",
                "error": "error_handler"
            }
        )
        
        # Source Summarization -> Synthesis
        workflow.add_conditional_edges(
            "source_summarization",
            self._should_continue_after_summarization,
            {
                "continue": "synthesis",
                "retry": "search",  # Retry search if not enough sources
                "error": "error_handler"
            }
        )
        
        # Synthesis -> Post Processing
        workflow.add_conditional_edges(
            "synthesis",
            self._should_continue_after_synthesis,
            {
                "continue": "post_processing",
                "error": "error_handler"
            }
        )
        
        # Post Processing -> End
        workflow.add_edge("post_processing", END)
        workflow.add_edge("error_handler", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    def _should_continue_after_context(self, state: ResearchBriefState) -> str:
        """Determine next step after context summarization"""
        
        if state.get("error"):
            return "error"
        return "continue"
    
    def _should_continue_after_planning(self, state: ResearchBriefState) -> str:
        """Determine next step after planning"""
        
        if state.get("error"):
            return "error"
        
        research_plan = state.get("research_plan")
        if not research_plan or not research_plan.search_queries:
            return "error"
        
        return "continue"
    
    def _should_continue_after_search(self, state: ResearchBriefState) -> str:
        """Determine next step after search"""
        
        if state.get("error"):
            return "error"
        
        search_results = state.get("search_results", [])
        if len(search_results) < 2:  # Need at least 2 sources
            return "error"
        
        return "continue"
    
    def _should_continue_after_summarization(self, state: ResearchBriefState) -> str:
        """Determine next step after source summarization"""
        
        if state.get("error"):
            return "error"
        
        source_summaries = state.get("source_summaries", [])
        retry_count = state.get("retry_count", 0)
        
        # Need at least 2 good source summaries
        if len(source_summaries) < 2:
            if retry_count < 2:  # Allow up to 2 retries
                return "retry"
            else:
                return "error"
        
        return "continue"
    
    def _should_continue_after_synthesis(self, state: ResearchBriefState) -> str:
        """Determine next step after synthesis"""
        
        if state.get("error"):
            return "error"
        
        final_brief = state.get("final_brief")
        if not final_brief:
            return "error"
        
        return "continue"
    
    async def _error_handler_node(self, state: ResearchBriefState) -> Dict[str, Any]:
        """Handle errors and create fallback response"""
        
        error_msg = state.get("error", "Unknown error occurred")
        self.logger.error(f"Workflow error: {error_msg}")
        
        # Create a minimal fallback brief
        from app.schemas import FinalBrief, Reference
        from datetime import datetime
        
        fallback_brief = FinalBrief(
            topic=state["request"].topic,
            executive_summary=f"Unable to generate comprehensive research brief for '{state['request'].topic}' due to processing errors. This is a fallback response.",
            key_findings=[
                "Automated research generation encountered technical difficulties",
                "Manual research may be required for this topic",
                "System limitations prevented comprehensive analysis"
            ],
            detailed_analysis=f"The automated research system encountered errors while processing the topic '{state['request'].topic}'. This may be due to limited search results, processing failures, or system constraints. For comprehensive research on this topic, manual investigation is recommended.",
            recommendations=[
                "Conduct manual research using academic databases",
                "Consult subject matter experts",
                "Try rephrasing the research topic"
            ],
            references=[],
            confidence_level=0.1,
            context_used=False
        )
        
        return {
            "final_brief": fallback_brief,
            "processing_stage": "error_handled"
        }
    
    @traceable(run_type="tool", name="research_brief")
    async def execute(self, request: BriefRequest) -> Dict[str, Any]:
        """Execute the research brief generation workflow"""
        
        self.logger.info(f"Starting workflow for topic: {request.topic}")
        
        # Initialize state
        initial_state = ResearchBriefState(
            request=request,
            context_summary=None,
            research_plan=None,
            search_results=[],
            source_summaries=[],
            final_brief=None,
            error=None,
            retry_count=0,
            total_sources_processed=0,
            processing_stage="initialized"
        )
        
        try:
            # Create a unique thread ID for checkpointing
            thread_id = f"user_{request.user_id}_{hash(request.topic) % 10000}"
            config = {"configurable": {"thread_id": thread_id}}
            
            # Execute the workflow
            result = await self.graph.ainvoke(initial_state, config=config)
            
            self.logger.info(f"Workflow completed. Stage: {result.get('processing_stage')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {str(e)}")
            
            # Return error state
            return await self._error_handler_node(initial_state)
    
    def get_workflow_visualization(self) -> str:
        """Get a text representation of the workflow"""
        
        return """
        Research Brief Generation Workflow:
        
        1. Context Summarization
           ├─ Load user history
           ├─ Generate context summary
           └─ Assess relevance
           
        2. Planning
           ├─ Analyze topic and context
           ├─ Generate research plan
           └─ Create search queries
           
        3. Search
           ├─ Execute web searches
           ├─ Collect results
           └─ Rank by relevance
           
        4. Source Summarization
           ├─ Process each source
           ├─ Extract key insights
           └─ Assess credibility
           
        5. Synthesis
           ├─ Combine all sources
           ├─ Generate final brief
           └─ Add references
           
        6. Post Processing
           ├─ Quality validation
           ├─ Store in context
           └─ Return result
        """