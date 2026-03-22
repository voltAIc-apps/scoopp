# Research pipeline orchestration — steps 1-5 per spec
# Each step is independently try/caught; a single failure never aborts the pipeline.

import os
import json
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# LLM extraction prompt for structured company info
COMPANY_EXTRACT_PROMPT = """\
From the website content below, extract structured company information as JSON.
Return ONLY valid JSON with these fields (set null if not found):
{
  "description": "3-5 sentences summarising what the company does",
  "industry": "sector/industry if identifiable",
  "size": "employee count or range if mentioned",
  "recent_news": "one or two sentences about the most recent news item, if any"
}"""


async def run_research_pipeline(
    research_id: str,
    company_name: str,
    person_name: str,
    person_email: Optional[str],
    fmt: str,
    mail_to: Optional[str],
    mail_subject: Optional[str],
    mail_context: Optional[Dict],
    request_context: Optional[Dict],
    config: dict,
) -> None:
    """Execute the full research pipeline as a background task."""
    from research_db import update_research
    from services.brave_search import search_web, extract_company_url, extract_linkedin_url
    from services.mailer import send_briefing_email

    start = time.time()

    # result accumulators
    company_url: Optional[str] = None
    company_info: Dict[str, Any] = {"name": company_name}
    person_info: Dict[str, Any] = {"name": person_name}
    all_failed = True

    # update status to running
    update_research(research_id, status="running")

    brave_api_key = os.environ.get("BRAVE_API_KEY", "")

    # ── Step 1: Discover company URL via Brave Search ────────
    try:
        if not brave_api_key:
            logger.warning("BRAVE_API_KEY not set, skipping company URL discovery")
        else:
            results = await search_web(f'"{company_name}"', brave_api_key)
            company_url = extract_company_url(results)
            if company_url:
                company_info["website"] = company_url
                all_failed = False
                logger.info("Step 1 OK: company URL = %s", company_url)
            else:
                logger.info("Step 1: no company URL found for '%s'", company_name)
    except Exception as exc:
        logger.error("Step 1 failed (company URL): %s", exc)

    # ── Step 2: Crawl company website + LLM extraction ───────
    if company_url:
        try:
            markdown = await _crawl_website(company_url, fmt, config)
            if markdown:
                extracted = await _extract_company_fields(markdown, config)
                if extracted:
                    company_info.update(
                        {k: v for k, v in extracted.items() if v is not None}
                    )
                    all_failed = False
                    logger.info("Step 2 OK: extracted company fields")
        except Exception as exc:
            logger.error("Step 2 failed (crawl/extract): %s", exc)

    # ── Step 3: LinkedIn profile lookup ──────────────────────
    try:
        if not brave_api_key:
            logger.warning("BRAVE_API_KEY not set, skipping LinkedIn lookup")
        else:
            linkedin_url = await _find_linkedin(
                person_name, person_email, brave_api_key
            )
            if linkedin_url:
                person_info["linkedin_url"] = linkedin_url
                all_failed = False
                logger.info("Step 3 OK: LinkedIn = %s", linkedin_url)
            else:
                logger.info("Step 3: no LinkedIn profile found for '%s'", person_name)
    except Exception as exc:
        logger.error("Step 3 failed (LinkedIn): %s", exc)

    # ── Step 4: Compile result and persist ────────────────────
    processing_time = time.time() - start
    result_payload = {
        "company": company_info,
        "person": person_info,
        "format": fmt,
    }
    final_status = "failed" if all_failed else "done"

    try:
        update_research(
            research_id,
            status=final_status,
            result_json=json.dumps(result_payload, ensure_ascii=False),
            processing_time_s=round(processing_time, 2),
        )
    except Exception as exc:
        logger.error("Step 4 failed (persist): %s", exc)

    # ── Step 5: Send briefing email (if mail_to present) ─────
    if mail_to and final_status == "done":
        try:
            email_result = await send_briefing_email(
                mail_to=mail_to,
                mail_subject=mail_subject,
                mail_context=mail_context,
                company=company_info,
                person=person_info,
                person_name=person_name,
                person_email=person_email,
                request_context=request_context,
            )
            update_research(
                research_id,
                mail_sent=email_result.get("sent", False),
                mail_error=email_result.get("error"),
            )
        except Exception as exc:
            logger.error("Step 5 failed (email): %s", exc)
            update_research(research_id, mail_error=str(exc))

    logger.info(
        "Research pipeline %s finished: status=%s, %.1fs",
        research_id, final_status, processing_time,
    )


# ── internal helpers ─────────────────────────────────────────

async def _crawl_website(url: str, fmt: str, config: dict) -> Optional[str]:
    """Crawl a company website and return markdown content.
    Reuses the existing crawl4ai infrastructure."""
    import asyncio
    from api import handle_markdown_request
    from utils import FilterType

    timeout = 8.0 if fmt == "brief" else 30.0

    try:
        markdown = await asyncio.wait_for(
            handle_markdown_request(url, FilterType.FIT, config=config),
            timeout=timeout,
        )
        return markdown
    except asyncio.TimeoutError:
        logger.warning("Crawl timed out after %.0fs for %s", timeout, url)
        return None
    except Exception as exc:
        logger.warning("Crawl failed for %s: %s", url, exc)
        return None


async def _extract_company_fields(
    markdown: str, config: dict
) -> Optional[Dict[str, str]]:
    """Use LLM to extract structured company fields from crawled markdown."""
    from crawl4ai import LLMConfig

    # resolve LLM API key (same pattern as api.py)
    llm_cfg = config.get("llm", {})
    if "api_key" in llm_cfg:
        api_key = llm_cfg["api_key"]
    else:
        api_key = os.environ.get(llm_cfg.get("api_key_env", ""), "")

    if not api_key:
        logger.warning("No LLM API key configured, skipping extraction")
        return None

    provider = llm_cfg.get("provider", "openai/gpt-4o-mini")

    try:
        # use litellm directly for a simple completion (no crawl4ai overhead)
        import litellm
        response = await litellm.acompletion(
            model=provider,
            messages=[
                {"role": "system", "content": COMPANY_EXTRACT_PROMPT},
                {"role": "user", "content": markdown[:8000]},  # cap input length
            ],
            api_key=api_key,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as exc:
        logger.error("LLM extraction failed: %s", exc)
        return None


async def _find_linkedin(
    person_name: str,
    person_email: Optional[str],
    brave_api_key: str,
) -> Optional[str]:
    """Search for a person's LinkedIn profile URL via Brave."""
    from services.brave_search import search_web, extract_linkedin_url

    # build query: "{person_name}" "{email_domain}" site:linkedin.com/in
    query_parts = [f'"{person_name}"']
    if person_email and "@" in person_email:
        domain = person_email.split("@", 1)[1]
        query_parts.append(f'"{domain}"')
    query_parts.append("site:linkedin.com/in")
    query = " ".join(query_parts)

    results = await search_web(query, brave_api_key)
    return extract_linkedin_url(results, person_name)
