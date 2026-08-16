# Secretless Operations Portal

A hands-on Azure security project built with Python 3.11, FastAPI, Azure Key Vault, App Service managed identity, and Azure RBAC.

The portal retrieves allow-listed secrets with `DefaultAzureCredential` but never returns secret values to the browser or writes them to logs. It displays only safe metadata such as the version prefix, enabled state, dates, content type, and value length.

## What you learn

- Why managed identity removes application credentials
- How `DefaultAzureCredential` uses `az login` locally and managed identity in Azure
- The difference between Azure management-plane permissions and Key Vault data-plane RBAC
- Why the App Service identity receives **Key Vault Secrets User**, not an administrator role
- How to verify both successful and intentionally denied access
- How to avoid leaking values through pages, health endpoints, logs, or source control

## Architecture

```text
Browser -> FastAPI on App Service
                |
                | DefaultAzureCredential
                v
       System-assigned managed identity
                |
                | Entra ID access token
                v
       Azure Key Vault RBAC
                |
                | get one allow-listed secret
                v
       Safe metadata only -> Browser
```

No SQL database or VM is required, which reduces cost and keeps the lab focused.

## Application features

- Responsive security operations dashboard
- Allow-list preventing arbitrary secret-name input
- Safe metadata inspection without exposing values
- `/health/live` for application liveness
- `/health/keyvault` for identity, RBAC, and retrieval verification
- Friendly authentication, authorization, missing-secret, and configuration errors
- Automated tests using a fake vault so tests never require Azure credentials
- Separate Portal, CLI, and PowerShell deployment guides

## Project structure

```text
app/
  main.py                 FastAPI routes and safe error handling
  keyvault_service.py     DefaultAzureCredential and SecretClient
  templates/index.html    Portal UI
  static/site.css         Responsive styling
tests/test_app.py          Offline automated tests
portal/README.md           Azure Portal workflow
cli/README.md              Azure CLI workflow
powershell/README.md       Azure PowerShell workflow
startup.sh                 App Service startup command
```

## Run locally

1. Install Python 3.11 or later.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Sign in to Azure.
5. Grant your user **Key Vault Secrets User** or **Key Vault Secrets Officer** on the lab vault.
6. Set `KEY_VAULT_URL`.

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
az login
$env:KEY_VAULT_URL='https://YOUR-VAULT.vault.azure.net/'
$env:ALLOWED_SECRET_NAMES='DemoApiKey,OperationsBanner,ThirdPartyEndpoint'
uvicorn app.main:app --reload
```

Bash:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
az login
export KEY_VAULT_URL='https://YOUR-VAULT.vault.azure.net/'
export ALLOWED_SECRET_NAMES='DemoApiKey,OperationsBanner,ThirdPartyEndpoint'
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Test without Azure

```powershell
pytest -q
```

Tests substitute a fake Key Vault service and assert that secret values are never rendered.

## Choose a deployment guide

- [Azure Portal](portal/README.md)
- [Azure CLI](cli/README.md)
- [Azure PowerShell](powershell/README.md)

## Security notes

The sample values in the guides are deliberately non-sensitive. Never paste a real production password into screenshots, terminal history, tickets, or source control. For production, add private endpoints, diagnostic logs, expiration alerts, a shared monitoring strategy, and separate vaults by environment.

