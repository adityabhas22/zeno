#!/usr/bin/env python3
"""
Test Agent Data Decryption - End-to-End Test

This script tests the complete flow:
1. Store encrypted integration data
2. Agent retrieves and decrypts the data (just like in production)
3. Verify that decrypted data is usable
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.storage import session_scope
from core.storage.models import Integration
from core.integrations.google.user_oauth import get_user_credentials
from google.oauth2.credentials import Credentials


def test_agent_decryption():
    """Test that agent properly decrypts data when retrieving from database."""
    print("🧪 Testing Agent Data Decryption - End-to-End")
    print("=" * 60)

    # Test data (simulating real OAuth tokens)
    test_auth_tokens = {
        "token": "ya29.test_token_example",
        "refresh_token": "1//test_refresh_token",
        "client_id": "test_client_id.apps.googleusercontent.com",
        "client_secret": "test_client_secret",
        "scopes": ["https://www.googleapis.com/auth/calendar"],
        "email": "test@example.com"
    }

    # Test user ID
    test_user_id = "test_agent_user_123"

    try:
        with session_scope() as db:
            print("📝 Creating test integration with encrypted data...")

            # Create integration (this will encrypt the data automatically)
            integration = Integration(
                user_id=test_user_id,
                integration_type="google_workspace",
                provider="google",
                auth_tokens=test_auth_tokens,
                is_active=True
            )

            db.add(integration)
            db.commit()
            db.refresh(integration)

            print(f"✅ Integration created with ID: {integration.id}")

            # Check raw database storage
            from sqlalchemy import text
            result = db.execute(text('SELECT encrypted_auth_tokens FROM integrations WHERE id = :id'), {'id': integration.id}).fetchone()
            if result:
                encrypted_data = result[0]
                print(f"🔐 Raw encrypted data in database: {len(encrypted_data)} chars")
                print(f"   Preview: {encrypted_data[:50]}...")

        print("\\n🔓 Testing Agent Data Retrieval (like production)...")

        # Now simulate what the agent does - retrieve credentials using the same function
        scopes = ["https://www.googleapis.com/auth/calendar"]

        try:
            credentials = get_user_credentials(test_user_id, scopes)

            if credentials:
                print("✅ Agent successfully retrieved and decrypted credentials!")
                print("   Token:", credentials.token[:20] + "..." if credentials.token else "None")
                print("   Refresh token:", credentials.refresh_token[:20] + "..." if credentials.refresh_token else "None")
                print("   Client ID:", credentials.client_id[:30] + "..." if credentials.client_id else "None")
                print("   Email:", getattr(credentials, 'id_token', {}).get('email', 'Not available'))

                # Verify data integrity
                if credentials.token == test_auth_tokens["token"]:
                    print("✅ Data integrity verified - decrypted data matches original!")
                else:
                    print("❌ Data integrity check failed!")

            else:
                print("❌ Agent failed to retrieve credentials")

        except Exception as e:
            print(f"❌ Agent credential retrieval failed: {e}")

        # Clean up
        print("\\n🧹 Cleaning up test data...")
        with session_scope() as db:
            db.delete(integration)
            db.commit()
            print("✅ Test integration deleted")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


def demonstrate_property_getter():
    """Demonstrate that the property getter automatically decrypts."""
    print("\\n" + "=" * 60)
    print("🔍 Demonstrating Property Getter Auto-Decryption")
    print("=" * 60)

    test_auth_tokens = {
        "token": "ya29.property_test",
        "refresh_token": "1//property_test",
        "email": "property@example.com"
    }

    try:
        with session_scope() as db:
            # Create integration
            integration = Integration(
                user_id="property_test_user",
                integration_type="google_workspace",
                provider="google",
                auth_tokens=test_auth_tokens
            )

            db.add(integration)
            db.commit()
            db.refresh(integration)

            print("📊 Integration object after creation:")
            print(f"   ID: {integration.id}")

            # Access the property - this should auto-decrypt
            print("\\n🔓 Accessing integration.auth_tokens property...")
            retrieved_tokens = integration.auth_tokens

            if retrieved_tokens:
                print("✅ Property getter successfully decrypted data:")
                for key, value in retrieved_tokens.items():
                    print(f"   {key}: {value}")

                # Verify it's the same data
                if retrieved_tokens == test_auth_tokens:
                    print("\\n✅ Perfect! Property getter auto-decrypts and returns original data!")
                else:
                    print("\\n❌ Data mismatch!")
            else:
                print("❌ Property getter returned None")

            # Clean up
            db.delete(integration)
            db.commit()

    except Exception as e:
        print(f"❌ Property getter test failed: {e}")


if __name__ == "__main__":
    test_agent_decryption()
    demonstrate_property_getter()
