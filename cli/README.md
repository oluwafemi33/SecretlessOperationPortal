# End-to-end deployment using Azure CLI

Commands use Bash syntax. They create billable Azure resources. Run them from the project root.

## 1. Variables and sign-in

```bash
az login
az account set --subscription "<subscription-id>"
RG="rg-secretless-lab"
LOCATION="westeurope"
SUFFIX="<unique-lowercase-suffix>"
KV="kv-secretless-$SUFFIX"
PLAN="plan-secretless-lab"
APP="app-secretless-$SUFFIX"
```

## 2. Create the vault and grant your user access

```bash
az group create --name "$RG" --location "$LOCATION"
az keyvault create --name "$KV" --resource-group "$RG" --location "$LOCATION" --enable-rbac-authorization true
KV_ID=$(az keyvault show --name "$KV" --query id -o tsv)
MY_ID=$(az ad signed-in-user show --query id -o tsv)
az role assignment create --assignee-object-id "$MY_ID" --assignee-principal-type User --role "Key Vault Secrets Officer" --scope "$KV_ID"
```

Wait for RBAC propagation, then create safe demo secrets:

```bash
az keyvault secret set --vault-name "$KV" --name DemoApiKey --value "demo-key-not-for-production-2026" --content-type "api-key"
az keyvault secret set --vault-name "$KV" --name OperationsBanner --value "Planned maintenance Sunday at 02:00 UTC" --content-type "text/plain"
az keyvault secret set --vault-name "$KV" --name ThirdPartyEndpoint --value "https://api.example.test/v1" --content-type "url"
```

## 3. Create App Service and managed identity

```bash
az appservice plan create --resource-group "$RG" --name "$PLAN" --location "$LOCATION" --sku B1 --is-linux
az webapp create --resource-group "$RG" --plan "$PLAN" --name "$APP" --runtime "PYTHON:3.11" --startup-file "startup.sh"
APP_PRINCIPAL=$(az webapp identity assign --resource-group "$RG" --name "$APP" --query principalId -o tsv)
az role assignment create --assignee-object-id "$APP_PRINCIPAL" --assignee-principal-type ServicePrincipal --role "Key Vault Secrets User" --scope "$KV_ID"
```

## 4. Configure and deploy

```bash
az webapp config appsettings set --resource-group "$RG" --name "$APP" --settings   KEY_VAULT_URL="https://$KV.vault.azure.net/"   ALLOWED_SECRET_NAMES="DemoApiKey,OperationsBanner,ThirdPartyEndpoint"   SCM_DO_BUILD_DURING_DEPLOYMENT="true"

zip -r publish.zip app requirements.txt startup.sh
az webapp deploy --resource-group "$RG" --name "$APP" --src-path publish.zip --type zip
az webapp restart --resource-group "$RG" --name "$APP"
```

PowerShell ZIP alternative:

```powershell
Compress-Archive -Path .\app,.\requirements.txt,.\startup.sh -DestinationPath .\publish.zip -Force
```

## 5. Verify

```bash
curl -i "https://$APP.azurewebsites.net/health/live"
curl -i "https://$APP.azurewebsites.net/health/keyvault"
az webapp log config --resource-group "$RG" --name "$APP" --application-logging filesystem --level information
az webapp log tail --resource-group "$RG" --name "$APP"
```

The Key Vault health endpoint should return HTTP 200, `connected`, and `authorized`. The home page must show metadata, never the value.

## 6. Negative test

```bash
az role assignment delete --assignee-object-id "$APP_PRINCIPAL" --role "Key Vault Secrets User" --scope "$KV_ID"
```

After propagation, `/health/keyvault` should return 503. Restore access:

```bash
az role assignment create --assignee-object-id "$APP_PRINCIPAL" --assignee-principal-type ServicePrincipal --role "Key Vault Secrets User" --scope "$KV_ID"
```

## 7. Troubleshooting

```bash
az webapp identity show --resource-group "$RG" --name "$APP"
az role assignment list --assignee "$APP_PRINCIPAL" --scope "$KV_ID" -o table
az webapp config appsettings list --resource-group "$RG" --name "$APP" --query "[?name=='KEY_VAULT_URL']"
```

Wait up to ten minutes after role changes. Confirm secret names are case-sensitive and the vault URL ends in `.vault.azure.net/`.

## 8. Cleanup

```bash
az group delete --name "$RG" --yes --no-wait
```

