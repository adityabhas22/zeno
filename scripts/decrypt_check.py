#!/usr/bin/env python3
"""
Decrypt and Display Integration Data

This script fetches encrypted integration data from the database and decrypts it
to verify that the encryption system is working correctly.

Requirements:
- ZENO_ENCRYPTION_PASSWORD environment variable must be set
- Database must be accessible
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.storage import session_scope
from core.storage.encryption import get_encryption_service
from sqlalchemy import text


def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Mask sensitive data for safe display."""
    masked = {}

    for key, value in data.items():
        if key in ['token', 'refresh_token', 'client_secret']:
            if isinstance(value, str) and len(value) > 10:
                masked[key] = value[:10] + "...[MASKED]"
            else:
                masked[key] = "[MASKED]"
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_data(value)
        else:
            masked[key] = value

    return masked


def decrypt_and_display():
    """Decrypt and display integration data from database."""

    print("🔓 Decrypting Integration Data from Database")
    print("=" * 50)

    # Check environment
    if not os.getenv("ZENO_ENCRYPTION_PASSWORD"):
        print("❌ ZENO_ENCRYPTION_PASSWORD environment variable not set")
        print("Please set it before running:")
        print("export ZENO_ENCRYPTION_PASSWORD='your-password'")
        sys.exit(1)

    try:
        # Initialize encryption service
        encryption_service = get_encryption_service()
        print("✅ Encryption service initialized")

        with session_scope() as db:
            # Fetch all integrations with encrypted data
            result = db.execute(
                text("""
                SELECT id, integration_type, provider, encrypted_auth_tokens, encrypted_config_data
                FROM integrations
                WHERE encrypted_auth_tokens IS NOT NULL OR encrypted_config_data IS NOT NULL
                """)
            ).fetchall()

            if not result:
                print("⚠️  No encrypted integrations found in database")
                return

            print(f"📊 Found {len(result)} encrypted integrations")
            print()

            for row in result:
                integration_id, integration_type, provider, encrypted_auth, encrypted_config = row

                print(f"🔑 Integration: {integration_id}")
                print(f"   Type: {integration_type}")
                print(f"   Provider: {provider}")
                print()

                # Decrypt auth tokens
                if encrypted_auth:
                    try:
                        decrypted_auth = encryption_service.decrypt_data(encrypted_auth)
                        masked_auth = mask_sensitive_data(decrypted_auth)

                        print("   📝 Auth Tokens (decrypted):")
                        for key, value in masked_auth.items():
                            print(f"      {key}: {value}")
                        print("   ✅ Auth tokens decrypted successfully")
                    except Exception as e:
                        print(f"   ❌ Failed to decrypt auth tokens: {e}")
                else:
                    print("   📝 No auth tokens found")

                print()

                # Decrypt config data
                if encrypted_config:
                    try:
                        decrypted_config = encryption_service.decrypt_data(encrypted_config)
                        masked_config = mask_sensitive_data(decrypted_config)

                        print("   ⚙️  Config Data (decrypted):")
                        for key, value in masked_config.items():
                            print(f"      {key}: {value}")
                        print("   ✅ Config data decrypted successfully")
                    except Exception as e:
                        print(f"   ❌ Failed to decrypt config data: {e}")
                else:
                    print("   ⚙️  No config data found")

                print("-" * 50)
                print()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def show_raw_encrypted_data():
    """Show the raw encrypted data in the database."""

    print("🔐 Raw Encrypted Data in Database")
    print("=" * 50)

    try:
        with session_scope() as db:
            result = db.execute(
                text("""
                SELECT id, integration_type, encrypted_auth_tokens, encrypted_config_data
                FROM integrations
                WHERE encrypted_auth_tokens IS NOT NULL OR encrypted_config_data IS NOT NULL
                """)
            ).fetchall()

            if not result:
                print("⚠️  No encrypted data found")
                return

            for row in result:
                integration_id, integration_type, encrypted_auth, encrypted_config = row

                print(f"🔑 Integration: {integration_id} ({integration_type})")

                if encrypted_auth:
                    print(f"   Encrypted Auth Tokens: {len(encrypted_auth)} chars")
                    print(f"   Preview: {encrypted_auth[:50]}...")

                if encrypted_config:
                    print(f"   Encrypted Config Data: {len(encrypted_config)} chars")
                    print(f"   Preview: {encrypted_config[:50]}...")

                print()

    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main function."""

    if len(sys.argv) > 1 and sys.argv[1] == "--raw":
        show_raw_encrypted_data()
    else:
        decrypt_and_display()


if __name__ == "__main__":
    main()
