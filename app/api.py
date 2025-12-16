import os
import json
import asyncio
from typing import List, Tuple, Dict
from functools import partial
from uuid import uuid4
from datetime import datetime

import logging
from typing import Optional, AsyncGenerator
from urllib.parse import unquote
from fastapi import HTTPException, Request, status
from fastapi.background import BackgroundTasks
from fastapi.responses import JSONResponse
from redis import asyncio as aioredis

from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    LLMExtractionStrategy,
    CacheMode,
    BrowserConfig,
    MemoryAdaptiveDispatcher,
    RateLimiter, 
    LLMConfig,
    BFSDeepCrawlStrategy,
    DFSDeepCrawlStrategy
)
from crawl4ai.utils import perform_completion_with_backoff
from crawl4ai.content_filter_strategy import (
    PruningContentFilter,
    BM25ContentFilter,
    LLMContentFilter
)
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

from utils import (
    TaskStatus,
    FilterType,
    get_base_url,
    is_task_id,
    should_cleanup_task,
    decode_redis_hash
)
from linkedin_auth import LinkedInAuthHandler, console_2fa_callback, console_captcha_callback

import psutil, time

logger = logging.getLogger(__name__)

# --- Helper functions ---
def _convert_crawl_result_to_dict(obj, _seen=None):
    """
    Recursively convert crawl result objects to dictionaries.
    Preserves all data without converting to strings.
    Includes circular reference protection.
    """
    if _seen is None:
        _seen = set()
    
    # Prevent circular references
    obj_id = id(obj)
    if obj_id in _seen:
        return {"_circular_ref": type(obj).__name__}
    
    # Track this object to prevent circular references
    if not isinstance(obj, (str, int, float, bool, type(None))):
        _seen.add(obj_id)
    # Handle None
    if obj is None:
        return None
    
    # Handle basic types that are already JSON serializable
    if isinstance(obj, (str, int, float, bool)):
        return obj
    
    # Handle lists and tuples
    if isinstance(obj, (list, tuple)):
        return [_convert_crawl_result_to_dict(item, _seen) for item in obj]
    
    # Handle dictionaries
    if isinstance(obj, dict):
        return {key: _convert_crawl_result_to_dict(value, _seen) for key, value in obj.items()}
    
    # Handle objects with model_dump method (Pydantic models, crawl4ai objects)
    if hasattr(obj, 'model_dump'):
        try:
            dumped = obj.model_dump()
            # Recursively process the dumped result in case it contains nested objects
            return _convert_crawl_result_to_dict(dumped, _seen)
        except Exception as e:
            logger.warning(f"model_dump() failed for {type(obj)}: {e}")
            # Fall through to __dict__ approach
    
    # Handle objects with to_dict method
    if hasattr(obj, 'to_dict'):
        try:
            return _convert_crawl_result_to_dict(obj.to_dict(), _seen)
        except Exception as e:
            logger.warning(f"to_dict() failed for {type(obj)}: {e}")
    
    # Handle objects with __dict__ attribute
    if hasattr(obj, '__dict__'):
        try:
            result = {}
            for key, value in obj.__dict__.items():
                # Skip private attributes and methods
                if not key.startswith('_') and not callable(value):
                    result[key] = _convert_crawl_result_to_dict(value, _seen)
            return result
        except Exception as e:
            logger.warning(f"__dict__ conversion failed for {type(obj)}: {e}")
    
    # Handle datetime objects
    if hasattr(obj, 'isoformat'):
        try:
            return obj.isoformat()
        except Exception:
            pass
    
    # Handle enum objects
    if hasattr(obj, 'value'):
        try:
            return obj.value
        except Exception:
            pass
    
    # For any other object type, try to extract meaningful data
    # without falling back to string representation
    try:
        # Try to get public attributes
        if hasattr(obj, '__class__'):
            result = {"_type": obj.__class__.__name__}
            for attr in dir(obj):
                if not attr.startswith('_') and not callable(getattr(obj, attr, None)):
                    try:
                        value = getattr(obj, attr)
                        result[attr] = _convert_crawl_result_to_dict(value, _seen)
                    except Exception:
                        continue
            # Only return if we found some attributes
            if len(result) > 1:  # More than just _type
                return result
    except Exception:
        pass
    
    # Clean up tracking to prevent memory leaks
    try:
        _seen.discard(obj_id)
    except:
        pass
    
    # Last resort: return type information instead of string
    return {"_type": type(obj).__name__, "_note": "Unable to serialize this object type"}

