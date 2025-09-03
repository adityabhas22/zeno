#!/usr/bin/env python3
"""
Test Script for Encryption Service

Tests the encryption/decryption functionality for integration data.
Run this script to verify that the encryption system is working correctly.

Requirements:
- ZENO_ENCRYPTION_PASSWORD environment variable must be set
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.storage.encryption import get_encryption_service


def test_encryption_service():
    """Test the encryption service functionality."""

    print("🧪 Testing Encryption Service")
    print("=" * 40)

    # Check environment
    if not os.getenv("ZENO_ENCRYPTION_PASSWORD"):
        print("❌ ZENO_ENCRYPTION_PASSWORD environment variable not set")
        print("Please set it before running tests:")
        print("export ZENO_ENCRYPTION_PASSWORD='your-secure-password'")
        sys.exit(1)

    try:
        # Initialize encryption service
        encryption_service = get_encryption_service()
        print("✅ Encryption service initialized")

        # Test data
        test_data = {
            "token": "ya29.test_token_here",
            "refresh_token": "1//test_refresh_token",
            "client_id": "test_client_id.apps.googleusercontent.com",
            "client_secret": "test_client_secret",
            "scopes": ["https://www.googleapis.com/auth/calendar"],
            "email": "test@example.com"
        }

        print("\n📝 Original data:")
        print(f"  Token: {test_data['token'][:20]}...")
        print(f"  Email: {test_data['email']}")

        # Test encryption
        encrypted = encryption_service.encrypt_data(test_data)
        print(f"\n🔐 Encrypted data length: {len(encrypted)} characters")

        # Test decryption
        decrypted = encryption_service.decrypt_data(encrypted)
        print("\n🔓 Decrypted data:")
        print(f"  Token: {decrypted['token'][:20]}...")
        print(f"  Email: {decrypted['email']}")

        # Verify data integrity
        if decrypted == test_data:
            print("\n✅ Encryption/decryption test PASSED")
            print("   Data integrity verified")
            return True
        else:
            print("\n❌ Encryption/decryption test FAILED")
            print("   Data integrity check failed")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


def test_integration_model():
    """Test the Integration model encryption properties."""

    print("\n🧪 Testing Integration Model Properties")
    print("=" * 40)

    try:
        from core.storage.models import Integration

        # Create a mock integration object
        integration = Integration(
            user_id="test_user",
            integration_type="google_workspace",
            provider="google"
        )

        # Test setting auth tokens
        test_auth_data = {
            "token": "ya29.test_token",
            "refresh_token": "1//test_refresh",
            "email": "test@example.com"
        }

        print("📝 Setting auth tokens...")
        integration.auth_tokens = test_auth_data

        # Check that encrypted field is set
        encrypted_auth = getattr(integration, 'encrypted_auth_tokens', None)
        if encrypted_auth:
            print(f"✅ Auth tokens encrypted (length: {len(encrypted_auth)})")
        else:
            print("❌ Auth tokens not encrypted")
            return False

        # Test getting auth tokens
        retrieved_auth = integration.auth_tokens
        if retrieved_auth == test_auth_data:
            print("✅ Auth tokens decrypted correctly")
        else:
            print("❌ Auth tokens decryption failed")
            return False

        # Test config data
        test_config = {"api_version": "v3", "timeout": 30}
        integration.config_data = test_config

        retrieved_config = integration.config_data
        if retrieved_config == test_config:
            print("✅ Config data encryption/decryption works")
        else:
            print("❌ Config data encryption/decryption failed")
            return False

        return True

    except Exception as e:
        print(f"❌ Integration model test failed: {e}")
        return False


def main():
    """Run all tests."""

    print("🚀 Zeno Encryption System Tests")
    print("=" * 50)

    # Test encryption service
    encryption_test = test_encryption_service()

    # Test integration model
    model_test = test_integration_model()

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"  Encryption Service: {'✅ PASSED' if encryption_test else '❌ FAILED'}")
    print(f"  Integration Model:  {'✅ PASSED' if model_test else '❌ FAILED'}")

    if encryption_test and model_test:
        print("\n🎉 All tests PASSED! Encryption system is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests FAILED. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
