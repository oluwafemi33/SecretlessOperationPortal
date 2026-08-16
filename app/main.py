import logging
from pathlib import Path

from azure.core.exceptions import ClientAuthenticationError, HttpResponseError, ResourceNotFoundError
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.keyvault_service import KeyVaultService

BASE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger("secretless-portal")
app = FastAPI(title="Secretless Operations Portal", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
service = KeyVaultService()


def get_service() -> KeyVaultService:
    return service


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, vault: KeyVaultService = Depends(get_service)):
    return templates.TemplateResponse(request, "index.html", {
        "configured": vault.configured,
        "vault_host": vault.vault_url.replace("https://", "").rstrip("/") if vault.configured else "Not configured",
        "secret_names": vault.allowed_names,
        "result": None,
        "error": None,
    })


@app.post("/inspect", response_class=HTMLResponse)
async def inspect_secret(request: Request, secret_name: str = Form(...), vault: KeyVaultService = Depends(get_service)):
    result, error = None, None
    try:
        result = (await vault.inspect(secret_name)).to_dict()
    except ValueError:
        error = "That secret is not on the application allow-list."
    except ResourceNotFoundError:
        error = "The secret was not found in this vault."
    except ClientAuthenticationError:
        error = "Azure could not authenticate this runtime. Sign in locally or enable the App Service managed identity."
    except HttpResponseError as exc:
        logger.warning("Key Vault request failed with status %s", exc.status_code)
        error = "Key Vault denied the request. Verify the identity, RBAC role, vault URL, and network access."
    except RuntimeError as exc:
        error = str(exc)
    return templates.TemplateResponse(request, "index.html", {
        "configured": vault.configured,
        "vault_host": vault.vault_url.replace("https://", "").rstrip("/") if vault.configured else "Not configured",
        "secret_names": vault.allowed_names,
        "result": result,
        "error": error,
    })


@app.get("/health/live")
async def live():
    return {"status": "healthy", "service": "secretless-operations-portal"}


@app.get("/health/keyvault")
async def keyvault_health(vault: KeyVaultService = Depends(get_service)):
    if not vault.configured:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "keyVault": "not configured"})
    try:
        metadata = await vault.inspect(vault.allowed_names[0])
        return {"status": "healthy", "keyVault": "connected", "identity": "authorized", "secret": metadata.name}
    except Exception as exc:
        logger.warning("Key Vault health check failed: %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"status": "unhealthy", "keyVault": "connection or authorization failed"})