def _flatten_results(results):
    """
    Flatten nested result structures to ensure we get a flat list of individual results.
    """
    flattened = []
    
    def _flatten_recursive(item):
        # Handle None
        if item is None:
            return
        
        # If it's a list or tuple, recursively flatten its contents
        if isinstance(item, (list, tuple)):
            for sub_item in item:
                _flatten_recursive(sub_item)
        else:
            # It's a single item, add it to our flattened list
            flattened.append(item)
    
    _flatten_recursive(results)
    
    logger.debug(f"Flattened {type(results)} with {len(results) if hasattr(results, '__len__') else 'unknown'} items into {len(flattened)} items")
    return flattened

def _ensure_flat_dict_list(processed_results):
    """
    Ensure the final result is a flat list of dictionaries, not nested lists.
    """
    if not isinstance(processed_results, list):
        logger.warning(f"Expected list, got {type(processed_results)}, converting...")
        processed_results = [processed_results]
    
    final_results = []
    
    for item in processed_results:
        if isinstance(item, list):
            # If we still have nested lists, flatten them
            logger.warning(f"Found nested list in results, flattening...")
            final_results.extend(_ensure_flat_dict_list(item))
        elif isinstance(item, dict):
            # This is what we want - a dictionary
            final_results.append(item)
        else:
            # Convert other types to dict if possible
            logger.warning(f"Found non-dict item {type(item)}, converting...")
            final_results.append(_convert_crawl_result_to_dict(item))
    
    logger.info(f"Final results: {len(final_results)} dictionaries")
    return final_results

# --- Helper to get memory ---
def _get_memory_mb():
    try:
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception as e:
        logger.warning(f"Could not get memory info: {e}")
        return None


async def handle_llm_qa(
    url: str,
    query: str,
    config: dict
) -> str:
    """Process QA using LLM with crawled content as context."""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        # Extract base URL by finding last '?q=' occurrence
        last_q_index = url.rfind('?q=')
        if last_q_index != -1:
            url = url[:last_q_index]
        query = query or config['llm'].get("llm_prompt","")    
        # Get markdown content
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url)
            if not result.success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.error_message
                )
            content = result.markdown.fit_markdown or result.markdown.raw_markdown

        # Create prompt and get LLM response
        prompt = f"""Use the following content as context to answer the question.
    Content:
    {content}

    Job: 
    {query}

    Answer:"""

        response = perform_completion_with_backoff(
            provider=config["llm"]["provider"],
            prompt_with_variables=prompt,
            api_token=config["llm"]["api_key"] or os.environ.get(config["llm"].get("api_key_env", ""))
        )

        return content,response.choices[0].message.content
    except Exception as e:
        logger.error(f"QA processing error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def process_llm_extraction(
    redis: aioredis.Redis,
    config: dict,
    task_id: str,
    url: str,
    instruction: str,
    schema: Optional[str] = None,
    cache: str = "0"
) -> None:
    """Process LLM extraction in background."""
    try:
        # If config['llm'] has api_key then ignore the api_key_env
        api_key = ""
        if "api_key" in config["llm"]:
            api_key = config["llm"]["api_key"]
        else:
            api_key = os.environ.get(config["llm"].get("api_key_env", None), "")
        llm_strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(
                provider=config["llm"]["provider"],
                api_token=api_key
            ),
            instruction=instruction,
            schema=json.loads(schema) if schema else None,
        )

        cache_mode = CacheMode.ENABLED if cache == "1" else CacheMode.WRITE_ONLY

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=url,
                config=CrawlerRunConfig(
                    extraction_strategy=llm_strategy,
                    scraping_strategy=LXMLWebScrapingStrategy(),
                    cache_mode=cache_mode
                )
            )

        if not result.success:
            await redis.hset(f"task:{task_id}", mapping={
                "status": TaskStatus.FAILED,
                "error": result.error_message
            })
            return

        try:
            content = json.loads(result.extracted_content)
        except json.JSONDecodeError:
            content = result.extracted_content
        await redis.hset(f"task:{task_id}", mapping={
            "status": TaskStatus.COMPLETED,
            "result": json.dumps(content)
        })

    except Exception as e:
        logger.error(f"LLM extraction error: {str(e)}", exc_info=True)
        await redis.hset(f"task:{task_id}", mapping={
            "status": TaskStatus.FAILED,
            "error": str(e)
        })

