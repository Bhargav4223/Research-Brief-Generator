from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import BriefRequest, FinalBrief
from app.graph.workflow import ResearchBriefWorkflow
from app.services.context_service import ContextService
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from langsmith import Client          # NEW
from langsmith.run_helpers import traceable  # NEW

# Start tracing **once** at import time
os.environ.setdefault("LANGSMITH_TRACING", "true")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize FastAPI app
app = FastAPI(
    title="Context-Aware Research Brief Generator",
    description="Generate structured research briefs with context awareness using LangGraph and LangChain",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
workflow = ResearchBriefWorkflow()
context_service = ContextService()
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    
    # Verify API key is configured
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY environment variable not set")
        raise RuntimeError("GOOGLE_API_KEY environment variable is required")
    
    logger.info("Research Brief Generator API started successfully")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    
    return {
        "message": "Context-Aware Research Brief Generator API",
        "version": "1.0.0",
        "endpoints": {
            "generate_brief": "POST /brief",
            "user_history": "GET /user/{user_id}/history",
            "health": "GET /health"
        }
    }

@app.post("/brief", response_model=FinalBrief)
async def generate_brief(request: BriefRequest):
    """Generate a research brief based on the provided topic and parameters"""
    
    logger.info(f"Received brief request for topic: {request.topic}")
    
    try:
        # Validate request
        if not request.topic.strip():
            raise HTTPException(status_code=400, detail="Topic cannot be empty")
        
        if request.depth < 1 or request.depth > 5:
            raise HTTPException(status_code=400, detail="Depth must be between 1 and 5")
        
        # Execute the workflow
        result = await workflow.execute(request)
        
        # Extract the final brief
        final_brief = result.get("final_brief")
        if not final_brief:
            error_msg = result.get("error", "Unknown error occurred during processing")
            logger.error(f"Workflow failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Failed to generate brief: {error_msg}")
        
        logger.info(f"Successfully generated brief for topic: {request.topic}")
        return final_brief
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating brief: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/user/{user_id}/history")
async def get_user_history(user_id: str):
    """Get research history summary for a user"""
    
    try:
        history_summary = context_service.get_user_history_summary(user_id)
        return {
            "user_id": user_id,
            "history": history_summary
        }
        
    except Exception as e:
        logger.error(f"Error retrieving user history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")

@app.get("/workflow/structure")
async def get_workflow_structure():
    """Get the workflow structure visualization"""
    
    return {
        "workflow_structure": workflow.get_workflow_visualization(),
        "nodes": [
            "context_summarization",
            "planning", 
            "search",
            "source_summarization",
            "synthesis",
            "post_processing"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    try:
        # Basic health checks
        api_key_configured = bool(os.getenv("GOOGLE_API_KEY"))
        
        return {
            "status": "healthy",
            "api_key_configured": api_key_configured,
            "components": {
                "workflow": "operational",
                "context_service": "operational",
                "llm_service": "operational" if api_key_configured else "not configured",
                "search_service": "operational"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)