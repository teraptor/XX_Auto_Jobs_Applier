"""
Credentials Manager
Handles encryption/decryption of HH.ru credentials
"""
import os
import base64
from typing import Tuple
from cryptography.fernet import Fernet

from src.repositories import UserRepository
from src.storage.tenant_context import TenantContext


class CredentialsManager:
    """
    Manages HH.ru credentials with encryption
    Replaces: Reading from secrets.yaml
    """

    def __init__(self, user_repo: UserRepository, context: TenantContext):
        """
        Initialize credentials manager

        Args:
            user_repo: User repository
            context: Tenant context
        """
        self.user_repo = user_repo
        self.context = context
        self._encryption_key = self._get_encryption_key()

    @staticmethod
    def _get_encryption_key() -> bytes:
        """Get encryption key from environment"""
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError(
                "ENCRYPTION_KEY environment variable not set. "
                "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        return key.encode()

    def encrypt_password(self, password: str) -> str:
        """
        Encrypt password using Fernet

        Args:
            password: Plain text password

        Returns:
            Base64 encoded encrypted password
        """
        fernet = Fernet(self._encryption_key)
        encrypted = fernet.encrypt(password.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt password using Fernet

        Args:
            encrypted_password: Base64 encoded encrypted password

        Returns:
            Plain text password
        """
        fernet = Fernet(self._encryption_key)
        encrypted_bytes = base64.b64decode(encrypted_password.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()

    async def get_hh_credentials(self) -> Tuple[str, str]:
        """
        Get HH.ru credentials for current user
        Replaces: load_yaml_file(Path("secrets.yaml"))

        Returns:
            Tuple of (login, password)

        Raises:
            ValueError: If user not found or credentials missing
        """
        user = await self.user_repo.get_by_id(
            self.context.user_id,
            self.context.tenant_id
        )

        if not user:
            raise ValueError(f"User not found: {self.context.user_id}")

        if not user['hh_login'] or not user['hh_password_encrypted']:
            raise ValueError(f"HH.ru credentials not set for user: {self.context.user_id}")

        # Decrypt password
        password = self.decrypt_password(user['hh_password_encrypted'])

        return user['hh_login'], password

    async def update_hh_credentials(self, login: str, password: str) -> None:
        """
        Update HH.ru credentials for current user

        Args:
            login: HH.ru login
            password: HH.ru password (will be encrypted)
        """
        encrypted_password = self.encrypt_password(password)

        await self.user_repo.update_credentials(
            user_id=self.context.user_id,
            tenant_id=self.context.tenant_id,
            hh_login=login,
            hh_password_encrypted=encrypted_password
        )
