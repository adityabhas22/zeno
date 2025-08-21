"""
Zeno Application Settings

Centralized configuration management using Pydantic settings.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "Zeno"
    version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    
    # Database (optional with default)
    database_url: str = "sqlite:///./zeno.db"
    database_echo: bool = False
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # LiveKit (optional with defaults for testing)
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_url: str = ""
    
    # Authentication (optional with defaults)
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    
    # Clerk Authentication
    clerk_secret_key: str = ""
    clerk_webhook_secret: str = "dev"
    
    # Google Workspace (optional)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8790"
    
    # External APIs
    weather_api_key: Optional[str] = None
    traffic_api_key: Optional[str] = None
    
    # iOS Push Notifications
    apns_key_id: Optional[str] = None
    apns_team_id: Optional[str] = None
    apns_bundle_id: Optional[str] = None
    apns_private_key_path: Optional[str] = None
    apns_use_sandbox: bool = True
    
    # File Paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    credentials_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "credentials")
    logs_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "logs")
    
    # Agent Configuration
    agent_max_tool_steps: int = 12
    agent_preemptive_generation: bool = False
    agent_allow_interruptions: bool = True
    
    # Daily Planning
    default_briefing_time: str = "08:00"
    max_daily_tasks: int = 20


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()