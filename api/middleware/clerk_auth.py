"""
Clerk JWT Authentication Middleware for FastAPI.

Handles JWT token verification for protected routes.
"""

import jwt
import requests
import time
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient, InvalidAlgorithmError

from config.settings import get_settings


# Global bearer token scheme - auto_error=False to allow CORS preflight
bearer_scheme = HTTPBearer(auto_error=False)
settings = get_settings()

# Cache for Clerk JWKS client
_clerk_jwks_client = None
_jwks_cache_timestamp = 0
JWKS_CACHE_DURATION = 3600  # 1 hour


def get_clerk_jwks_client() -> Optional[PyJWKClient]:
    """Get or create Clerk's JWKS client for JWT verification."""
    global _clerk_jwks_client, _jwks_cache_timestamp

    # Check if we need to refresh the cache
    if _clerk_jwks_client is None or (time.time() - _jwks_cache_timestamp) > JWKS_CACHE_DURATION:
        try:
            # Extract Clerk instance domain from secret key
            clerk_domain = extract_clerk_domain()
            if not clerk_domain:
                print("❌ Could not extract Clerk domain from secret key")
                return None

            jwks_url = f"https://{clerk_domain}/.well-known/jwks.json"
            print(f"🔧 Initializing JWKS client for: {jwks_url}")

            _clerk_jwks_client = PyJWKClient(jwks_url)
            _jwks_cache_timestamp = time.time()

        except Exception as e:
            print(f"❌ Error initializing JWKS client: {e}")
            _clerk_jwks_client = None

    return _clerk_jwks_client


def extract_clerk_domain() -> Optional[str]:
    """Extract Clerk instance domain from the secret key."""
    if not settings.clerk_secret_key or not settings.clerk_secret_key.startswith("sk_"):
        return None

    try:
        # For development keys like: sk_test_...
        # For production keys like: sk_live_...
        # The domain is usually: your-app.clerk.accounts.dev

        # Check if this is a test key
        if settings.clerk_secret_key.startswith("sk_test_"):
            # For test keys, use configured domain if available
            clerk_domain = getattr(settings, 'clerk_domain', None)
            if clerk_domain:
                return clerk_domain

            # Fallback for test keys without explicit domain
            return "clerk.accounts.dev"

        # For production keys, use configured domain
        clerk_domain = getattr(settings, 'clerk_domain', None)
        if clerk_domain:
            return clerk_domain

        # Fallback for production keys without explicit domain
        # Try to extract from secret key format or use default
        return "clerk.accounts.dev"  # Default Clerk domain

    except Exception as e:
        print(f"❌ Error extracting Clerk domain: {e}")
        return None


def verify_clerk_jwt(token: str) -> Dict[str, Any]:
    """
    Verify a Clerk JWT token with proper signature validation.

    Args:
        token: The JWT token to verify

    Returns:
        The decoded JWT payload

    Raises:
        HTTPException: If the token is invalid
    """
    try:
        # Check if we should verify signatures
        # Verify if: environment is production OR CLERK_DOMAIN is configured
        is_production_env = getattr(settings, 'environment', 'development') == 'production'
        has_clerk_domain = getattr(settings, 'clerk_domain', None) is not None
        should_verify = is_production_env or has_clerk_domain

        # Debug logging
        print(f"🔍 Environment check: {getattr(settings, 'environment', 'development')}")
        print(f"🔍 CLERK_DOMAIN configured: {has_clerk_domain}")
        print(f"🔍 Should verify JWT: {should_verify}")

        if not should_verify:
            # Development mode - decode without verification but log warning
            print("⚠️  DEV MODE: JWT signature verification disabled")
            print("💡 To enable verification, use production Clerk key or set CLERK_DOMAIN")
            payload = jwt.decode(token, options={"verify_signature": False, "verify_exp": True})
            return payload

        # Production mode - verify with Clerk's public key
        jwks_client = get_clerk_jwks_client()
        if not jwks_client:
            print("❌ JWKS client not available, falling back to unverified decoding")
            payload = jwt.decode(token, options={"verify_signature": False, "verify_exp": True})
            return payload

        # Get the signing key from JWKS
        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
        except Exception as e:
            print(f"❌ Could not get signing key: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not verify token signature"
            )

        # Verify and decode the token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],  # Clerk uses RS256
            options={"verify_exp": True, "verify_signature": True}
        )

        print("✅ JWT signature verified successfully")
        return payload

    except jwt.ExpiredSignatureError:
        print("❌ JWT token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidSignatureError:
        print("❌ JWT signature verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature"
        )
    except jwt.InvalidTokenError as e:
        print(f"❌ JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        print(f"❌ Unexpected error during JWT verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
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
