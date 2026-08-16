# End-to-end deployment using the Azure Portal

This is the most visual path. It uses the Portal for resources, identity, RBAC, configuration, monitoring, and verification, and GitHub deployment through Deployment Center.

## 1. Prerequisites

- Azure subscription
- Permission to create resources and role assignments
- GitHub repository containing this project
- A globally unique Key Vault name and Web App name

Create one resource group for the lab so cleanup is easy.

## 2. Create the Key Vault

1. In Azure Portal, select **Create a resource > Key Vault**.
2. Choose the lab resource group and a nearby region.
3. Enter a globally unique name.
4. On **Access configuration**, select **Azure role-based access control**.
5. Keep soft delete enabled. Enable purge protection when you want production-like protection; it is irreversible for that vault.
6. Create the vault.

## 3. Give yourself secret-management access

Creating the vault does not automatically grant data-plane secret access.

1. Open the vault and select **Access control (IAM)**.
2. Select **Add > Add role assignment**.
3. Choose **Key Vault Secrets Officer**.
4. Assign access to **User, group, or service principal**.
5. Select your signed-in account and complete the assignment.
6. Wait several minutes for RBAC propagation.

## 4. Create safe lab secrets

Open **Objects > Secrets > Generate/Import** and create:

| Name | Example value | Content type |
|---|---|---|
| `DemoApiKey` | `demo-key-not-for-production-2026` | `api-key` |
| `OperationsBanner` | `Planned maintenance Sunday at 02:00 UTC` | `text/plain` |
| `ThirdPartyEndpoint` | `https://api.example.test/v1` | `url` |

These are demonstrations, not real credentials.

## 5. Create the Python Web App

1. Select **Create a resource > Web App**.
2. Publish: **Code**.
3. Runtime stack: **Python 3.11** or a currently supported Python version compatible with the project.
4. Operating system: **Linux**.
5. Use **Basic B1** for the lab if Free is unavailable or incompatible with the required feature.
6. Keep the Web App in the same region as the vault when practical.
7. Create it.

## 6. Enable managed identity

1. Open the Web App.
2. Select **Settings > Identity**.
3. On **System assigned**, switch **Status** to **On**.
4. Save and copy the displayed Object (principal) ID.

No password or client secret is created.

## 7. Grant least-privilege vault access

1. Open the Key Vault.
2. Select **Access control (IAM) > Add role assignment**.
3. Choose **Key Vault Secrets User**.
4. Assign access to **Managed identity**.
5. Select **App Service**, choose the Web App, and complete the assignment.
6. Wait up to ten minutes for propagation.

Do not assign Secrets Officer, Contributor, or Owner to the Web App.

## 8. Configure the application

Open **Web App > Settings > Environment variables** and add:

| Name | Value |
|---|---|
| `KEY_VAULT_URL` | `https://YOUR-VAULT.vault.azure.net/` |
| `ALLOWED_SECRET_NAMES` | `DemoApiKey,OperationsBanner,ThirdPartyEndpoint` |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` |

Apply the settings.

Open **Settings > Configuration > General settings** and set Startup Command to:

```text
startup.sh
```

Save and restart.

## 9. Deploy from GitHub

1. Push this project to a GitHub repository. Do not push a local `.env` file.
2. Open **Web App > Deployment Center**.
3. Choose **Continuous Deployment (CI/CD)**.
4. Source: **GitHub**.
5. Authorize Azure, then choose the organization, repository, and branch.
6. Save. Azure creates a GitHub Actions workflow and starts deployment.
7. Monitor the deployment from Deployment Center or the GitHub Actions tab.

## 10. Verify

Open:

```text
https://YOUR-APP.azurewebsites.net/health/live
```

Expected: `{"status":"healthy","service":"secretless-operations-portal"}`.

Then open:

```text
https://YOUR-APP.azurewebsites.net/health/keyvault
```

Expected: HTTP 200 with `keyVault: connected` and `identity: authorized`.

Open the home page, choose `DemoApiKey`, and select **Run secure retrieval**. Confirm that only metadata appears.

## 11. Negative test

1. Remove the Web App's **Key Vault Secrets User** assignment.
2. Wait for cached authorization to expire.
3. Re-run the Key Vault health check; expect HTTP 503.
4. The UI should show an authorization message without a secret value.
5. Restore the role and wait for propagation.

## 12. Monitoring and troubleshooting

- Use **Web App > Monitoring > Log stream** for application errors.
- A 403 normally means the managed identity lacks the correct role or RBAC has not propagated.
- A 404 from Key Vault means the selected secret does not exist.
- A 503 with “not configured” means `KEY_VAULT_URL` is missing or malformed.
- Verify that Key Vault uses RBAC, not legacy access policies.
- Never switch the deployed application to debug mode merely to reveal exceptions.

## 13. Cleanup

Delete the lab resource group. A soft-deleted vault may remain recoverable for its retention period; purge-protected vaults cannot be immediately purged.

