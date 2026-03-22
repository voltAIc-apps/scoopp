# Brave Search API wrapper for company URL discovery and LinkedIn lookup

import re
import logging
from typing import Optional, List, Dict
import httpx

logger = logging.getLogger(__name__)

BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"

# domains to skip when looking for a company's own website
DIRECTORY_DOMAINS = {
    "linkedin.com", "xing.com", "crunchbase.com",
    "glassdoor.com", "indeed.com", "kununu.com",
    "northdata.de", "firmenwissen.de", "wlw.de",
    "facebook.com", "twitter.com", "instagram.com",
    "wikipedia.org", "yelp.com", "yellowpages.com",
}

# generic linkedin slugs that are not person profiles
GENERIC_LINKEDIN_SLUGS = {
    "jobs", "company", "companies", "pulse", "learning",
    "groups", "events", "help", "feed", "mynetwork",
    "messaging", "notifications", "search", "in",
}

LINKEDIN_PROFILE_RE = re.compile(
    r"https?://(?:\w+\.)?linkedin\.com/in/([a-zA-Z0-9\-_%]+)"
)


async def search_web(
    query: str,
    api_key: str,
    num_results: int = 5,
) -> List[Dict]:
    """Run a Brave web search. Returns list of {title, url, description}."""
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": num_results}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(BRAVE_API_URL, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("web", {}).get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description", ""),
        })
    return results


def _domain_of(url: str) -> str:
    """Extract bare domain from URL (e.g. 'www.example.com' -> 'example.com')."""
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        # strip www. prefix
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def extract_company_url(results: List[Dict]) -> Optional[str]:
    """Return the first search result URL that is not a known directory site."""
    for r in results:
        url = r.get("url", "")
        domain = _domain_of(url)
        if not domain:
            continue
        # skip if domain matches any directory
        if any(domain == d or domain.endswith("." + d) for d in DIRECTORY_DOMAINS):
            continue
        return url
    return None


def extract_linkedin_url(
    results: List[Dict],
    person_name: str,
) -> Optional[str]:
    """Extract a linkedin.com/in/ profile URL from search results.
    Validates that the slug is not a generic page."""
    for r in results:
        url = r.get("url", "")
        m = LINKEDIN_PROFILE_RE.match(url)
        if not m:
            continue
        slug = m.group(1).lower()
        # reject generic slugs
        if slug in GENERIC_LINKEDIN_SLUGS:
            continue
        # basic length check — real profile slugs are at least 3 chars
        if len(slug) < 3:
            continue
        return url
    return None
