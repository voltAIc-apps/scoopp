# Pydantic models for the research pipeline
# Spec: ~/Downloads/files/scoopp-spec.md

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, EmailStr


class MailContext(BaseModel):
    """Meeting / booking context passed through to the briefing email."""
    consultant_name: Optional[str] = None
    meeting_date: Optional[str] = None
    meeting_time: Optional[str] = None
    topic: Optional[str] = None
    meet_link: Optional[str] = None


class RequestContext(BaseModel):
    """Attribution / UTM context from the booking widget."""
    page_url: Optional[str] = None
    page_title: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    custom: Optional[Dict[str, Any]] = None


# ── request ──────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    company_name: str
    person_name: str
    person_email: Optional[str] = None
    format: Literal["brief", "detailed"] = "brief"
    mail_to: Optional[EmailStr] = None
    mail_subject: Optional[str] = None
    mail_context: Optional[MailContext] = None
    context: Optional[RequestContext] = None


# ── response (immediate) ─────────────────────────────────────

class ResearchResponse(BaseModel):
    research_id: str
    status: str = "queued"


# ── result sub-models ────────────────────────────────────────

class CompanyResult(BaseModel):
    name: str
    website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    recent_news: Optional[str] = None


class PersonResult(BaseModel):
    name: str
    linkedin_url: Optional[str] = None


class ResearchResultPayload(BaseModel):
    """Nested inside ResearchResultResponse.result"""
    company: CompanyResult
    person: PersonResult
    format: str = "brief"


# ── GET /research/{id} response ──────────────────────────────

class ResearchResultResponse(BaseModel):
    research_id: str
    status: str
    result: Optional[ResearchResultPayload] = None
