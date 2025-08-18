"""
Zeno Application Settings

Centralized configuration management using Pydantic settings.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Zeno"
    version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # LiveKit
    livekit_api_key: str = Field(env="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(env="LIVEKIT_API_SECRET")
    livekit_url: str = Field(env="LIVEKIT_URL")
    
    # Authentication
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, env="JWT_EXPIRE_MINUTES")  # 24 hours
    
    # Google Workspace
    google_client_id: str = Field(env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(env="GOOGLE_REDIRECT_URI")
    
    # External APIs
    weather_api_key: Optional[str] = Field(default=None, env="WEATHER_API_KEY")
    traffic_api_key: Optional[str] = Field(default=None, env="TRAFFIC_API_KEY")
    
    # iOS Push Notifications
    apns_key_id: Optional[str] = Field(default=None, env="APNS_KEY_ID")
    apns_team_id: Optional[str] = Field(default=None, env="APNS_TEAM_ID")
    apns_bundle_id: Optional[str] = Field(default=None, env="APNS_BUNDLE_ID")
    apns_private_key_path: Optional[str] = Field(default=None, env="APNS_PRIVATE_KEY_PATH")
    apns_use_sandbox: bool = Field(default=True, env="APNS_USE_SANDBOX")
    
    # File Paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    credentials_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "credentials")
    logs_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "logs")
    
    # Agent Configuration
    agent_max_tool_steps: int = Field(default=12, env="AGENT_MAX_TOOL_STEPS")
    agent_preemptive_generation: bool = Field(default=False, env="AGENT_PREEMPTIVE_GENERATION")
    agent_allow_interruptions: bool = Field(default=True, env="AGENT_ALLOW_INTERRUPTIONS")
    
    # Daily Planning
    default_briefing_time: str = Field(default="08:00", env="DEFAULT_BRIEFING_TIME")
    max_daily_tasks: int = Field(default=20, env="MAX_DAILY_TASKS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
