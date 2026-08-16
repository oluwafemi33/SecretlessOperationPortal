from fastapi.testclient import TestClient

from app.keyvault_service import SecretMetadata
from app.main import app, get_service


class FakeVault:
    configured = True
    vault_url = "https://kv-test.vault.azure.net/"
    allowed_names = ("DemoApiKey",)

    async def inspect(self, name):
        return SecretMetadata(name, True, "12345678…", "api-key", None, None, None, 32)


app.dependency_overrides[get_service] = lambda: FakeVault()
client = TestClient(app)


def test_live_health():
    assert client.get("/health/live").status_code == 200


def test_keyvault_health():
    response = client.get("/health/keyvault")
    assert response.status_code == 200
    assert response.json()["identity"] == "authorized"


def test_page_never_returns_secret_value():
    response = client.post("/inspect", data={"secret_name": "DemoApiKey"})
    assert response.status_code == 200
    assert "No secret value was sent" in response.text
