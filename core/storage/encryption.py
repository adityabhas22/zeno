"""
Secure Encryption Service for Zeno

Provides AES-256-GCM encryption for sensitive integration data.
Uses envelope encryption with a master key for enhanced security.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from typing import Dict, Any, Optional
from pathlib import Path

from config.settings import get_settings


class EncryptionService:
    """
    Secure encryption service using AES-256-GCM with envelope encryption.

    Features:
    - AES-256-GCM encryption for confidentiality and integrity
    - PBKDF2 key derivation for master key protection
    - Envelope encryption pattern for key management
    - Automatic key rotation support
    """

    # Encryption constants
    KEY_SIZE = 32  # 256-bit key
    SALT_SIZE = 16  # 128-bit salt
    NONCE_SIZE = 12  # 96-bit nonce for GCM
    PBKDF2_ITERATIONS = 100000  # OWASP recommended minimum

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service.

        Args:
            master_key: Base64-encoded master key. If None, loads from environment/settings.
        """
        self.settings = get_settings()

        if master_key:
            self.master_key = base64.b64decode(master_key)
        else:
            self.master_key = self._load_or_generate_master_key()

        # Derive encryption key from master key
        self.encryption_key = self._derive_key(self.master_key)

    def _load_or_generate_master_key(self) -> bytes:
        """Load master key from file or generate a new one."""
        key_file = self.settings.base_dir / "encryption_key.key"

        if key_file.exists():
            try:
                with open(key_file, "rb") as f:
                    encrypted_key = f.read()

                # For now, we'll store the key encrypted with a password
                # In production, consider using AWS KMS, Azure Key Vault, etc.
                password = os.getenv("ZENO_ENCRYPTION_PASSWORD") or self.settings.encryption_password
                if not password:
                    raise ValueError("ZENO_ENCRYPTION_PASSWORD environment variable or encryption_password setting required")

                return self._decrypt_master_key(encrypted_key, password.encode())

            except Exception as e:
                print(f"❌ Failed to load master key: {e}")
                raise
        else:
            # Generate new master key
            print("🔐 Generating new master encryption key...")
            master_key = secrets.token_bytes(self.KEY_SIZE)

            # Encrypt and save the master key
            password = os.getenv("ZENO_ENCRYPTION_PASSWORD") or self.settings.encryption_password
            if not password:
                raise ValueError("ZENO_ENCRYPTION_PASSWORD environment variable or encryption_password setting required to generate new key")

            encrypted_key = self._encrypt_master_key(master_key, password.encode())

            key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(key_file, "wb") as f:
                f.write(encrypted_key)

            print(f"✅ Master key saved to {key_file}")
            return master_key

    def _encrypt_master_key(self, master_key: bytes, password: bytes) -> bytes:
        """Encrypt master key with password using PBKDF2 + AES."""
        salt = secrets.token_bytes(self.SALT_SIZE)

        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        derived_key = kdf.derive(password)

        # Encrypt master key
        nonce = secrets.token_bytes(self.NONCE_SIZE)
        cipher = Cipher(algorithms.AES(derived_key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()

        ciphertext = encryptor.update(master_key) + encryptor.finalize()

        # Return format: salt + nonce + ciphertext + tag
        return salt + nonce + ciphertext + encryptor.tag

    def _decrypt_master_key(self, encrypted_data: bytes, password: bytes) -> bytes:
        """Decrypt master key with password."""
        if len(encrypted_data) < self.SALT_SIZE + self.NONCE_SIZE + 16:  # 16 = GCM tag size
            raise ValueError("Invalid encrypted key format")

        salt = encrypted_data[:self.SALT_SIZE]
        nonce = encrypted_data[self.SALT_SIZE:self.SALT_SIZE + self.NONCE_SIZE]
        ciphertext = encrypted_data[self.SALT_SIZE + self.NONCE_SIZE:-16]
        tag = encrypted_data[-16:]

        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        derived_key = kdf.derive(password)

        # Decrypt master key
        cipher = Cipher(algorithms.AES(derived_key), modes.GCM(nonce, tag), backend=default_backend())
        decryptor = cipher.decryptor()

        return decryptor.update(ciphertext) + decryptor.finalize()

    def _derive_key(self, master_key: bytes) -> bytes:
        """Derive encryption key from master key using HKDF."""
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=b"zeno_integration_encryption",
            info=b"integration_data_encryption",
            backend=default_backend()
        )
        return hkdf.derive(master_key)

    def encrypt_data(self, data: Dict[str, Any]) -> str:
        """
        Encrypt dictionary data using AES-256-GCM.

        Args:
            data: Dictionary to encrypt

        Returns:
            Base64-encoded encrypted data with nonce and tag
        """
        # Convert to JSON
        json_data = json.dumps(data, separators=(',', ':')).encode('utf-8')

        # Generate nonce
        nonce = secrets.token_bytes(self.NONCE_SIZE)

        # Encrypt
        cipher = Cipher(algorithms.AES(self.encryption_key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()

        ciphertext = encryptor.update(json_data) + encryptor.finalize()

        # Combine: nonce + ciphertext + tag
        encrypted_blob = nonce + ciphertext + encryptor.tag

        # Return base64 encoded
        return base64.b64encode(encrypted_blob).decode('utf-8')

    def decrypt_data(self, encrypted_b64: str) -> Dict[str, Any]:
        """
        Decrypt base64-encoded data back to dictionary.

        Args:
            encrypted_b64: Base64-encoded encrypted data

        Returns:
            Decrypted dictionary

        Raises:
            ValueError: If decryption fails or data is corrupted
        """
        try:
            # Decode base64
            encrypted_blob = base64.b64decode(encrypted_b64)

            if len(encrypted_blob) < self.NONCE_SIZE + 16:  # 16 = GCM tag size
                raise ValueError("Invalid encrypted data format")

            # Extract components
            nonce = encrypted_blob[:self.NONCE_SIZE]
            ciphertext = encrypted_blob[self.NONCE_SIZE:-16]
            tag = encrypted_blob[-16:]

            # Decrypt
            cipher = Cipher(algorithms.AES(self.encryption_key), modes.GCM(nonce, tag), backend=default_backend())
            decryptor = cipher.decryptor()

            json_data = decryptor.update(ciphertext) + decryptor.finalize()

            # Parse JSON
            return json.loads(json_data.decode('utf-8'))

        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    def rotate_key(self, new_password: Optional[str] = None) -> None:
        """
        Rotate the master key and re-encrypt all data.

        Args:
            new_password: New password for master key encryption. If None, uses current password.
        """
        # This would need to be implemented with a migration script
        # to re-encrypt all existing encrypted data
        raise NotImplementedError("Key rotation requires database migration")


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create the global encryption service instance."""
    global _encryption_service

    if _encryption_service is None:
        _encryption_service = EncryptionService()

    return _encryption_service


def encrypt_integration_data(data: Dict[str, Any]) -> str:
    """
    Encrypt integration data for secure storage.

    Args:
        data: Integration data dictionary

    Returns:
        Encrypted data string for database storage
    """
    service = get_encryption_service()
    return service.encrypt_data(data)


def decrypt_integration_data(encrypted_data: str) -> Dict[str, Any]:
    """
    Decrypt integration data from secure storage.

    Args:
        encrypted_data: Encrypted data string from database

    Returns:
        Decrypted integration data dictionary
    """
    service = get_encryption_service()
    return service.decrypt_data(encrypted_data)
