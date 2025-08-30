"""
Clerk JWT Authentication Middleware for FastAPI.

Handles JWT token verification for protected routes.
"""

import jwt
import requests
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config.settings import get_settings


# Global bearer token scheme - auto_error=False to allow CORS preflight
bearer_scheme = HTTPBearer(auto_error=False)
settings = get_settings()

# Cache for Clerk public keys
_clerk_jwks_cache = None


def get_clerk_public_keys() -> Dict[str, Any]:
    """Get Clerk's public keys for JWT verification."""
    global _clerk_jwks_cache
    
    if _clerk_jwks_cache is None:
        try:
            # Clerk provides public keys at their JWKS endpoint
            # Extract instance ID from secret key
            if settings.clerk_secret_key.startswith("sk_"):
                # For development, we'll use a simpler approach
                # In production, you'd want to fetch from Clerk's JWKS endpoint
                _clerk_jwks_cache = {"dev": "dev_mode"}
            else:
                response = requests.get("https://api.clerk.com/v1/jwks")
                response.raise_for_status()
                _clerk_jwks_cache = response.json()
        except Exception as e:
            print(f"Error fetching Clerk public keys: {e}")
            _clerk_jwks_cache = {"error": str(e)}
    
    return _clerk_jwks_cache


def verify_clerk_jwt(token: str) -> Dict[str, Any]:
    """
    Verify a Clerk JWT token and return the payload.
    
    Args:
        token: The JWT token to verify
        
    Returns:
        The decoded JWT payload
        
    Raises:
        HTTPException: If the token is invalid
    """
    try:
        # For development, we'll decode without verification
        # In production, you'd verify with Clerk's public key
        if settings.clerk_secret_key.startswith("sk_test_"):
            # Development mode - decode without verification
            payload = jwt.decode(token, options={"verify_signature": False})
            print(f"🔓 DEV MODE: Decoded JWT payload: {payload}")
            return payload
        else:
            # Production mode - verify with Clerk's public key
            # This would need proper JWKS key fetching and verification
            # For now, we'll use unverified decoding
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
            
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get the current authenticated user.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"message": f"Hello {user['sub']}"}
    """
    if not credentials:
        print("❌ No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        token = credentials.credentials
        payload = verify_clerk_jwt(token)
        
        # Extract user information from JWT payload
        user_info = {
            "clerk_user_id": payload.get("sub"),
            "email": payload.get("email"),
            "first_name": payload.get("given_name"),
            "last_name": payload.get("family_name"),
            "full_payload": payload
        }
        
        print(f"✅ Authenticated user: {user_info['clerk_user_id']} ({user_info['email']})")
        return user_info
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> str:
    """
    FastAPI dependency to get just the clerk_user_id string.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user_id: str = Depends(get_current_user_id)):
            return {"message": f"Hello {user_id}"}
    """
    user_info = await get_current_user(credentials)
    return user_info["clerk_user_id"]


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency for optional authentication.
    
    Returns user info if authenticated, None if not.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


async def get_current_user_loose(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Dict[str, Any]:
    """
    Development-friendly dependency: prefer Bearer JWT via Clerk, but if unavailable,
    accept Clerk identity provided via headers from native clients:
      - X-Clerk-UserId
      - X-Clerk-Email
      - X-Clerk-First-Name
      - X-Clerk-Last-Name

    This mirrors the React starter's requirement (always auth), but unblocks
    native dev environments where fetching a JWT can intermittently fail.
    """
    try:
        user = await get_current_user(credentials)
        return user
    except HTTPException:
        uid = request.headers.get("x-clerk-user-id") or request.headers.get("X-Clerk-UserId")
        if uid:
            return {
                "clerk_user_id": uid,
                "email": request.headers.get("x-clerk-email") or request.headers.get("X-Clerk-Email"),
                "first_name": request.headers.get("x-clerk-first-name") or request.headers.get("X-Clerk-First-Name"),
                "last_name": request.headers.get("x-clerk-last-name") or request.headers.get("X-Clerk-Last-Name"),
                "full_payload": {},
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
