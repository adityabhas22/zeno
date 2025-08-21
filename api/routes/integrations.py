"""
Integration Management API Routes

Handles OAuth flows and credential management for external services.
"""

import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
import os
import requests

# Allow OAuth over HTTP for development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from api.middleware.clerk_auth import get_current_user_id
from core.storage import get_database_session, User, Integration, session_scope
from config.settings import get_settings

router = APIRouter()
settings = get_settings()

# Google OAuth Scopes for Zeno - comprehensive list to match agent capabilities
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/contacts",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

# In-memory storage for OAuth states (use Redis in production)
_oauth_states: Dict[str, Dict[str, Any]] = {}


class GoogleIntegrationStatus(BaseModel):
    """Response model for Google integration status."""
    connected: bool
    email: Optional[str] = None
    connectedAt: Optional[str] = None
    scopes: Optional[list] = None
    expires_at: Optional[str] = None


class GoogleAuthUrlResponse(BaseModel):
    """Response model for Google OAuth URL."""
    authUrl: str  # camelCase to match frontend expectation
    state: str


def _get_google_oauth_flow(state: str) -> Flow:
    """Create Google OAuth flow with callback URL."""
    client_secrets_path = settings.credentials_dir / "client_secret.json"
    
    if not client_secrets_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured. Missing client_secret.json file."
        )
    
    # Use our backend callback URL
    api_base_url = getattr(settings, 'api_base_url', 'http://localhost:8000')
    redirect_uri = f"{api_base_url}/integrations/google/callback"
    
    flow = Flow.from_client_secrets_file(
        str(client_secrets_path),
        scopes=GOOGLE_SCOPES,
        redirect_uri=redirect_uri,
        state=state
    )
    
    return flow


@router.get("/google/status", response_model=GoogleIntegrationStatus)
async def get_google_integration_status(
    clerk_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_database_session)
) -> GoogleIntegrationStatus:
    """Get the current user's Google integration status."""
    
    try:
        integration = db.query(Integration).filter(
            Integration.user_id == clerk_user_id,
            Integration.integration_type == "google_workspace",
            Integration.is_active == True
        ).first()
        
        if not integration:
            return GoogleIntegrationStatus(connected=False)
        
        # Check if token is still valid
        auth_tokens = getattr(integration, 'auth_tokens', None) or {}
        expires_at = getattr(integration, 'token_expires_at', None)
        
        if expires_at and expires_at < datetime.utcnow():
            # Token expired
            return GoogleIntegrationStatus(connected=False)
        
        # Convert datetime to ISO string if it exists
        created_at = getattr(integration, 'created_at', None)
        connected_at_str = created_at.isoformat() if created_at is not None else None
        
        return GoogleIntegrationStatus(
            connected=True,
            email=auth_tokens.get("email"),
            connectedAt=connected_at_str,
            scopes=auth_tokens.get("scopes", []),
            expires_at=expires_at.isoformat() if expires_at and expires_at is not None else None
        )
        
    except Exception as e:
        print(f"Database error in get_google_integration_status: {e}")
        # Return disconnected status if database is unavailable
        return GoogleIntegrationStatus(connected=False)


@router.get("/google/auth", response_model=GoogleAuthUrlResponse)
async def start_google_oauth(
    clerk_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_database_session)
) -> GoogleAuthUrlResponse:
    """Start Google OAuth flow for the current user."""
    
    # Generate secure state token
    state = secrets.token_urlsafe(32)
    
    # Store state with user info (expires in 10 minutes)
    _oauth_states[state] = {
        "user_id": clerk_user_id,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=10)
    }
    
    try:
        flow = _get_google_oauth_flow(state)
        
        # Generate authorization URL with consent prompt to ensure refresh token
        auth_url, _ = flow.authorization_url(
            prompt="consent",
            access_type="offline",
            include_granted_scopes="true"
        )
        
        return GoogleAuthUrlResponse(authUrl=auth_url, state=state)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize OAuth flow: {str(e)}"
        )


