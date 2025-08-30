"""
User-Specific Google OAuth for Zeno

Enhanced OAuth handling with per-user credential storage and management.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Iterable, Optional
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config.settings import get_settings
from core.storage import session_scope, Integration, User


def get_user_credentials(user_id: str, scopes: Iterable[str]) -> Optional[Credentials]:
    """
    Get Google OAuth credentials for a specific user.
    
    Args:
        user_id: Clerk user ID
        scopes: Required OAuth scopes
        
    Returns:
        Valid Google OAuth credentials or None if not available
    """
    scopes = list(scopes)
    
    try:
        with session_scope() as db:
            integration = db.query(Integration).filter(
                Integration.user_id == user_id,
                Integration.integration_type == "google_workspace",
                Integration.is_active == True
            ).first()
            
            if not integration or not getattr(integration, 'auth_tokens', None):
                return None
            
            auth_tokens = getattr(integration, 'auth_tokens', None) or {}
            
            # Reconstruct credentials from stored data
            credentials = Credentials(
                token=auth_tokens.get("token"),
                refresh_token=auth_tokens.get("refresh_token"),
                id_token=auth_tokens.get("id_token"),
                token_uri=auth_tokens.get("token_uri"),
                client_id=auth_tokens.get("client_id"),
                client_secret=auth_tokens.get("client_secret"),
                scopes=auth_tokens.get("scopes", [])
            )
            
            # Check if credentials have required scopes
            if not set(scopes).issubset(set(credentials.scopes or [])):
                print(f"⚠️  User {user_id} missing required scopes: {set(scopes) - set(credentials.scopes or [])}")
                return None
            
            # Check if token is expired and refresh if needed
            if credentials.expired and credentials.refresh_token:
                try:
                    print(f"🔄 Refreshing expired token for user {user_id}")
                    credentials.refresh(Request())
                    
                    # Update stored credentials
                    if auth_tokens:
                        auth_tokens.update({
                            "token": credentials.token,
                            "refresh_token": credentials.refresh_token,
                        })

                    # Update integration using object properties (encryption handled automatically)
                    integration.auth_tokens = auth_tokens
                    setattr(integration, 'token_expires_at', credentials.expiry)
                    setattr(integration, 'last_sync_at', datetime.utcnow())
                    setattr(integration, 'updated_at', datetime.utcnow())
                    
                    db.commit()
                    print(f"✅ Token refreshed for user {user_id}")
                    
                except Exception as e:
                    print(f"❌ Failed to refresh token for user {user_id}: {e}")
                    return None
            
            elif credentials.expired:
                print(f"❌ Token expired for user {user_id} and no refresh token available")
                return None
            
            return credentials
            
    except Exception as e:
        print(f"❌ Error getting credentials for user {user_id}: {e}")
        return None


def get_user_service(user_id: str, api_name: str, api_version: str, scopes: Iterable[str]):
    """
    Get authenticated Google API service for a specific user.
    
    Args:
        user_id: Clerk user ID
        api_name: Google API service name (e.g., 'calendar', 'gmail')
        api_version: API version (e.g., 'v3', 'v1')
        scopes: Required OAuth scopes
        
    Returns:
        Authenticated Google API service client or None if not available
        
    Raises:
        Exception: If user hasn't connected their Google account
    """
    credentials = get_user_credentials(user_id, scopes)
    
    if not credentials:
        raise Exception(
            f"User {user_id} has not connected their Google account. "
            "Please connect your Google account in settings to use this feature."
        )
    
    try:
        return build(api_name, api_version, credentials=credentials, cache_discovery=False)
    except Exception as e:
        raise Exception(f"Failed to create Google API service: {e}")


def check_user_has_google_access(user_id: str, scopes: Optional[Iterable[str]] = None) -> bool:
    """
    Check if a user has connected their Google account with required scopes.
    
    Args:
        user_id: Clerk user ID
        scopes: Optional list of required scopes to check
        
    Returns:
        True if user has valid Google credentials, False otherwise
    """
    try:
        with session_scope() as db:
            integration = db.query(Integration).filter(
                Integration.user_id == user_id,
                Integration.integration_type == "google_workspace",
                Integration.is_active == True
            ).first()
            
            if not integration or not getattr(integration, 'auth_tokens', None):
                return False
            
            # Check token expiry
            expires_at = getattr(integration, 'token_expires_at', None)
            if expires_at and expires_at < datetime.utcnow():
                # Check if we have a refresh token
                auth_tokens = getattr(integration, 'auth_tokens', None) or {}
                if not auth_tokens.get("refresh_token"):
                    return False
            
            # Check scopes if provided
            if scopes:
                auth_tokens = getattr(integration, 'auth_tokens', None) or {}
                user_scopes = auth_tokens.get("scopes", [])
                if not set(scopes).issubset(set(user_scopes)):
                    return False
            
            return True
            
    except Exception:
        return False


def get_user_google_info(user_id: str) -> Optional[dict]:
    """
    Get user's Google account information.
    
    Args:
        user_id: Clerk user ID
        
    Returns:
        Dictionary with user's Google account info or None
    """
    try:
        with session_scope() as db:
            integration = db.query(Integration).filter(
                Integration.user_id == user_id,
                Integration.integration_type == "google_workspace",
                Integration.is_active == True
            ).first()
            
            if not integration or not getattr(integration, 'auth_tokens', None):
                return None
            
            auth_tokens = getattr(integration, 'auth_tokens', None) or {}
            created_at = getattr(integration, 'created_at', None)
            last_sync_at = getattr(integration, 'last_sync_at', None)
            
            return {
                "email": auth_tokens.get("email"),
                "name": auth_tokens.get("name"),
                "picture": auth_tokens.get("picture"),
                "connected_at": created_at.isoformat() if created_at else None,
                "last_sync": last_sync_at.isoformat() if last_sync_at else None,
                "scopes": auth_tokens.get("scopes", [])
            }
            
    except Exception:
        return None


# Fallback function for backward compatibility with existing code
def ensure_credentials(scopes: Iterable[str]) -> Credentials:
    """
    Fallback to global credentials for backward compatibility.
    
    This function maintains compatibility with existing code that doesn't
    pass user_id. In production, this should be phased out in favor of
    user-specific credentials.
    """
    from .oauth import ensure_credentials as _ensure_global_credentials
    
    print("⚠️  Using global credentials. Consider updating to user-specific credentials.")
    return _ensure_global_credentials(scopes)


def get_service(api_name: str, api_version: str, scopes: Iterable[str]):
    """
    Fallback to global service for backward compatibility.
    
    This function maintains compatibility with existing code that doesn't
    pass user_id. In production, this should be phased out in favor of
    user-specific services.
    """
    from .oauth import get_service as _get_global_service
    
    print("⚠️  Using global service. Consider updating to user-specific service.")
    return _get_global_service(api_name, api_version, scopes)
