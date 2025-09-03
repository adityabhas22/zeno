#!/usr/bin/env python3
"""
Migration Script: Encrypt Existing Integration Data

This script migrates existing plain-text integration data to encrypted storage.
Run this script once after deploying the encryption changes.

Requirements:
- ZENO_ENCRYPTION_PASSWORD environment variable must be set
- Database must be accessible

Usage:
    export ZENO_ENCRYPTION_PASSWORD="your-secure-password"
    python scripts/migrate_integration_encryption.py
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.storage import session_scope, Integration
from core.storage.encryption import get_encryption_service
from sqlalchemy import text
import json


def migrate_integration_data():
    """Migrate existing integration data to encrypted storage."""

    print("🔐 Starting integration data encryption migration...")

    # Initialize encryption service to ensure master key exists
    try:
        encryption_service = get_encryption_service()
        print("✅ Encryption service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize encryption service: {e}")
        print("Make sure ZENO_ENCRYPTION_PASSWORD environment variable is set")
        return False

    migrated_count = 0
    error_count = 0

    try:
        with session_scope() as db:
            # Get all integrations - we'll check for data in the migration loop
            integrations = db.query(Integration).all()

            print(f"📊 Found {len(integrations)} integrations to migrate")

            for integration in integrations:
                try:
                    print(f"🔄 Checking integration {integration.id} ({integration.integration_type})")

                    # Check if data needs migration by looking at raw database columns
                    # Use raw SQL to check the old columns directly
                    result = db.execute(
                        text("""
                        SELECT auth_tokens, config_data, encrypted_auth_tokens, encrypted_config_data
                        FROM integrations
                        WHERE id = :integration_id
                        """),
                        {"integration_id": integration.id}
                    ).fetchone()

                    if result:
                        old_auth_tokens, old_config_data, encrypted_auth_tokens, encrypted_config_data = result

                        # Check if we have data to migrate
                        has_old_auth = old_auth_tokens is not None
                        has_old_config = old_config_data is not None
                        has_encrypted_auth = encrypted_auth_tokens is not None
                        has_encrypted_config = encrypted_config_data is not None

                        if has_old_auth and not has_encrypted_auth:
                            # Encrypt auth tokens
                            try:
                                encrypted_auth = encryption_service.encrypt_data(old_auth_tokens)
                                db.execute(
                                    text("""
                                    UPDATE integrations
                                    SET encrypted_auth_tokens = :encrypted_auth, auth_tokens = NULL
                                    WHERE id = :integration_id
                                    """),
                                    {"encrypted_auth": encrypted_auth, "integration_id": integration.id}
                                )
                                print(f"✅ Encrypted auth tokens for integration {integration.id}")
                            except Exception as e:
                                print(f"❌ Failed to encrypt auth tokens for integration {integration.id}: {e}")
                                error_count += 1
                                continue

                        if has_old_config and not has_encrypted_config:
                            # Encrypt config data
                            try:
                                encrypted_config = encryption_service.encrypt_data(old_config_data)
                                db.execute(
                                    text("""
                                    UPDATE integrations
                                    SET encrypted_config_data = :encrypted_config, config_data = NULL
                                    WHERE id = :integration_id
                                    """),
                                    {"encrypted_config": encrypted_config, "integration_id": integration.id}
                                )
                                print(f"✅ Encrypted config data for integration {integration.id}")
                            except Exception as e:
                                print(f"❌ Failed to encrypt config data for integration {integration.id}: {e}")
                                error_count += 1
                                continue

                        if (has_old_auth and not has_encrypted_auth) or (has_old_config and not has_encrypted_config):
                            migrated_count += 1
                        elif has_encrypted_auth or has_encrypted_config:
                            print(f"⏭️  Integration {integration.id} already encrypted")
                        else:
                            print(f"⏭️  Integration {integration.id} has no data to migrate")
                    else:
                        print(f"⚠️  Could not find integration {integration.id} in database")

                except Exception as e:
                    error_count += 1
                    print(f"❌ Failed to migrate integration {integration.id}: {e}")
                    continue

            db.commit()
            print(f"🎉 Migration completed!")
            print(f"✅ Successfully migrated: {migrated_count} integrations")
            print(f"❌ Errors: {error_count} integrations")

            return error_count == 0

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def verify_migration():
    """Verify that the migration was successful by testing encryption/decryption."""

    print("\n🔍 Verifying migration...")

    try:
        from core.storage.encryption import get_encryption_service
        service = get_encryption_service()

        with session_scope() as db:
            # Get a few integrations with encrypted data to test
            result = db.execute(
                text("""
                SELECT id, encrypted_auth_tokens, encrypted_config_data
                FROM integrations
                WHERE encrypted_auth_tokens IS NOT NULL OR encrypted_config_data IS NOT NULL
                LIMIT 3
                """)
            ).fetchall()

            if not result:
                print("⚠️  No encrypted integrations found to verify")
                return True

            success_count = 0

            for row in result:
                integration_id, encrypted_auth, encrypted_config = row

                try:
                    # Test auth_tokens decryption
                    if encrypted_auth:
                        decrypted_auth = service.decrypt_data(encrypted_auth)
                        if decrypted_auth and isinstance(decrypted_auth, dict):
                            print(f"✅ Auth tokens decrypted successfully for {integration_id}")
                            success_count += 1
                        else:
                            print(f"❌ Auth tokens decryption failed for {integration_id}")

                    # Test config_data decryption
                    if encrypted_config:
                        decrypted_config = service.decrypt_data(encrypted_config)
                        if decrypted_config and isinstance(decrypted_config, dict):
                            print(f"✅ Config data decrypted successfully for {integration_id}")
                            success_count += 1
                        else:
                            print(f"❌ Config data decryption failed for {integration_id}")

                except Exception as e:
                    print(f"❌ Verification failed for integration {integration_id}: {e}")

            print(f"🔍 Verification: {success_count} successful decryptions")
            return success_count > 0

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def main():
    """Main migration function."""

    print("🚀 Zeno Integration Data Encryption Migration")
    print("=" * 50)

    # Check environment
    if not os.getenv("ZENO_ENCRYPTION_PASSWORD"):
        print("❌ ZENO_ENCRYPTION_PASSWORD environment variable not set")
        print("Please set it before running this migration:")
        print("export ZENO_ENCRYPTION_PASSWORD='your-secure-password'")
        sys.exit(1)

    # Run migration
    migration_success = migrate_integration_data()

    if migration_success:
        # Verify migration
        verification_success = verify_migration()

        if verification_success:
            print("\n🎉 Migration completed successfully!")
            print("\n📝 Next steps:")
            print("1. Update your deployment to use the new encryption system")
            print("2. Consider rotating your encryption key periodically")
            print("3. Monitor for any integration issues")
        else:
            print("\n⚠️  Migration completed but verification failed")
            print("Check the logs above for details")
            sys.exit(1)
    else:
        print("\n❌ Migration failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