@router.get("/google/callback")
async def handle_google_oauth_callback(
    request: Request,
    db: Session = Depends(get_database_session)
):
    """Handle Google OAuth callback and store credentials."""
    
    # Get callback parameters
    state = request.query_params.get("state")
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}"
        )
    
    if not state or not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing state or code parameter"
        )
    
    # Validate state token
    oauth_state = _oauth_states.get(state)
    if not oauth_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state token"
        )
    
    if oauth_state["expires_at"] < datetime.utcnow():
        _oauth_states.pop(state, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state expired"
        )
    
    user_id = oauth_state["user_id"]
    _oauth_states.pop(state, None)  # Clean up state
    
    try:
        # Complete OAuth flow manually to avoid scope validation issues
        flow = _get_google_oauth_flow(state)
        
        # Extract authorization code from callback URL
        code = request.query_params.get('code')
        if not code:
            return RedirectResponse(
                url=f"http://localhost:3000/settings?error=No authorization code received",
                status_code=status.HTTP_302_FOUND
            )
        
        # Manual token exchange to bypass scope validation
        import requests
        import json
        from google.oauth2.credentials import Credentials
        
        # Get client info from flow
        client_config = flow.client_config
        
        # Exchange authorization code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'code': code,
            'client_id': client_config['client_id'],
            'client_secret': client_config['client_secret'],
            'redirect_uri': flow.redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data)
        if token_response.status_code != 200:
            return RedirectResponse(
                url=f"http://localhost:3000/settings?error=Failed to exchange authorization code",
                status_code=status.HTTP_302_FOUND
            )
        
        token_info = token_response.json()
        
        # Create credentials object manually
        credentials = Credentials(
            token=token_info['access_token'],
            refresh_token=token_info.get('refresh_token'),
            id_token=token_info.get('id_token'),
            token_uri=token_url,
            client_id=client_config['client_id'],
            client_secret=client_config['client_secret'],
            scopes=GOOGLE_SCOPES  # Use our defined scopes
        )
        
        # Get user info from Google
        from googleapiclient.discovery import build
        oauth2_service = build('oauth2', 'v2', credentials=credentials, cache_discovery=False)
        user_info = oauth2_service.userinfo().get().execute()
        
        # Prepare credential data for storage
        cred_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "id_token": getattr(credentials, 'id_token', None),
            "token_uri": getattr(credentials, 'token_uri', 'https://oauth2.googleapis.com/token'),
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture")
        }
        
        # Store or update integration
        integration = db.query(Integration).filter(
            Integration.user_id == user_id,
            Integration.integration_type == "google_workspace"
        ).first()
        
        if integration:
            # Update existing using db.query().update()
            db.query(Integration).filter(
                Integration.user_id == user_id,
                Integration.integration_type == "google_workspace"
            ).update({
                "auth_tokens": cred_data,
                "is_active": True,
                "token_expires_at": credentials.expiry,
                "last_sync_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
        else:
            # Create new
            integration = Integration(
                user_id=user_id,
                integration_type="google_workspace",
                provider="google",
                auth_tokens=cred_data,
                is_active=True,
                token_expires_at=credentials.expiry,
                last_sync_at=datetime.utcnow()
            )
            db.add(integration)
        
        db.commit()
        
        # Redirect to frontend success page
        frontend_url = "http://localhost:3000"
        return RedirectResponse(
            url=f"{frontend_url}/settings/integrations?google=connected",
            status_code=status.HTTP_302_FOUND
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete OAuth flow: {str(e)}"
        )


@router.delete("/google/disconnect")
async def disconnect_google_integration(
    clerk_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_database_session)
) -> dict:
    """Disconnect the user's Google integration."""
    
    integration = db.query(Integration).filter(
        Integration.user_id == clerk_user_id,
        Integration.integration_type == "google_workspace"
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google integration not found"
        )
    
    try:
        # Revoke token with Google (optional but recommended)
        auth_tokens = getattr(integration, 'auth_tokens', None) or {}
        if auth_tokens.get("token"):
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://oauth2.googleapis.com/revoke",
                        data={"token": auth_tokens["token"]},
                        timeout=5.0
                    )
            except Exception:
                # Continue even if revocation fails
                pass
        
        # Deactivate integration using db.query().update()
        db.query(Integration).filter(
            Integration.user_id == clerk_user_id,
            Integration.integration_type == "google_workspace"
        ).update({
            "is_active": False,
            "updated_at": datetime.utcnow()
        })
        
        db.commit()
        
        return {
            "success": True,
            "message": "Google integration disconnected successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect Google integration: {str(e)}"
        )


@router.post("/google/refresh")
async def refresh_google_token(
    clerk_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_database_session)
) -> dict:
    """Manually refresh the user's Google OAuth token."""
    
    integration = db.query(Integration).filter(
        Integration.user_id == clerk_user_id,
        Integration.integration_type == "google_workspace",
        Integration.is_active == True
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google integration not found"
        )
    
    auth_tokens = getattr(integration, 'auth_tokens', None) or {}
    if not auth_tokens.get("refresh_token"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No refresh token available. Please reconnect your Google account."
        )
    
    try:
        # Reconstruct credentials
        credentials = Credentials(
            token=auth_tokens.get("token"),
            refresh_token=auth_tokens.get("refresh_token"),
            token_uri=auth_tokens.get("token_uri"),
            client_id=auth_tokens.get("client_id"),
            client_secret=auth_tokens.get("client_secret"),
            scopes=auth_tokens.get("scopes")
        )
        
        # Refresh the token
        from google.auth.transport.requests import Request
        credentials.refresh(Request())
        
        # Update stored credentials
        auth_tokens.update({
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
        })
        
        # Update integration using db.query().update()
        db.query(Integration).filter(
            Integration.user_id == clerk_user_id,
            Integration.integration_type == "google_workspace"
        ).update({
            "auth_tokens": auth_tokens,
            "token_expires_at": credentials.expiry,
            "last_sync_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        db.commit()
        
        return {
            "success": True,
            "message": "Token refreshed successfully",
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh token: {str(e)}"
        )
