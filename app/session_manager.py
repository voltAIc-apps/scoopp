import json
import time
from typing import Dict, Optional
import logging
from redis import asyncio as aioredis

logger = logging.getLogger(__name__)

class LinkedInSessionManager:
    """Manage LinkedIn session cookies with Redis persistence"""
    
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis
        self.session_ttl = 86400 * 7  # 7 days
        
    async def save_session(self, username: str, cookies: list, user_agent: str = None) -> bool:
        """Save LinkedIn session cookies to Redis"""
        try:
            session_data = {
                "cookies": cookies,
                "user_agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "created_at": int(time.time()),
                "last_validated": int(time.time())
            }
            
            session_key = f"linkedin_session:{username}"
            await self.redis.setex(
                session_key,
                self.session_ttl,
                json.dumps(session_data)
            )
            
            logger.info(f"Saved LinkedIn session for {username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session for {username}: {str(e)}")
            return False
    
    async def get_session(self, username: str) -> Optional[Dict]:
        """Get LinkedIn session cookies from Redis"""
        try:
            session_key = f"linkedin_session:{username}"
            session_data = await self.redis.get(session_key)
            
            if session_data:
                data = json.loads(session_data)
                logger.info(f"Retrieved LinkedIn session for {username}")
                return data
            
            logger.info(f"No session found for {username}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session for {username}: {str(e)}")
            return None
    
    async def validate_and_refresh_session(self, username: str, config: dict) -> Optional[Dict]:
        """Validate existing session and refresh if needed"""
        try:
            session_data = await self.get_session(username)
            if not session_data:
                return None
            
            # Check if session was validated recently (within 1 hour)
            last_validated = session_data.get("last_validated", 0)
            if time.time() - last_validated < 3600:  # 1 hour
                logger.info(f"Session for {username} is recently validated")
                return session_data
            
            # Validate session with LinkedIn
            from api import validate_linkedin_session
            is_valid = await validate_linkedin_session(session_data["cookies"], config)
            
            if is_valid:
                # Update last_validated timestamp
                session_data["last_validated"] = int(time.time())
                await self.save_session(
                    username, 
                    session_data["cookies"], 
                    session_data.get("user_agent")
                )
                logger.info(f"Session for {username} validated and refreshed")
                return session_data
            else:
                # Session is invalid, remove it
                await self.remove_session(username)
                logger.info(f"Invalid session for {username} removed")
                return None
                
        except Exception as e:
            logger.error(f"Failed to validate session for {username}: {str(e)}")
            return None
    
    async def remove_session(self, username: str) -> bool:
        """Remove LinkedIn session from Redis"""
        try:
            session_key = f"linkedin_session:{username}"
            result = await self.redis.delete(session_key)
            logger.info(f"Removed session for {username}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to remove session for {username}: {str(e)}")
            return False
    
    async def list_sessions(self) -> list:
        """List all stored LinkedIn sessions"""
        try:
            pattern = "linkedin_session:*"
            keys = await self.redis.keys(pattern)
            
            sessions = []
            for key in keys:
                username = key.decode().replace("linkedin_session:", "")
                session_data = await self.get_session(username)
                if session_data:
                    sessions.append({
                        "username": username,
                        "created_at": session_data.get("created_at"),
                        "last_validated": session_data.get("last_validated")
                    })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {str(e)}")
            return []

async def get_or_create_linkedin_session(
    username: str,
    password: str,
    redis: aioredis.Redis,
    config: dict,
    force_new: bool = False
) -> Optional[Dict]:
    """Get existing session or create new one with login"""
    session_manager = LinkedInSessionManager(redis)
    
    # Try to get existing session first (unless force_new)
    if not force_new:
        session_data = await session_manager.validate_and_refresh_session(username, config)
        if session_data:
            logger.info(f"Using existing session for {username}")
            return {
                "success": True,
                "source": "cached",
                "browser_config": {
                    "cookies": session_data["cookies"],
                    "headers": {
                        "User-Agent": session_data.get("user_agent")
                    }
                }
            }
    
    # Need to create new session
    logger.info(f"Creating new LinkedIn session for {username}")
    from api import handle_linkedin_login
    
    login_result = await handle_linkedin_login(
        username=username,
        password=password,
        config=config,
        interactive_mode=True,
        use_2fa_callback=True
    )
    
    if login_result["success"]:
        # Save the new session
        await session_manager.save_session(
            username=username,
            cookies=login_result["cookies"],
            user_agent=login_result["browser_config"]["headers"]["User-Agent"]
        )
        
        login_result["source"] = "new_login"
        logger.info(f"New LinkedIn session created and saved for {username}")
    
    return login_result