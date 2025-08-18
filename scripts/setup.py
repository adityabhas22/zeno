#!/usr/bin/env python3
"""
Zeno Setup Script

Initialize the Zeno project with necessary directories, configurations, and dependencies.
"""

import os
import sys
from pathlib import Path
import shutil
import subprocess


def create_directories():
    """Create necessary directories for Zeno."""
    directories = [
        "credentials",
        "logs",
        "logs/transcripts",
        "data",
        "data/tasks",
        "data/briefings",
        "deployment/ssl",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")


def copy_legacy_credentials():
    """Copy credentials from legacy directory if they exist."""
    legacy_credentials = Path("legacy/voice-starter/credentials")
    new_credentials = Path("credentials")
    
    if legacy_credentials.exists():
        for file in legacy_credentials.glob("*"):
            if file.is_file():
                shutil.copy2(file, new_credentials)
                print(f"✅ Copied credential file: {file.name}")
    else:
        print("ℹ️  No legacy credentials found to copy")


def create_env_file():
    """Create .env file from template if it doesn't exist."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        shutil.copy2(env_example, env_file)
        print("✅ Created .env file from template")
        print("⚠️  Please edit .env file with your actual configuration values")
    elif env_file.exists():
        print("ℹ️  .env file already exists")
    else:
        print("❌ .env.example not found - cannot create .env file")


def install_dependencies():
    """Install Python dependencies."""
    try:
        print("📦 Installing Python dependencies...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True, capture_output=True, text=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")


def setup_google_oauth():
    """Setup Google OAuth if credentials exist."""
    client_secrets = Path("credentials/client_secret.json")
    
    if client_secrets.exists():
        print("🔐 Google client_secret.json found")
        print("ℹ️  Run 'python scripts/init_oauth.py' to complete Google OAuth setup")
    else:
        print("⚠️  Google client_secret.json not found")
        print("   Please add your Google OAuth credentials to credentials/client_secret.json")
        print("   Visit: https://console.cloud.google.com/apis/credentials")


def check_environment():
    """Check if all required environment variables are set."""
    required_vars = [
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET", 
        "LIVEKIT_URL",
        "JWT_SECRET_KEY",
        "DATABASE_URL"
    ]
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        return
    
    missing_vars = []
    with open(env_file) as f:
        env_content = f.read()
        for var in required_vars:
            if f"{var}=" not in env_content or f"{var}=your_" in env_content:
                missing_vars.append(var)
    
    if missing_vars:
        print("⚠️  The following environment variables need to be configured:")
        for var in missing_vars:
            print(f"   - {var}")
        print("   Please edit .env file with your actual values")
    else:
        print("✅ All required environment variables are configured")


def create_git_ignore():
    """Create or update .gitignore file."""
    gitignore_content = """# Zeno Project .gitignore

# Environment variables
.env
.env.local
.env.production

# Credentials and secrets
credentials/
*.key
*.pem
*.p8

# Logs and data
logs/
data/
*.log

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Database
*.db
*.sqlite
*.sqlite3

# Docker
.dockerignore

# Temporary files
*.tmp
*.temp
.cache/

# LiveKit
*.room
"""
    
    gitignore_path = Path(".gitignore")
    with open(gitignore_path, "w") as f:
        f.write(gitignore_content)
    print("✅ Created/updated .gitignore file")


def main():
    """Main setup function."""
    print("🤖 Zeno Setup Script")
    print("=" * 40)
    
    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print(f"Setting up Zeno in: {project_root}")
    print()
    
    # Run setup steps
    create_directories()
    copy_legacy_credentials()
    create_env_file()
    create_git_ignore()
    
    # Install dependencies
    install_dependencies()
    
    # Setup checks
    setup_google_oauth()
    check_environment()
    
    print()
    print("🎉 Zeno setup completed!")
    print()
    print("Next steps:")
    print("1. Edit .env file with your configuration")
    print("2. Add Google OAuth credentials to credentials/client_secret.json")
    print("3. Run 'python scripts/init_oauth.py' to setup Google authentication")
    print("4. Start the API: 'uvicorn api.main:app --reload'")
    print("5. Start the agent: 'python -m agents.core.zeno_agent'")
    print()
    print("For more information, see README.md")


if __name__ == "__main__":
    main()
