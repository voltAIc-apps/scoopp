import asyncio
import json
import logging
from typing import Dict, List, Optional
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

logger = logging.getLogger(__name__)

class LinkedInCookieExtractor:
    """Automated LinkedIn cookie extraction using crawl4ai"""
    
    def __init__(self, config: dict):
        self.config = config
    
    async def extract_cookies_headless(self, username: str, password: str) -> Dict:
        """
        Extract LinkedIn cookies using headless automation
        
        This method:
        1. Navigates to LinkedIn login
        2. Fills credentials via JavaScript
        3. Submits form and waits for redirect
        4. Extracts authentication cookies
        5. Validates session
        """
        browser_config = BrowserConfig(
            headless=True,
            extra_args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor"
            ],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport_width=1920,
            viewport_height=1080
        )
        
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Step 1: Navigate to login and perform authentication
                login_script = f"""
                async function loginToLinkedIn() {{
                    // Wait for page to load
                    await new Promise(resolve => setTimeout(resolve, 3000));
                    
                    const usernameField = document.querySelector('#username');
                    const passwordField = document.querySelector('#password');
                    const submitBtn = document.querySelector('button[type="submit"]');
                    
                    if (!usernameField || !passwordField || !submitBtn) {{
                        return {{
                            success: false,
                            error: 'Login form elements not found',
                            url: window.location.href
                        }};
                    }}
                    
                    // Fill credentials
                    usernameField.value = '{username}';
                    usernameField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    
                    passwordField.value = '{password}';
                    passwordField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    
                    // Wait and submit
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    submitBtn.click();
                    
                    // Wait for redirect/response
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    
                    const currentUrl = window.location.href;
                    const isLoggedIn = !currentUrl.includes('/login') && 
                                     (currentUrl.includes('/feed') || 
                                      currentUrl.includes('/in/') ||
                                      document.querySelector('[data-control-name="identity_welcome_message"]'));
                    
                    // Extract cookies
                    const cookies = document.cookie.split(';').map(cookie => {{
                        const [name, ...valueParts] = cookie.trim().split('=');
                        const value = valueParts.join('=');
                        return {{ name: name.trim(), value: value }};
                    }}).filter(cookie => 
                        ['li_at', 'JSESSIONID', 'liap', 'li_rm'].includes(cookie.name)
                    );
                    
                    return {{
                        success: isLoggedIn,
                        url: currentUrl,
                        cookies: cookies,
                        loginForm: !!document.querySelector('#username'),
                        hasCaptcha: document.body.innerHTML.toLowerCase().includes('captcha') ||
                                   document.body.innerHTML.toLowerCase().includes('recaptcha'),
                        has2FA: document.body.innerHTML.toLowerCase().includes('verification') ||
                               document.body.innerHTML.toLowerCase().includes('two-step'),
                        hasError: document.body.innerHTML.toLowerCase().includes('incorrect') ||
                                 document.body.innerHTML.toLowerCase().includes('couldn\\'t find') ||
                                 document.body.innerHTML.toLowerCase().includes('suspended')
                    }};
                }}
                
                return await loginToLinkedIn();
                """
                
                config = CrawlerRunConfig(js_code=[login_script])
                result = await crawler.arun("https://www.linkedin.com/login", config=config)
                
                if not result.success:
                    return {
                        "success": False,
                        "error": f"Failed to load LinkedIn login page: {result.error_message}"
                    }
                
                # Parse JavaScript execution result
                if result.js_execution_result and len(result.js_execution_result) > 0:
                    login_result = result.js_execution_result[0]
                    
                    if login_result.get("success"):
                        # Format cookies for crawl4ai
                        formatted_cookies = []
                        for cookie in login_result.get("cookies", []):
                            formatted_cookies.append({
                                "name": cookie["name"],
                                "value": cookie["value"],
                                "domain": ".linkedin.com",
                                "path": "/",
                                "secure": True,
                                "httpOnly": cookie["name"] == "li_at"
                            })
                        
                        return {
                            "success": True,
                            "cookies": formatted_cookies,
                            "raw_cookies": login_result.get("cookies", []),
                            "login_url": login_result.get("url", ""),
                            "method": "headless_automation"
                        }
                    
                    elif login_result.get("hasError"):
                        return {
                            "success": False,
                            "error": "Invalid LinkedIn credentials or account issue",
                            "details": login_result
                        }
                    
                    elif login_result.get("hasCaptcha"):
                        return {
                            "success": False,
                            "error": "CAPTCHA detected - automated login blocked",
                            "solution": "Try manual login or wait before retrying",
                            "details": login_result
                        }
                    
                    elif login_result.get("has2FA"):
                        return {
                            "success": False,
                            "error": "2FA required - cannot complete automated login",
                            "solution": "Disable 2FA temporarily or use manual cookie extraction",
                            "details": login_result
                        }
                    
                    else:
                        return {
                            "success": False,
                            "error": "Login failed for unknown reason",
                            "details": login_result
                        }
                else:
                    return {
                        "success": False,
                        "error": "JavaScript execution failed during login"
                    }
                    
        except Exception as e:
            logger.error(f"Cookie extraction error: {str(e)}")
            return {
                "success": False,
                "error": f"Automation failed: {str(e)}"
            }
    
    async def validate_cookies(self, cookies: List[Dict]) -> bool:
        """Validate if extracted cookies work for LinkedIn access"""
        try:
            browser_config = BrowserConfig(
                headless=True,
                cookies=cookies,
                extra_args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Test access to LinkedIn feed
                result = await crawler.arun("https://www.linkedin.com/feed/")
                
                # Check if we're logged in
                if result.success:
                    is_logged_in = (
                        "/login" not in result.url and 
                        "sign in" not in result.markdown.lower() and
                        ("feed" in result.url or "home" in result.markdown.lower())
                    )
                    return is_logged_in
                    
            return False
            
        except Exception as e:
            logger.error(f"Cookie validation error: {str(e)}")
            return False
    
    async def get_cookies_with_retry(
        self, 
        username: str, 
        password: str, 
        max_retries: int = 3
    ) -> Dict:
        """Extract cookies with retry logic"""
        
        for attempt in range(max_retries):
            logger.info(f"LinkedIn cookie extraction attempt {attempt + 1}/{max_retries}")
            
            result = await self.extract_cookies_headless(username, password)
            
            if result.get("success"):
                # Validate cookies
                cookies = result.get("cookies", [])
                if cookies and await self.validate_cookies(cookies):
                    logger.info("LinkedIn cookies extracted and validated successfully")
                    return result
                else:
                    logger.warning("Extracted cookies failed validation")
                    result["success"] = False
                    result["error"] = "Cookies failed validation"
            
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5  # Progressive backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        
        return {
            "success": False,
            "error": f"Failed to extract valid cookies after {max_retries} attempts"
        }