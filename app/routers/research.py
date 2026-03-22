# Research endpoints — POST /research, GET /research/{research_id}
# Follows the job.py factory pattern for router initialisation.

from uuid import uuid4
from typing import Callable
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from auth import verify_api_key
from models.research import (
    ResearchRequest,
    ResearchResponse,
    ResearchResultResponse,
    ResearchResultPayload,
    CompanyResult,
    PersonResult,
)
from research_db import save_research, get_research
from services.researcher import run_research_pipeline

# ── dependency placeholders (injected by init_research_router) ──
_config = None
_token_dep: Callable = lambda: None

router = APIRouter(prefix="/research", tags=["research"])


def init_research_router(redis, config, token_dep) -> APIRouter:
    """Inject shared singletons and return the router for mounting."""
    global _config, _token_dep
    _config = config
    _token_dep = token_dep
    return router


# ── POST /research ───────────────────────────────────────────

@router.post("", status_code=202, response_model=ResearchResponse)
async def create_research(
    request: Request,
    body: ResearchRequest,
    background_tasks: BackgroundTasks,
    _auth=Depends(verify_api_key),
):
    """Trigger a research job. Returns immediately with a job ID."""
    research_id = str(uuid4())

    # persist initial record
    save_research(
        research_id=research_id,
        company_name=body.company_name,
        person_name=body.person_name,
        fmt=body.format,
        status="queued",
        mail_to=body.mail_to,
    )

    # schedule background pipeline
    background_tasks.add_task(
        run_research_pipeline,
        research_id=research_id,
        company_name=body.company_name,
        person_name=body.person_name,
        person_email=body.person_email,
        fmt=body.format,
        mail_to=body.mail_to,
        mail_subject=body.mail_subject,
        mail_context=body.mail_context.model_dump() if body.mail_context else None,
        request_context=body.context.model_dump() if body.context else None,
        config=_config,
    )

    return ResearchResponse(research_id=research_id, status="queued")


# ── GET /research/{research_id} ──────────────────────────────

@router.get("/{research_id}", response_model=ResearchResultResponse)
async def get_research_status(
    research_id: str,
    request: Request,
    _auth=Depends(verify_api_key),
):
    """Return the status and result of a research job."""
    row = get_research(research_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Research job not found")

    # build result payload if completed
    result = None
    if row["status"] == "done" and row.get("result_json"):
        rj = row["result_json"]
        result = ResearchResultPayload(
            company=CompanyResult(**rj.get("company", {})),
            person=PersonResult(**rj.get("person", {})),
            format=rj.get("format", "brief"),
        )

    return ResearchResultResponse(
        research_id=research_id,
        status=row["status"],
        result=result,
    )
