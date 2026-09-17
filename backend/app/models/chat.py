"""
Pydantic data models for FastAPI Chat API endpoints.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the user session")
    message: str = Field(..., description="User query or message content")

    @field_validator("session_id", "message")
    def validate_non_empty(cls, value: str, info) -> str:
        if not value or not value.strip():
            raise ValueError(f"Field '{info.field_name}' must not be empty or whitespace only.")
        return value.strip()


class ChatResponse(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., description="Original user message")
    response: Optional[str] = Field(None, description="Natural language bot response or fallback guidance")
    activity: Optional[str] = Field(None, description="Extracted outdoor activity")
    location: Optional[str] = Field(None, description="Extracted city or location query")
    time_context: Optional[str] = Field(None, description="Extracted time context (e.g. today, evening)")
    resolved_location: Optional[Dict[str, Any]] = Field(None, description="Resolved geographical coordinates")
    weather: Optional[Dict[str, Any]] = Field(None, description="Live weather data")
    selected_sop: Optional[Dict[str, Any]] = Field(None, description="Authoritative matched SOP policy")
    error: Optional[str] = Field(None, description="Error message if processing failed")
