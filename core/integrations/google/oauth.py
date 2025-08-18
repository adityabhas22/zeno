"""
Google OAuth Authentication for Zeno

Enhanced OAuth handling with Zeno-specific configuration.
"""

from __future__ import annotations

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlparse, parse_qs

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow

from config.settings import get_settings


def _get_credentials_paths():
    """Get credential file paths from settings."""
    settings = get_settings()
    client_secrets_path = settings.credentials_dir / "client_secret.json"
    token_path = settings.credentials_dir / "token.json"
    return client_secrets_path, token_path


def _load_credentials(token_path: Path) -> Optional[Credentials]:
    """Load existing credentials from token file."""
    if not token_path.exists():
        return None
    try:
        return Credentials.from_authorized_user_file(str(token_path))
    except Exception:
        return None


def _save_credentials(creds: Credentials, token_path: Path) -> None:
    """Save credentials to token file."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with token_path.open("w") as f:
        f.write(creds.to_json())


class _OAuthHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""
    auth_response_url: Optional[str] = None

    def do_GET(self):  # noqa: N802 (HTTPServer name)
        type(self).auth_response_url = self.requestline.split(" ")[1]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Zeno Authentication Complete</h1>"
            b"<p>You may close this window and return to Zeno.</p></body></html>"
        )

    def log_message(self, format, *args):
        """Suppress log messages."""
        pass


def ensure_credentials(scopes: Iterable[str]) -> Credentials:
    """
    Ensure valid Google OAuth credentials for the given scopes.
    
    Args:
        scopes: List of Google API scopes needed
        
    Returns:
        Valid Google OAuth credentials
        
    Raises:
        RuntimeError: If authentication fails
    """
    client_secrets_path, token_path = _get_credentials_paths()
    scopes = list(scopes)
    
    # Check if client secrets file exists
    if not client_secrets_path.exists():
        raise RuntimeError(
            f"Google client_secret.json not found at {client_secrets_path}. "
            "Please add your Google OAuth credentials to enable Google Workspace integration."
        )
    
    # Try to load existing credentials
    creds = _load_credentials(token_path)

    # Check if credentials are valid and have required scopes
    if creds and creds.valid and set(scopes).issubset(set(creds.scopes or [])):
        return creds

    # Try to refresh expired credentials
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            if set(scopes).issubset(set(creds.scopes or [])):
                _save_credentials(creds, token_path)
                return creds
        except Exception as e:
            print(f"Failed to refresh credentials: {e}")

    # Need to run OAuth flow
    print("🔐 Zeno needs Google Workspace access. Opening browser for authentication...")
    
    # Set environment variable to allow HTTP for local development
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets_path), scopes=scopes
        )
        # Force prompt=consent to ensure we get a refresh token
        creds = flow.run_local_server(
            port=8790, 
            prompt='consent',
            open_browser=True
        )
        
        _save_credentials(creds, token_path)
        print("✅ Google Workspace authentication successful!")
        return creds
        
    except Exception as e:
        raise RuntimeError(f"Google OAuth authentication failed: {e}")


def get_service(api_name: str, api_version: str, scopes: Iterable[str]):
    """
    Get authenticated Google API service.
    
    Args:
        api_name: Google API service name (e.g., 'calendar', 'gmail')
        api_version: API version (e.g., 'v3', 'v1')
        scopes: Required OAuth scopes
        
    Returns:
        Authenticated Google API service client
    """
    from googleapiclient.discovery import build
    
    creds = ensure_credentials(scopes)
    return build(api_name, api_version, credentials=creds, cache_discovery=False)
