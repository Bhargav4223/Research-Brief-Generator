# app/services/llm_service.py

import os
from typing import Type, TypeVar, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage, HumanMessage
from pydantic import BaseModel, ValidationError
import json
import asyncio
import logging
from app.utils.async_helpers import get_shared_event_loop
from datetime import datetime
from app.schemas import SourceSummary, FinalBrief # Import schemas for fallback

T = TypeVar('T', bound=BaseModel)

class LLMService:
    """Service for managing LLM interactions with structured outputs"""
    
    # def __init__(self):
    #     self.logger = logging.getLogger(__name__)
    #     loop = get_shared_event_loop()
    #     asyncio.set_event_loop(loop)
        
    #     self.primary_llm = ChatGoogleGenerativeAI(
    #         model="gemini-1.5-flash", temperature=0.3, google_api_key=os.getenv("GOOGLE_API_KEY")
    #     )
    #     self.fast_llm = ChatGoogleGenerativeAI(
    #         model="gemini-1.5-flash", temperature=0.1, google_api_key=os.getenv("GOOGLE_API_KEY")
    #     )
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Do NOT create clients here – do it lazily
        self._primary_llm = None
        self._fast_llm = None

    @property
    def primary_llm(self):
        if self._primary_llm is None:
            self._primary_llm = ChatGoogleGenerativeAI(
                model="gemma-3-27b-it",
                temperature=0.3,
                google_api_key=os.getenv("GOOGLE_API_KEY")
            )
        return self._primary_llm

    @property
    def fast_llm(self):
        if self._fast_llm is None:
            self._fast_llm = ChatGoogleGenerativeAI(
                model="gemma-3-27b-it",
                temperature=0.1,
                google_api_key=os.getenv("GOOGLE_API_KEY")
            )
        return self._fast_llm
    async def generate_structured_output(
        self, 
        prompt: str, 
        output_model: Type[T], 
        context: Optional[str] = None,
        use_fast_model: bool = False,
        max_retries: int = 3
    ) -> T:
        """
        Generate structured output with self-correction and retry logic.
        """
        parser = PydanticOutputParser(pydantic_object=output_model)
        full_prompt = self._build_prompt(prompt, parser.get_format_instructions(), context)
        llm = self.fast_llm if use_fast_model else self.primary_llm
        
        for attempt in range(max_retries):
            try:
                response = await llm.ainvoke([HumanMessage(content=full_prompt)])
                # Attempt to parse the object
                return parser.parse(response.content)
            
            except ValidationError as e:
                # --- SELF-CORRECTION LOGIC ---
                self.logger.warning(f"Attempt {attempt + 1} failed with validation error: {e}")
                
                # Check if it's a "string_too_long" error and it's not the last attempt
                if "string_too_long" in str(e) and attempt < max_retries - 1:
                    self.logger.info("Attempting to self-correct a 'string_too_long' error.")
                    # We can't easily fix JSON here, so we just add a stronger prompt instruction and retry
                    full_prompt += "\n\nREMINDER: YOU FAILED THE PREVIOUS ATTEMPT BECAUSE A STRING WAS TOO LONG. BE MORE CONCISE AND STRICTLY ADHERE TO ALL LENGTH LIMITS."
                    continue # Retry with the angrier prompt
                else:
                    self.logger.error("Could not self-correct or final attempt failed.")
                    # On the last attempt, fall through to the fallback response
                    break

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed with a non-validation error: {str(e)}")
                if attempt == max_retries - 1:
                    break # On the last attempt, fall through
                continue
        
        # If all retries fail, generate a safe, valid fallback object
        return self._create_fallback_response(output_model)

    def _build_prompt(self, user_prompt: str, format_instructions: str, context: Optional[str] = None) -> str:
        base_template = """You are an expert research assistant. Your task is to provide accurate, well-structured responses.
            {context}
            USER REQUEST:
            {user_prompt}
            IMPORTANT: You must respond with a valid JSON object that matches the specified schema exactly.
            {format_instructions}
            Ensure your response is factually accurate, professional, and strictly follows all constraints, especially character limits.
            Response:"""
        context_text = f"CONTEXT:\n{context}\n" if context else ""
        return base_template.format(
            context=context_text, user_prompt=user_prompt, format_instructions=format_instructions
        )

    def _create_fallback_response(self, output_model: Type[T]) -> T:
        """Create a minimal, valid fallback response when all generation attempts fail."""
        self.logger.error(f"All retries failed for model {output_model.__name__}. Creating a fallback response.")
        
        # Specific fallback for SourceSummary to avoid losing all data
        if output_model == SourceSummary:
            return SourceSummary(
                url="error.com",
                title="Summarization Failed",
                key_points=["Model failed to produce a valid summary."],
                relevance_to_topic="Unknown due to parsing failure.",
                credibility_assessment="Unknown due to parsing failure.",
                summary="The AI model failed to generate a summary that meets the required format (e.g., length constraints) after multiple attempts.",
                confidence_score=0.1
            )
            
        # Specific fallback for FinalBrief
        if output_model == FinalBrief:
            return FinalBrief(
                topic="Error: Analysis Failed",
                executive_summary="The AI model failed to generate a valid brief that meets the required format. This is often due to an inability to follow all structural rules after multiple attempts.",
                key_findings=["Failed to extract key findings."],
                detailed_analysis="A valid detailed analysis could not be generated.",
                recommendations=["Review source material and retry query."],
                references=[],
                confidence_level=0.1,
                generated_at=datetime.now(),
                context_used=False
            )

        # A truly generic fallback for any other potential models
        try:
            field_defaults = {
                field_name: "Error" if field_info.annotation == str else 0
                for field_name, field_info in output_model.model_fields.items()
                if field_info.is_required()
            }
            return output_model(**field_defaults)
        except Exception:
            # This should be unreachable if the above fallbacks are comprehensive
            raise ValueError(f"CRITICAL: Could not create a fallback for model {output_model.__name__}")