async def handle_markdown_request(
    url: str,
    filter_type: FilterType,
    query: Optional[str] = None,
    cache: str = "0",
    config: Optional[dict] = None
) -> str:
    """Handle markdown generation requests."""
    try:
        decoded_url = unquote(url)
        if not decoded_url.startswith(('http://', 'https://')):
            decoded_url = 'https://' + decoded_url

        if filter_type == FilterType.RAW:
            md_generator = DefaultMarkdownGenerator()
        else:
            content_filter = {
                FilterType.FIT: PruningContentFilter(),
                FilterType.BM25: BM25ContentFilter(user_query=query or ""),
                FilterType.LLM: LLMContentFilter(
                    llm_config=LLMConfig(
                        provider=config["llm"]["provider"],
                        api_token=os.environ.get(config["llm"].get("api_key_env", None), ""),
                    ),
                    instruction=query or "Extract main content"
                )
            }[filter_type]
            md_generator = DefaultMarkdownGenerator(content_filter=content_filter)

        cache_mode = CacheMode.ENABLED if cache == "1" else CacheMode.WRITE_ONLY

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=decoded_url,
                config=CrawlerRunConfig(
                    markdown_generator=md_generator,
                    scraping_strategy=LXMLWebScrapingStrategy(),
                    cache_mode=cache_mode
                )
            )
            
            if not result.success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.error_message
                )

            return (result.markdown.raw_markdown 
                   if filter_type == FilterType.RAW 
                   else result.markdown.fit_markdown)

    except Exception as e:
        logger.error(f"Markdown error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def handle_llm_request(
    redis: aioredis.Redis,
    background_tasks: BackgroundTasks,
    request: Request,
    input_path: str,
    query: Optional[str] = None,
    schema: Optional[str] = None,
    cache: str = "0",
    config: Optional[dict] = None
) -> JSONResponse:
    """Handle LLM extraction requests."""
    base_url = get_base_url(request)
    
    try:
        if is_task_id(input_path):
            return await handle_task_status(
                redis, input_path, base_url
            )

        if not query:
            return JSONResponse({
                "message": "Please provide an instruction",
                "_links": {
                    "example": {
                        "href": f"{base_url}/llm/{input_path}?q=Extract+main+content",
                        "title": "Try this example"
                    }
                }
            })

        return await create_new_task(
            redis,
            background_tasks,
            input_path,
            query,
            schema,
            cache,
            base_url,
            config
        )

    except Exception as e:
        logger.error(f"LLM endpoint error: {str(e)}", exc_info=True)
        return JSONResponse({
            "error": str(e),
            "_links": {
                "retry": {"href": str(request.url)}
            }
        }, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

async def handle_task_status(
    redis: aioredis.Redis,
    task_id: str,
    base_url: str,
    *,
    keep: bool = False
) -> JSONResponse:
    """Handle task status check requests."""
    task = await redis.hgetall(f"task:{task_id}")
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task = decode_redis_hash(task)
    response = create_task_response(task, task_id, base_url)

    if task["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        if not keep and should_cleanup_task(task["created_at"]):
            await redis.delete(f"task:{task_id}")

    return JSONResponse(response)

async def create_new_task(
    redis: aioredis.Redis,
    background_tasks: BackgroundTasks,
    input_path: str,
    query: str,
    schema: Optional[str],
    cache: str,
    base_url: str,
    config: dict
) -> JSONResponse:
    """Create and initialize a new task."""
    decoded_url = unquote(input_path)
    if not decoded_url.startswith(('http://', 'https://')):
        decoded_url = 'https://' + decoded_url

    from datetime import datetime
    task_id = f"llm_{int(datetime.now().timestamp())}_{id(background_tasks)}"
    
    await redis.hset(f"task:{task_id}", mapping={
        "status": TaskStatus.PROCESSING,
        "created_at": datetime.now().isoformat(),
        "url": decoded_url
    })

    background_tasks.add_task(
        process_llm_extraction,
        redis,
        config,
        task_id,
        decoded_url,
        query,
        schema,
        cache
    )

    return JSONResponse({
        "task_id": task_id,
        "status": TaskStatus.PROCESSING,
        "url": decoded_url,
        "_links": {
            "self": {"href": f"{base_url}/llm/{task_id}"},
            "status": {"href": f"{base_url}/llm/{task_id}"}
        }
    })

def create_task_response(task: dict, task_id: str, base_url: str) -> dict:
    """Create response for task status check."""
    response = {
        "task_id": task_id,
        "status": task["status"],
        "created_at": task["created_at"],
        "url": task["url"],
        "_links": {
            "self": {"href": f"{base_url}/llm/{task_id}"},
            "refresh": {"href": f"{base_url}/llm/{task_id}"}
        }
    }

    if task["status"] == TaskStatus.COMPLETED:
        response["result"] = json.loads(task["result"])
    elif task["status"] == TaskStatus.FAILED:
        response["error"] = task["error"]

    return response

async def handle_linkedin_login(
    username: str,
    password: str,
    config: dict,
    interactive_mode: bool = True,
    use_2fa_callback: bool = False
) -> dict:
    """Handle LinkedIn login with CAPTCHA and 2FA support"""
    try:
        auth_handler = LinkedInAuthHandler(config)
        
        # Set up callbacks if needed
        captcha_callback = console_captcha_callback if interactive_mode else None
        twofa_callback = console_2fa_callback if use_2fa_callback else None
        
        result = await auth_handler.enhanced_linkedin_login(
            username=username,
            password=password,
            interactive_mode=interactive_mode,
            captcha_callback=captcha_callback,
            twofa_callback=twofa_callback
        )
        
        return result
        
    except Exception as e:
        logger.error(f"LinkedIn login error: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}

async def validate_linkedin_session(cookies: list, config: dict) -> bool:
    """Validate if LinkedIn session cookies are still valid"""
    try:
        browser_config = BrowserConfig(
            headless=True,
            cookies=cookies
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun("https://www.linkedin.com/feed/")
            
            # Check if we're still logged in
            if "/login" in result.url or "Sign in" in result.markdown:
                return False
            return True
            
    except Exception as e:
        logger.error(f"Session validation error: {str(e)}")
        return False

async def stream_results(crawler: AsyncWebCrawler, results_gen: AsyncGenerator) -> AsyncGenerator[bytes, None]:
    """Stream results with heartbeats and completion markers."""
    import json
    from utils import datetime_handler

    try:
        async for result in results_gen:
            try:
                server_memory_mb = _get_memory_mb()
                result_dict = result.model_dump()
                result_dict['server_memory_mb'] = server_memory_mb
                logger.info(f"Streaming result for {result_dict.get('url', 'unknown')}")
                data = json.dumps(result_dict, default=datetime_handler) + "\n"
                yield data.encode('utf-8')
            except Exception as e:
                logger.error(f"Serialization error: {e}")
                error_response = {"error": str(e), "url": getattr(result, 'url', 'unknown')}
                yield (json.dumps(error_response) + "\n").encode('utf-8')

        yield json.dumps({"status": "completed"}).encode('utf-8')
        
    except asyncio.CancelledError:
        logger.warning("Client disconnected during streaming")
    finally:
        # try:
        #     await crawler.close()
        # except Exception as e:
        #     logger.error(f"Crawler cleanup error: {e}")
        pass

async def handle_crawl_request(
    urls: List[str],
    browser_config: dict,
    crawler_config: dict,
    config: dict,
    max_depth: Optional[int] = None,
    crawl_strategy: Optional[str] = None,
    include_external: Optional[bool] = None,
    max_pages: Optional[int] = None
) -> dict:
    """Handle non-streaming crawl requests with optional depth crawling."""
    start_mem_mb = _get_memory_mb() # <--- Get memory before
    start_time = time.time()
    mem_delta_mb = None
    peak_mem_mb = start_mem_mb
    
    try:
        # Validate depth crawling parameters
        if max_depth is not None:
            if len(urls) > 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Depth crawling only supports single URL. Provide exactly one URL when using max_depth."
                )
            
            # Enable depth crawling mode
            url = urls[0]
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            return await handle_depth_crawl_request(
                url=url,
                max_depth=max_depth,
                crawl_strategy=crawl_strategy or "bfs",
                include_external=include_external or False,
                max_pages=max_pages,
                browser_config=browser_config,
                crawler_config=crawler_config,
                config=config
            )
        
        # Regular multi-URL crawling
        urls = [('https://' + url) if not url.startswith(('http://', 'https://')) else url for url in urls]
        browser_config = BrowserConfig.load(browser_config)
        crawler_config = CrawlerRunConfig.load(crawler_config)

        dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=config["crawler"]["memory_threshold_percent"],
            rate_limiter=RateLimiter(
                base_delay=tuple(config["crawler"]["rate_limiter"]["base_delay"])
            ) if config["crawler"]["rate_limiter"]["enabled"] else None
        )
        
        from crawler_pool import get_crawler
        crawler = await get_crawler(browser_config)

        # crawler: AsyncWebCrawler = AsyncWebCrawler(config=browser_config)
        # await crawler.start()
        
        base_config = config["crawler"]["base_config"]
        # Iterate on key-value pairs in global_config then use haseattr to set them 
        for key, value in base_config.items():
            if hasattr(crawler_config, key):
                setattr(crawler_config, key, value)

        results = []
        func = getattr(crawler, "arun" if len(urls) == 1 else "arun_many")
        partial_func = partial(func, 
                                urls[0] if len(urls) == 1 else urls, 
                                config=crawler_config, 
                                dispatcher=dispatcher)
        results = await partial_func()

        # await crawler.close()
        
        end_mem_mb = _get_memory_mb() # <--- Get memory after
        end_time = time.time()
        
        if start_mem_mb is not None and end_mem_mb is not None:
            mem_delta_mb = end_mem_mb - start_mem_mb # <--- Calculate delta
            peak_mem_mb = max(peak_mem_mb if peak_mem_mb else 0, end_mem_mb) # <--- Get peak memory
        logger.info(f"Memory usage: Start: {start_mem_mb} MB, End: {end_mem_mb} MB, Delta: {mem_delta_mb} MB, Peak: {peak_mem_mb} MB")
                              
        # Convert and ensure flat structure
        processed_results = [_convert_crawl_result_to_dict(result) for result in results]
        processed_results = _ensure_flat_dict_list(processed_results)
        
        return {
            "success": True,
            "results": processed_results,
            "server_processing_time_s": end_time - start_time,
            "server_memory_delta_mb": mem_delta_mb,
            "server_peak_memory_mb": peak_mem_mb
        }

    except Exception as e:
        logger.error(f"Crawl error: {str(e)}", exc_info=True)
        if 'crawler' in locals() and crawler.ready: # Check if crawler was initialized and started
            #  try:
            #      await crawler.close()
            #  except Exception as e:
            #       logger.error(f"Error closing crawler during exception handling: {e}")
            logger.error(f"Error closing crawler during exception handling: {e}")

        # Measure memory even on error if possible
        end_mem_mb_error = _get_memory_mb()
        if start_mem_mb is not None and end_mem_mb_error is not None:
            mem_delta_mb = end_mem_mb_error - start_mem_mb

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=json.dumps({ # Send structured error
                "error": str(e),
                "server_memory_delta_mb": mem_delta_mb,
                "server_peak_memory_mb": max(peak_mem_mb if peak_mem_mb else 0, end_mem_mb_error or 0)
            })
        )

async def handle_stream_crawl_request(
    urls: List[str],
    browser_config: dict,
    crawler_config: dict,
    config: dict
) -> Tuple[AsyncWebCrawler, AsyncGenerator]:
    """Handle streaming crawl requests."""
    try:
        browser_config = BrowserConfig.load(browser_config)
        # browser_config.verbose = True # Set to False or remove for production stress testing
        browser_config.verbose = False
        crawler_config = CrawlerRunConfig.load(crawler_config)
        crawler_config.scraping_strategy = LXMLWebScrapingStrategy()
        crawler_config.stream = True

        dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=config["crawler"]["memory_threshold_percent"],
            rate_limiter=RateLimiter(
                base_delay=tuple(config["crawler"]["rate_limiter"]["base_delay"])
            )
        )

        from crawler_pool import get_crawler
        crawler = await get_crawler(browser_config)

        # crawler = AsyncWebCrawler(config=browser_config)
        # await crawler.start()

        results_gen = await crawler.arun_many(
            urls=urls,
            config=crawler_config,
            dispatcher=dispatcher
        )

        return crawler, results_gen

    except Exception as e:
        # Make sure to close crawler if started during an error here
        if 'crawler' in locals() and crawler.ready:
            #  try:
            #       await crawler.close()
            #  except Exception as e:
            #       logger.error(f"Error closing crawler during stream setup exception: {e}")
            logger.error(f"Error closing crawler during stream setup exception: {e}")
        logger.error(f"Stream crawl error: {str(e)}", exc_info=True)
        # Raising HTTPException here will prevent streaming response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
        
