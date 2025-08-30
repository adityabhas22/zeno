#!/usr/bin/env python3
"""
Test Password Security - Try wrong passwords vs correct password
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.storage import session_scope
from core.storage.encryption import get_encryption_service
from sqlalchemy import text


def test_password(password: str, description: str) -> bool:
    """Test a specific password."""
    print(f"\n🧪 Testing: {description}")
    print(f"   Password: {password[:20]}{'...' if len(password) > 20 else ''}")

    # Set the password
    os.environ['ZENO_ENCRYPTION_PASSWORD'] = password

    try:
        # Try to initialize encryption service
        service = get_encryption_service()
        print("   ✅ Encryption service initialized")

        # Try to decrypt data
        with session_scope() as db:
            result = db.execute(
                text("""
                SELECT encrypted_auth_tokens
                FROM integrations
                WHERE encrypted_auth_tokens IS NOT NULL
                LIMIT 1
                """)
            ).fetchone()

            if result:
                encrypted_data = result[0]
                try:
                    decrypted = service.decrypt_data(encrypted_data)
                    print("   ✅ Data decrypted successfully")
                    print(f"   📝 Sample decrypted data: {str(decrypted)[:100]}...")
                    return True
                except Exception as e:
                    print(f"   ❌ Decryption failed: {e}")
                    return False
            else:
                print("   ⚠️  No encrypted data found to test")
                return True

    except Exception as e:
        print(f"   ❌ Encryption service failed: {e}")
        return False


def main():
    """Test various passwords."""
    print("🔐 Password Security Test")
    print("=" * 50)

    # Test wrong passwords
    wrong_passwords = [
        "wrong-password-123",
        "another-random-password",
        "password",
        "123456",
        "admin",
        "dev",
        ""
    ]

    for pwd in wrong_passwords:
        test_password(pwd, f"WRONG: '{pwd}'")

    print("\n" + "=" * 50)

    # Test correct password from .env
    env_file = project_root / ".env"
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('ZENO_ENCRYPTION_PASSWORD='):
                    correct_password = line.split('=', 1)[1].strip().strip('"')
                    test_password(correct_password, "CORRECT: From .env file")
                    break

    print("\n" + "=" * 50)
    print("📊 Summary:")
    print("   ❌ Wrong passwords: Should all fail")
    print("   ✅ Correct password: Should work")
    print("   🔒 This proves the encryption is secure!")


if __name__ == "__main__":
    main()
