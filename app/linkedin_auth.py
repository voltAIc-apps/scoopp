import asyncio
import json
import time
from typing import Dict, Optional, Tuple
from crawl4ai import AsyncWebCrawler, BrowserConfig
import logging

logger = logging.getLogger(__name__)

class LinkedInAuthHandler:
    def __init__(self, config: dict):
        self.config = config
        self.max_wait_time = 300  # 5 minutes max wait for user input
        
    async def enhanced_linkedin_login(
        self, 
        username: str, 
        password: str,
        interactive_mode: bool = True,
        captcha_callback: Optional[callable] = None,
        twofa_callback: Optional[callable] = None
    ) -> Dict:
        """
        Enhanced LinkedIn login with CAPTCHA and 2FA handling
        
        Args:
            username: LinkedIn username/email
            password: LinkedIn password
            interactive_mode: If True, keeps browser visible for manual intervention
            captcha_callback: Function to call when CAPTCHA is detected
            twofa_callback: Function to call when 2FA is required
        """
        browser_config = BrowserConfig(
            headless=not interactive_mode,
            extra_args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ],
            viewport_width=1920,
            viewport_height=1080
        )
        
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Step 1: Navigate to login page
                logger.info("Navigating to LinkedIn login page...")
                await crawler.arun("https://www.linkedin.com/login")
                await asyncio.sleep(2)
                
                # Step 2: Fill credentials
                logger.info("Filling login credentials...")
                await self._fill_login_form(crawler, username, password)
                
                # Step 3: Handle potential challenges
                login_result = await self._handle_login_challenges(
                    crawler, 
                    interactive_mode,
                    captcha_callback,
                    twofa_callback
                )
                
                if login_result["success"]:
                    # Extract cookies and return
                    cookies = await self._extract_session_cookies(crawler)
                    return {
                        "success": True,
                        "cookies": cookies,
                        "browser_config": {
                            "cookies": cookies,
                            "headers": {
                                "User-Agent": browser_config.extra_args[-1].split("=")[1]
                            }
                        }
                    }
                else:
                    return login_result
                    
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _fill_login_form(self, crawler: AsyncWebCrawler, username: str, password: str):
        """Fill the login form with credentials"""
        fill_script = f"""
        // Wait for form elements to load
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        const usernameField = document.querySelector('#username');
        const passwordField = document.querySelector('#password');
        const submitBtn = document.querySelector('button[type="submit"]');
        
        if (usernameField && passwordField) {{
            usernameField.value = '{username}';
            usernameField.dispatchEvent(new Event('input', {{ bubbles: true }}));
            
            passwordField.value = '{password}';
            passwordField.dispatchEvent(new Event('input', {{ bubbles: true }}));
            
            await new Promise(resolve => setTimeout(resolve, 500));
            
            if (submitBtn) {{
                submitBtn.click();
                return 'form_submitted';
            }}
        }}
        return 'form_not_found';
        """
        
        result = await crawler.execute_script(fill_script)
        await asyncio.sleep(3)  # Wait for submission
        
    async def _handle_login_challenges(
        self, 
        crawler: AsyncWebCrawler,
        interactive_mode: bool,
        captcha_callback: Optional[callable],
        twofa_callback: Optional[callable]
    ) -> Dict:
        """Handle CAPTCHA, 2FA, and other login challenges"""
        
        max_attempts = 10
        for attempt in range(max_attempts):
            current_url = await crawler.get_current_url()
            page_content = await crawler.get_page_content()
            
            # Check if login was successful
            if self._is_login_successful(current_url, page_content):
                return {"success": True}
            
            # Check for CAPTCHA
            if self._detect_captcha(page_content):
                logger.info("CAPTCHA detected!")
                if interactive_mode:
                    result = await self._handle_captcha_interactive(crawler, captcha_callback)
                    if not result["success"]:
                        return result
                else:
                    return {"success": False, "error": "CAPTCHA detected but interactive mode disabled"}
            
            # Check for 2FA
            elif self._detect_2fa(page_content):
                logger.info("2FA challenge detected!")
                result = await self._handle_2fa(crawler, twofa_callback, interactive_mode)
                if not result["success"]:
                    return result
            
            # Check for security check
            elif self._detect_security_check(page_content):
                logger.info("Security check detected!")
                if interactive_mode:
                    result = await self._handle_security_check_interactive(crawler)
                    if not result["success"]:
                        return result
                else:
                    return {"success": False, "error": "Security check detected but interactive mode disabled"}
            
            # Check for login error
            elif self._detect_login_error(page_content):
                return {"success": False, "error": "Invalid credentials or account locked"}
            
            await asyncio.sleep(2)
        
        return {"success": False, "error": "Login timeout - unable to complete authentication"}
    
    def _is_login_successful(self, url: str, content: str) -> bool:
        """Check if login was successful"""
        success_indicators = [
            "/feed/" in url,
            "/in/" in url,
            "linkedin.com/feed" in url,
            '"authenticationRedirectUrl"' in content,
            'class="global-nav"' in content
        ]
        return any(indicator for indicator in success_indicators)
    
    def _detect_captcha(self, content: str) -> bool:
        """Detect CAPTCHA challenges"""
        captcha_indicators = [
            "captcha" in content.lower(),
            "recaptcha" in content.lower(),
            "challenge" in content.lower() and "verify" in content.lower(),
            'data-sitekey=' in content,
            'g-recaptcha' in content
        ]
        return any(indicator for indicator in captcha_indicators)
    
    def _detect_2fa(self, content: str) -> bool:
        """Detect 2FA challenges"""
        twofa_indicators = [
            "two-step" in content.lower(),
            "verification code" in content.lower(),
            "enter the pin" in content.lower(),
            'name="pin"' in content,
            'id="input__phone_verification_pin"' in content
        ]
        return any(indicator for indicator in twofa_indicators)
    
    def _detect_security_check(self, content: str) -> bool:
        """Detect security verification"""
        security_indicators = [
            "security verification" in content.lower(),
            "verify it's you" in content.lower(),
            "unusual activity" in content.lower(),
            "verify your identity" in content.lower()
        ]
        return any(indicator for indicator in security_indicators)
    
    def _detect_login_error(self, content: str) -> bool:
        """Detect login errors"""
        error_indicators = [
            "incorrect email or password" in content.lower(),
            "couldn't find a linkedin account" in content.lower(),
            "account has been restricted" in content.lower(),
            "too many failed login attempts" in content.lower()
        ]
        return any(indicator for indicator in error_indicators)
    
    async def _handle_captcha_interactive(self, crawler: AsyncWebCrawler, callback: Optional[callable]) -> Dict:
        """Handle CAPTCHA in interactive mode"""
        if callback:
            # Custom callback for CAPTCHA handling
            try:
                await callback(crawler)
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": f"CAPTCHA callback failed: {str(e)}"}
        else:
            # Wait for manual CAPTCHA solving
            logger.info("Please solve the CAPTCHA manually in the browser window...")
            
            # Wait up to 5 minutes for CAPTCHA to be solved
            start_time = time.time()
            while time.time() - start_time < self.max_wait_time:
                await asyncio.sleep(5)
                content = await crawler.get_page_content()
                
                if not self._detect_captcha(content):
                    logger.info("CAPTCHA appears to be solved!")
                    return {"success": True}
            
            return {"success": False, "error": "CAPTCHA solving timeout"}
    
    async def _handle_2fa(self, crawler: AsyncWebCrawler, callback: Optional[callable], interactive_mode: bool) -> Dict:
        """Handle 2FA verification"""
        if callback:
            # Custom callback for 2FA code
            try:
                code = await callback()
                await self._submit_2fa_code(crawler, code)
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": f"2FA callback failed: {str(e)}"}
        elif interactive_mode:
            # Wait for manual 2FA code entry
            logger.info("Please enter the 2FA code manually in the browser window...")
            
            start_time = time.time()
            while time.time() - start_time < self.max_wait_time:
                await asyncio.sleep(5)
                content = await crawler.get_page_content()
                url = await crawler.get_current_url()
                
                if self._is_login_successful(url, content):
                    logger.info("2FA appears to be completed!")
                    return {"success": True}
            
            return {"success": False, "error": "2FA completion timeout"}
        else:
            return {"success": False, "error": "2FA required but no handler provided"}
    
    async def _submit_2fa_code(self, crawler: AsyncWebCrawler, code: str):
        """Submit 2FA verification code"""
        submit_script = f"""
        const pinField = document.querySelector('#input__phone_verification_pin') || 
                        document.querySelector('input[name="pin"]') ||
                        document.querySelector('input[type="text"][maxlength="6"]');
        
        if (pinField) {{
            pinField.value = '{code}';
            pinField.dispatchEvent(new Event('input', {{ bubbles: true }}));
            
            const submitBtn = document.querySelector('button[type="submit"]') ||
                             document.querySelector('button[data-id="verification-submit-button"]');
            
            if (submitBtn) {{
                submitBtn.click();
                return 'code_submitted';
            }}
        }}
        return 'field_not_found';
        """
        
        await crawler.execute_script(submit_script)
        await asyncio.sleep(3)
    
    async def _handle_security_check_interactive(self, crawler: AsyncWebCrawler) -> Dict:
        """Handle security verification in interactive mode"""
        logger.info("Please complete the security verification manually...")
        
        start_time = time.time()
        while time.time() - start_time < self.max_wait_time:
            await asyncio.sleep(5)
            content = await crawler.get_page_content()
            url = await crawler.get_current_url()
            
            if self._is_login_successful(url, content):
                logger.info("Security verification completed!")
                return {"success": True}
        
        return {"success": False, "error": "Security verification timeout"}
    
    async def _extract_session_cookies(self, crawler: AsyncWebCrawler) -> list:
        """Extract LinkedIn session cookies"""
        try:
            cookies = await crawler.get_cookies()
            linkedin_cookies = []
            
            for cookie in cookies:
                if cookie.get("domain") in [".linkedin.com", "linkedin.com", ".www.linkedin.com"]:
                    linkedin_cookies.append({
                        "name": cookie["name"],
                        "value": cookie["value"],
                        "domain": cookie["domain"],
                        "path": cookie.get("path", "/"),
                        "secure": cookie.get("secure", True),
                        "httpOnly": cookie.get("httpOnly", False)
                    })
            
            return linkedin_cookies
        except Exception as e:
            logger.error(f"Error extracting cookies: {str(e)}")
            return []

# Helper functions for callbacks
async def console_2fa_callback() -> str:
    """Simple console-based 2FA code input"""
    import aioconsole
    code = await aioconsole.ainput("Enter your 2FA code: ")
    return code.strip()

async def console_captcha_callback(crawler: AsyncWebCrawler):
    """Simple console-based CAPTCHA handler"""
    import aioconsole
    await aioconsole.ainput("Please solve the CAPTCHA in the browser and press Enter...")