async def handle_crawl_job(
    redis,
    background_tasks: BackgroundTasks,
    urls: List[str],
    browser_config: Dict,
    crawler_config: Dict,
    config: Dict,
    max_depth: Optional[int] = None,
    crawl_strategy: Optional[str] = None,
    include_external: Optional[bool] = None,
    max_pages: Optional[int] = None,
) -> Dict:
    """
    Fire-and-forget version of handle_crawl_request.
    Creates a task in Redis, runs the heavy work in a background task,
    lets /crawl/job/{task_id} polling fetch the result.
    """
    task_id = f"crawl_{uuid4().hex[:8]}"
    await redis.hset(f"task:{task_id}", mapping={
        "status": TaskStatus.PROCESSING,         # <-- keep enum values consistent
        "created_at": datetime.utcnow().isoformat(),
        "url": json.dumps(urls),                 # store list as JSON string
        "result": "",
        "error": "",
    })

    async def _runner():
        try:
            result = await handle_crawl_request(
                urls=urls,
                browser_config=browser_config,
                crawler_config=crawler_config,
                config=config,
                max_depth=max_depth,
                crawl_strategy=crawl_strategy,
                include_external=include_external,
                max_pages=max_pages,
            )
            await redis.hset(f"task:{task_id}", mapping={
                "status": TaskStatus.COMPLETED,
                "result": json.dumps(result),
            })
            await asyncio.sleep(5)  # Give Redis time to process the update
        except Exception as exc:
            await redis.hset(f"task:{task_id}", mapping={
                "status": TaskStatus.FAILED,
                "error": str(exc),
            })

    background_tasks.add_task(_runner)
    return {"task_id": task_id}

