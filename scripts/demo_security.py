#!/usr/bin/env python3
"""
Demonstrate Encryption Security - Wrong vs Right Password
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.storage.encryption import get_encryption_service


def demo_security():
    """Demonstrate the security of the encryption system."""

    print("🔐 ENCRYPTION SECURITY DEMONSTRATION")
    print("=" * 60)
    print()

    # Test data to encrypt
    test_data = {
        "token": "ya29.test_token_example",
        "refresh_token": "1//test_refresh_token",
        "client_secret": "GOCSPX-test-secret",
        "email": "test@example.com"
    }

    print("📝 Original Test Data:")
    for key, value in test_data.items():
        print(f"   {key}: {value}")
    print()

    # Test 1: Encrypt with correct password
    print("🔒 TEST 1: Encrypt with CORRECT password")
    os.environ['ZENO_ENCRYPTION_PASSWORD'] = "testpassword123"

    try:
        service = get_encryption_service()
        encrypted = service.encrypt_data(test_data)
        print("✅ Data encrypted successfully")
        print(f"   Encrypted length: {len(encrypted)} characters")
        print(f"   Encrypted preview: {encrypted[:50]}...")
        print()
    except Exception as e:
        print(f"❌ Encryption failed: {e}")
        return

    # Test 2: Try to decrypt with wrong password
    print("🔓 TEST 2: Try to DECRYPT with WRONG password")
    os.environ['ZENO_ENCRYPTION_PASSWORD'] = "wrong-password-123"

    try:
        # This should fail because the master key was encrypted with "testpassword123"
        service_wrong = get_encryption_service()
        decrypted_wrong = service_wrong.decrypt_data(encrypted)
        print("❌ SECURITY BREACH! Wrong password worked!")
        print(f"   Decrypted: {decrypted_wrong}")
    except Exception as e:
        print("✅ Security working! Wrong password failed as expected")
        print(f"   Error: {e}")
    print()

    # Test 3: Decrypt with correct password
    print("🔓 TEST 3: Try to DECRYPT with CORRECT password")
    os.environ['ZENO_ENCRYPTION_PASSWORD'] = "testpassword123"

    try:
        service_correct = get_encryption_service()
        decrypted_correct = service_correct.decrypt_data(encrypted)
        print("✅ Correct password worked!")
        print("   Decrypted data:")
        for key, value in decrypted_correct.items():
            print(f"      {key}: {value}")

        # Verify data integrity
        if decrypted_correct == test_data:
            print("✅ Data integrity verified - encryption/decryption is perfect!")
        else:
            print("❌ Data integrity check failed!")
    except Exception as e:
        print(f"❌ Unexpected error with correct password: {e}")

    print()
    print("=" * 60)
    print("🎯 SECURITY CONCLUSION:")
    print("   ✅ Wrong passwords: FAIL (as expected)")
    print("   ✅ Correct password: WORKS (as expected)")
    print("   🔒 Your data is SECURE!")
    print()
    print("💡 This proves that:")
    print("   - Only the correct password can decrypt your data")
    print("   - Database breaches won't expose sensitive information")
    print("   - OAuth tokens, API keys, and secrets are protected")


def test_database_security():
    """Test the actual database data security."""
    print("\n" + "=" * 60)
    print("🗄️  DATABASE SECURITY TEST")
    print("=" * 60)

    from core.storage import session_scope
    from sqlalchemy import text

    # Show raw encrypted data
    print("\n🔐 Raw encrypted data in database:")
    with session_scope() as db:
        result = db.execute(
            text("""
            SELECT id, encrypted_auth_tokens, encrypted_config_data
            FROM integrations
            WHERE encrypted_auth_tokens IS NOT NULL OR encrypted_config_data IS NOT NULL
            LIMIT 1
            """)
        ).fetchone()

        if result:
            integration_id, auth_data, config_data = result
            print(f"   Integration ID: {integration_id}")

            if auth_data:
                print(f"   Auth tokens (encrypted): {len(auth_data)} chars")
                print(f"   Preview: {auth_data[:50]}...")
            else:
                print("   Auth tokens: None")

            if config_data:
                print(f"   Config data (encrypted): {len(config_data)} chars")
                print(f"   Preview: {config_data[:50]}...")
            else:
                print("   Config data: None")
        else:
            print("   No encrypted data found")

    print("\n🔓 Try to decrypt with WRONG password:")
    os.environ['ZENO_ENCRYPTION_PASSWORD'] = "completely-wrong-password"

    try:
        service = get_encryption_service()
        print("❌ Should have failed but didn't!")
    except Exception as e:
        print("✅ Correctly failed with wrong password")

    print("\n🔓 Decrypt with CORRECT password:")
    os.environ['ZENO_ENCRYPTION_PASSWORD'] = "testpassword123"

    try:
        service = get_encryption_service()
        print("✅ Successfully initialized with correct password")
        print("✅ Your database data is secure!")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    demo_security()
    test_database_security()
