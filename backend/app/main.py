"""
FastAPI application for Weather Advisory Support Bot.
Exposes POST /chat and session management endpoints.
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from backend.app.models.chat import ChatRequest, ChatResponse
from backend.app.session import session_manager
from backend.app.graph import graph

load_dotenv()

app = FastAPI(
    title="Weather Advisory Support Bot API",
    description="Backend API for Weather Advisory Support Bot powered by LangGraph & PolicyEngine",
    version="0.1.0",
)

# Configure CORS origins for Streamlit frontend and local development
frontend_env = os.getenv("FRONTEND_URL", "").strip()
allowed_origins = [
    "http://localhost:8501",
    "http://localhost:8000",
    "http://127.0.0.1:8501",
    "http://127.0.0.1:8000",
]

if frontend_env:
    for origin in frontend_env.split(","):
        clean_origin = origin.strip().rstrip("/")
        if clean_origin and clean_origin not in allowed_origins:
            allowed_origins.append(clean_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Weather Advisory Bot API is running"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint orchestrating intent extraction, geocoding, live weather,
    deterministic SOP policy matching, and response generation via LangGraph.
    """
    session_id = request.session_id
    user_msg = request.message

    # Get conversation context for this session
    history = session_manager.get_history(session_id)

    # Invoke LangGraph workflow
    initial_state = {
        "user_question": user_msg,
        "messages": history,
    }

    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph execution failure: {str(exc)}"
        ) from exc

    response_text = final_state.get("response", "")
    error_msg = final_state.get("error")

    # Update session history
    session_manager.add_user_message(session_id, user_msg)
    if response_text:
        session_manager.add_assistant_message(session_id, response_text)

    return ChatResponse(
        session_id=session_id,
        message=user_msg,
        response=response_text,
        activity=final_state.get("activity"),
        location=final_state.get("location"),
        time_context=final_state.get("time_context"),
        resolved_location=final_state.get("resolved_location"),
        weather=final_state.get("weather"),
        selected_sop=final_state.get("selected_sop"),
        evaluated_sop=final_state.get("evaluated_sop"),
        error=error_msg,
    )



@app.post("/session/{session_id}/reset")
def reset_session_endpoint(session_id: str):
    """
    Reset and clear in-memory conversation history for the specified session ID.
    """
    if not session_id or not session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Session ID cannot be empty."
        )

    session_manager.reset_session(session_id.strip())
    return {
        "session_id": session_id.strip(),
        "message": "Session reset successfully"
    }


@app.get("/session/{session_id}")
def inspect_session_endpoint(session_id: str):
    """
    Optional inspection endpoint for session conversation history.
    """
    if not session_id or not session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Session ID cannot be empty."
        )

    history = session_manager.get_history(session_id.strip())
    return {
        "session_id": session_id.strip(),
        "messages": history,
    }