def create_deep_crawl_strategy(strategy_name: str, max_depth: int, include_external: bool):
    """Create appropriate deep crawl strategy based on strategy name."""
    if strategy_name == "bfs":
        return BFSDeepCrawlStrategy(max_depth=max_depth, include_external=include_external)
    elif strategy_name == "dfs":
        return DFSDeepCrawlStrategy(max_depth=max_depth, include_external=include_external)
    else:
        raise ValueError(f"Unknown crawl strategy: {strategy_name}. Available strategies: bfs, dfs")

async def handle_depth_crawl_request(
    url: str,
    max_depth: int,
    crawl_strategy: str,
    include_external: bool,
    max_pages: Optional[int],
    browser_config: dict,
    crawler_config: dict,
    config: dict
) -> dict:
    """Handle depth crawling requests."""
    start_mem_mb = _get_memory_mb()
    start_time = time.time()
    mem_delta_mb = None
    peak_mem_mb = start_mem_mb
    
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        browser_config = BrowserConfig.load(browser_config)
        crawler_config = CrawlerRunConfig.load(crawler_config)
        
        deep_crawl_strategy = create_deep_crawl_strategy(crawl_strategy, max_depth, include_external)
        crawler_config.deep_crawl_strategy = deep_crawl_strategy
        
        if max_pages:
            crawler_config.max_pages = max_pages

        dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=config["crawler"]["memory_threshold_percent"],
            rate_limiter=RateLimiter(
                base_delay=tuple(config["crawler"]["rate_limiter"]["base_delay"])
            ) if config["crawler"]["rate_limiter"]["enabled"] else None
        )
        
        from crawler_pool import get_crawler
        crawler = await get_crawler(browser_config)
        
        base_config = config["crawler"]["base_config"]
        for key, value in base_config.items():
            if hasattr(crawler_config, key):
                setattr(crawler_config, key, value)

        result = await crawler.arun(url, config=crawler_config, dispatcher=dispatcher)
        
        end_mem_mb = _get_memory_mb()
        end_time = time.time()
        
        if start_mem_mb is not None and end_mem_mb is not None:
            mem_delta_mb = end_mem_mb - start_mem_mb
            peak_mem_mb = max(peak_mem_mb if peak_mem_mb else 0, end_mem_mb)
            
        # Handle different result structures from depth crawling
        if hasattr(result, 'results') and result.results:
            # For depth crawling, result.results is a list of CrawlResult objects
            raw_results = result.results
            logger.info(f"Depth crawl raw results type: {type(raw_results)}, length: {len(raw_results) if hasattr(raw_results, '__len__') else 'unknown'}")
            
            # Flatten nested results if needed
            results = _flatten_results(raw_results)
            logger.info(f"Depth crawl completed: {len(results)} pages after flattening")
        else:
            # Single result
            results = [result]
            logger.info(f"Depth crawl completed: 1 page")
        
        # Convert results to dictionaries using recursive approach
        processed_results = [_convert_crawl_result_to_dict(r) for r in results]
        
        # Final validation - ensure we have a flat list of dicts
        processed_results = _ensure_flat_dict_list(processed_results)
        
        return {
            "success": True,
            "results": processed_results,
            "crawl_metadata": {
                "max_depth": max_depth,
                "strategy": crawl_strategy,
                "include_external": include_external,
                "pages_crawled": len(processed_results)
            },
            "server_processing_time_s": end_time - start_time,
            "server_memory_delta_mb": mem_delta_mb,
            "server_peak_memory_mb": peak_mem_mb
        }

    except Exception as e:
        logger.error(f"Depth crawl error: {str(e)}", exc_info=True)
        
        end_mem_mb_error = _get_memory_mb()
        if start_mem_mb is not None and end_mem_mb_error is not None:
            mem_delta_mb = end_mem_mb_error - start_mem_mb

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=json.dumps({
                "error": str(e),
                "server_memory_delta_mb": mem_delta_mb,
                "server_peak_memory_mb": max(peak_mem_mb if peak_mem_mb else 0, end_mem_mb_error or 0)
            })
        )