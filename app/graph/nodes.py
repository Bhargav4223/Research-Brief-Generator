from typing import Dict, Any
from app.graph.state import ResearchBriefState
from app.services.llm_service import LLMService
from app.services.search_service import SearchService
from app.services.context_service import ContextService
from app.schemas import (
    ResearchPlan, SourceSummary, FinalBrief, 
    SearchResult, Reference
)
import logging

class ResearchNodes:
    """Collection of nodes for the research brief generation workflow"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.search_service = SearchService()
        self.context_service = ContextService()
        self.logger = logging.getLogger(__name__)
    
    async def context_summarization_node(self, state: ResearchBriefState) -> Dict[str, Any]:
        """Node for summarizing previous user context"""
        
        self.logger.info("Processing context summarization")
        
        try:
            if state["request"].follow_up:
                context_summary = self.context_service.get_context_summary(
                    state["request"].user_id,
                    state["request"].topic
                )
                return {
                    "context_summary": context_summary,
                    "processing_stage": "context_completed"
                }
            else:
                return {
                    "context_summary": None,
                    "processing_stage": "context_completed"
                }
                
        except Exception as e:
            self.logger.error(f"Context summarization failed: {str(e)}")
            return {
                "error": f"Context summarization failed: {str(e)}",
                "processing_stage": "context_failed"
            }
    
    async def planning_node(self, state: ResearchBriefState) -> Dict[str, Any]:
        """Node for creating research plan"""
        
        self.logger.info("Processing research planning")
        
        try:
            topic = state["request"].topic
            depth = state["request"].depth
            context = state.get("context_summary")
            
            # Build planning prompt
            context_text = ""
            if context and context.context_relevance > 0.3:
                context_text = f"""
                PREVIOUS RESEARCH CONTEXT:
                - Previous topics: {', '.join(context.previous_topics)}
                - Key insights: {'; '.join(context.key_insights[:3])}
                - Context relevance: {context.context_relevance:.2f}
                """
            
            planning_prompt = f"""
            Create a comprehensive research plan for the topic: "{topic}"
            
            Research depth level: {depth} (1=basic, 5=comprehensive)
            
            {context_text}
            
            Generate a structured research plan that includes:
            1. 3-8 relevant subtopics to explore
            2. 5-12 specific search queries to execute
            3. 3-6 key focus areas for analysis
            4. Estimated number of sources needed (5-15)
            
            Ensure the plan is thorough yet focused, avoiding overly broad or narrow scopes.
            """
            
            research_plan = await self.llm_service.generate_structured_output(
                planning_prompt,
                ResearchPlan,
                context=context_text if context_text else None
            )
            
            return {
                "research_plan": research_plan,
                "processing_stage": "planning_completed"
            }
            
        except Exception as e:
            self.logger.error(f"Planning failed: {str(e)}")
            return {
                "error": f"Planning failed: {str(e)}",
                "processing_stage": "planning_failed"
            }
    
    async def search_node(self, state: ResearchBriefState) -> Dict[str, Any]:
        """Node for executing web searches"""
        
        self.logger.info("Processing web search")
        
        try:
            research_plan = state.get("research_plan")
            if not research_plan:
                raise ValueError("No research plan available")
            
            # Execute searches
            search_results = await self.search_service.search_multiple_queries(
                research_plan.search_queries
            )
            
            self.logger.info(f"Retrieved {len(search_results)} search results")
            
            return {
                "search_results": search_results,
                "processing_stage": "search_completed"
            }
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            return {
                "error": f"Search failed: {str(e)}",
                "processing_stage": "search_failed"
            }
    
    async def source_summarization_node(self, state: ResearchBriefState) -> Dict[str, Any]:
        """Node for summarizing individual sources"""
        
        self.logger.info("Processing source summarization")
        
        try:
            search_results = state.get("search_results", [])
            topic = state["request"].topic
            
            if not search_results:
                raise ValueError("No search results available")
            
            source_summaries = []
            
            # Process top results (limit to avoid excessive processing)
            top_results = search_results[:min(10, len(search_results))]
            
            for result in top_results:
                try:
                    summary_prompt = f"""
                    Analyze this search result for the research topic: "{topic}"
                    
                    Source Title: {result.title}
                    Source URL: {result.url}
                    Content Snippet: {result.snippet}
                    
                    Create a comprehensive source summary that includes:
                    1. 3-8 key points from this source
                    2. Relevance assessment to the main topic
                    3. Credibility assessment (based on source type, content quality)
                    4. A concise summary (100-400 words)
                    5. Confidence score for the information quality
                    
                    Focus on extracting actionable insights and factual information.
                    """
                    
                    source_summary = await self.llm_service.generate_structured_output(
                        summary_prompt,
                        SourceSummary,
                        use_fast_model=True  # Use faster model for individual summaries
                    )
                    
                    source_summaries.append(source_summary)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to summarize source {result.url}: {str(e)}")
                    continue
            
            self.logger.info(f"Successfully summarized {len(source_summaries)} sources")
            
            return {
                "source_summaries": source_summaries,
                "total_sources_processed": len(source_summaries),
                "processing_stage": "summarization_completed"
            }
            
        except Exception as e:
            self.logger.error(f"Source summarization failed: {str(e)}")
            return {
                "error": f"Source summarization failed: {str(e)}",
                "processing_stage": "summarization_failed"
            }
    
    async def synthesis_node(self, state: ResearchBriefState) -> Dict[str, Any]:
        """Node for synthesizing final brief"""
        
        self.logger.info("Processing synthesis")
        
        try:
            topic = state["request"].topic
            research_plan = state.get("research_plan")
            source_summaries = state.get("source_summaries", [])
            context_summary = state.get("context_summary")
            
            if not source_summaries:
                raise ValueError("No source summaries available")
            
            # Prepare context for synthesis
            context_text = ""
            if context_summary and context_summary.context_relevance > 0.3:
                context_text = f"""
                PREVIOUS RESEARCH CONTEXT:
                Building on previous research into: {', '.join(context_summary.previous_topics)}
                Key insights from previous work: {'; '.join(context_summary.key_insights[:3])}
                """
            
            # Prepare source content
            source_content = []
            references = []
            
            for summary in source_summaries:
                source_content.append(f"""
                Source: {summary.title}
                Key Points: {'; '.join(summary.key_points)}
                Summary: {summary.summary}
                Relevance: {summary.relevance_to_topic}
                """)
                
                references.append(Reference(
                    title=summary.title,
                    url=summary.url,
                    summary=summary.summary[:200] + "..." if len(summary.summary) > 200 else summary.summary,
                    relevance=summary.relevance_to_topic
                ))
            
            synthesis_prompt = f"""
            Create a comprehensive research brief on: "{topic}"
            
            {context_text}
            
            RESEARCH PLAN FOCUS:
            Focus Areas: {', '.join(research_plan.focus_areas) if research_plan else 'General analysis'}
            
            SOURCE MATERIALS:
            {chr(10).join(source_content)}
            
            Generate a complete research brief with:
            1. Executive summary (150-250 words) - high-level overview
            2. Key findings (4-8 points) - most important discoveries
            3. Detailed analysis (500-1500 words) - comprehensive examination
            4. Recommendations (3-6 points) - actionable insights
            5. Confidence level (0.0-1.0) - overall confidence in findings
            
            Ensure the brief is:
            - Evidence-based and factually accurate
            - Well-structured and professionally written
            - Actionable and insightful
            - Appropriately cites the research sources
            """
            
            # Generate the final brief structure (without references first)
            brief_data = await self.llm_service.generate_structured_output(
                synthesis_prompt,
                FinalBrief,
                context=context_text if context_text else None
            )
            
            # Add references and metadata
            final_brief = FinalBrief(
                topic=brief_data.topic,
                executive_summary=brief_data.executive_summary,
                key_findings=brief_data.key_findings,
                detailed_analysis=brief_data.detailed_analysis,
                recommendations=brief_data.recommendations,
                references=references,
                confidence_level=brief_data.confidence_level,
                context_used=context_summary is not None and context_summary.context_relevance > 0.3
            )
            
            # Store in user context for future reference
            self.context_service.store_brief(state["request"].user_id, final_brief)
            
            return {
                "final_brief": final_brief,
                "processing_stage": "synthesis_completed"
            }
            
        except Exception as e:
            self.logger.error(f"Synthesis failed: {str(e)}")
            return {
                "error": f"Synthesis failed: {str(e)}",
                "processing_stage": "synthesis_failed"
            }
    
    async def post_processing_node(self, state: ResearchBriefState) -> Dict[str, Any]:
        """Node for final post-processing and validation"""
        
        self.logger.info("Processing post-processing")
        
        try:
            final_brief = state.get("final_brief")
            if not final_brief:
                raise ValueError("No final brief available")
            
            # Validate the brief meets quality standards
            quality_score = self._assess_brief_quality(final_brief)
            
            if quality_score < 0.6:
                self.logger.warning(f"Brief quality score {quality_score} below threshold")
                # Could trigger regeneration or enhancement here
            
            return {
                "final_brief": final_brief,
                "processing_stage": "completed"
            }
            
        except Exception as e:
            self.logger.error(f"Post-processing failed: {str(e)}")
            return {
                "error": f"Post-processing failed: {str(e)}",
                "processing_stage": "post_processing_failed"
            }
    
    def _assess_brief_quality(self, brief: FinalBrief) -> float:
        """Assess the quality of the generated brief"""
        
        quality_factors = []
        
        # Length checks
        quality_factors.append(1.0 if len(brief.executive_summary) >= 100 else 0.5)
        quality_factors.append(1.0 if len(brief.detailed_analysis) >= 300 else 0.5)
        quality_factors.append(1.0 if len(brief.key_findings) >= 3 else 0.5)
        quality_factors.append(1.0 if len(brief.recommendations) >= 2 else 0.5)
        quality_factors.append(1.0 if len(brief.references) >= 1 else 0.0)
        
        # Content quality
        quality_factors.append(brief.confidence_level)
        
        return sum(quality_factors) / len(quality_factors)