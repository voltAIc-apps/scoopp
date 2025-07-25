from typing import List, Optional, Dict
from enum import Enum
from pydantic import BaseModel, Field
from utils import FilterType


class CrawlStrategy(str, Enum):
    BFS = "bfs"
    DFS = "dfs"


class CrawlRequest(BaseModel):
    urls: List[str] = Field(min_length=1, max_length=100)
    browser_config: Optional[Dict] = Field(default_factory=dict)
    crawler_config: Optional[Dict] = Field(default_factory=dict)
    # Depth crawling parameters (optional - when provided, enables depth crawling for single URL)
    max_depth: Optional[int] = Field(default=None, ge=0, le=5, description="Enable depth crawling with max depth (0-5). Only works with single URL.")
    crawl_strategy: Optional[CrawlStrategy] = Field(default=CrawlStrategy.BFS, description="Crawling strategy: bfs (breadth-first) or dfs (depth-first)")
    include_external: Optional[bool] = Field(default=False, description="Whether to follow external domain links")
    max_pages: Optional[int] = Field(default=None, ge=1, le=100, description="Maximum pages to crawl in depth mode")



class MarkdownRequest(BaseModel):
    """Request body for the /md endpoint."""
    url: str                    = Field(...,  description="Absolute http/https URL to fetch")
    f:   FilterType             = Field(FilterType.FIT,
                                        description="Content‑filter strategy: FIT, RAW, BM25, or LLM")
    q:   Optional[str] = Field(None,  description="Query string used by BM25/LLM filters")
    c:   Optional[str] = Field("0",   description="Cache‑bust / revision counter")


class RawCode(BaseModel):
    code: str

class HTMLRequest(BaseModel):
    url: str
    
class ScreenshotRequest(BaseModel):
    url: str
    screenshot_wait_for: Optional[float] = 2
    output_path: Optional[str] = None

class PDFRequest(BaseModel):
    url: str
    output_path: Optional[str] = None


class JSEndpointRequest(BaseModel):
    url: str
    scripts: List[str] = Field(
        ...,
        description="List of separated JavaScript snippets to execute"
    )

class LinkedInLoginRequest(BaseModel):
    username: str = Field(..., description="LinkedIn username/email")
    password: str = Field(..., description="LinkedIn password")
    force_new: bool = Field(False, description="Force new login even if session exists")

class LinkedInCrawlRequest(BaseModel):
    urls: List[str] = Field(..., description="LinkedIn URLs to crawl")
    username: str = Field(..., description="LinkedIn username/email")
    password: str = Field(..., description="LinkedIn password")
    crawler_config: Dict = Field(default_factory=dict)
    browser_config: Optional[Dict] = Field(default_factory=dict, description="Additional browser configuration")
    max_depth: Optional[int] = Field(None, description="Enable depth crawling")
    crawl_strategy: Optional[str] = Field("bfs", description="Crawling strategy: bfs or dfs")
    include_external: Optional[bool] = Field(False, description="Include external links in depth crawl")
    max_pages: Optional[int] = Field(None, description="Maximum pages to crawl")
    force_new_login: Optional[bool] = Field(False, description="Force new login even if session exists")