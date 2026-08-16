import asyncio
import os
from dataclasses import asdict, dataclass
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


@dataclass(frozen=True)
class SecretMetadata:
    name: str
    enabled: bool
    version_preview: str
    content_type: str
    created_on: str | None
    updated_on: str | None
    expires_on: str | None
    value_length: int

    def to_dict(self) -> dict:
        return asdict(self)


class KeyVaultService:
    def __init__(self) -> None:
        self.vault_url = os.getenv("KEY_VAULT_URL", "").strip()
        configured = os.getenv("ALLOWED_SECRET_NAMES", "DemoApiKey,OperationsBanner,ThirdPartyEndpoint")
        self.allowed_names = tuple(name.strip() for name in configured.split(",") if name.strip())
        self._client: SecretClient | None = None

    @property
    def configured(self) -> bool:
        return self.vault_url.startswith("https://") and ".vault.azure.net" in self.vault_url

    def _get_client(self) -> SecretClient:
        if not self.configured:
            raise RuntimeError("KEY_VAULT_URL is not configured")
        if self._client is None:
            credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
            self._client = SecretClient(vault_url=self.vault_url, credential=credential)
        return self._client

    async def inspect(self, name: str) -> SecretMetadata:
        if name not in self.allowed_names:
            raise ValueError("Secret name is not allow-listed")
        secret = await asyncio.to_thread(self._get_client().get_secret, name)
        props = secret.properties
        return SecretMetadata(
            name=name,
            enabled=props.enabled is not False,
            version_preview=f"{props.version[:8]}…" if props.version else "unknown",
            content_type=props.content_type or "not set",
            created_on=_iso(props.created_on),
            updated_on=_iso(props.updated_on),
            expires_on=_iso(props.expires_on),
            value_length=len(secret.value or ""),
        )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
