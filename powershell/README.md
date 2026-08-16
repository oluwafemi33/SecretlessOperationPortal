# End-to-end deployment using Azure PowerShell

Commands create billable Azure resources. Run them from the project root.

## 1. Variables and sign-in

```powershell
Connect-AzAccount
Set-AzContext -SubscriptionId '<subscription-id>'
$ResourceGroup='rg-secretless-lab'
$Location='westeurope'
$Suffix='<unique-lowercase-suffix>'
$VaultName="kv-secretless-$Suffix"
$PlanName='plan-secretless-lab'
$AppName="app-secretless-$Suffix"
```

## 2. Create the vault and grant your user access

```powershell
New-AzResourceGroup -Name $ResourceGroup -Location $Location
New-AzKeyVault -Name $VaultName -ResourceGroupName $ResourceGroup -Location $Location -EnableRbacAuthorization
$Vault=Get-AzKeyVault -VaultName $VaultName
$Me=(Get-AzADUser -SignedIn).Id
New-AzRoleAssignment -ObjectId $Me -RoleDefinitionName 'Key Vault Secrets Officer' -Scope $Vault.ResourceId
```

After RBAC propagation, create safe demo secrets:

```powershell
Set-AzKeyVaultSecret -VaultName $VaultName -Name DemoApiKey -SecretValue (ConvertTo-SecureString 'demo-key-not-for-production-2026' -AsPlainText -Force) -ContentType 'api-key'
Set-AzKeyVaultSecret -VaultName $VaultName -Name OperationsBanner -SecretValue (ConvertTo-SecureString 'Planned maintenance Sunday at 02:00 UTC' -AsPlainText -Force) -ContentType 'text/plain'
Set-AzKeyVaultSecret -VaultName $VaultName -Name ThirdPartyEndpoint -SecretValue (ConvertTo-SecureString 'https://api.example.test/v1' -AsPlainText -Force) -ContentType 'url'
```

## 3. Create App Service and managed identity

```powershell
New-AzAppServicePlan -ResourceGroupName $ResourceGroup -Name $PlanName -Location $Location -Tier Basic -NumberofWorkers 1 -WorkerSize Small -Linux
New-AzWebApp -ResourceGroupName $ResourceGroup -Name $AppName -Location $Location -AppServicePlan $PlanName
Set-AzWebApp -ResourceGroupName $ResourceGroup -Name $AppName -LinuxFxVersion 'PYTHON|3.11'
$WebApp=Set-AzWebApp -ResourceGroupName $ResourceGroup -Name $AppName -AssignIdentity $true
$PrincipalId=$WebApp.Identity.PrincipalId
New-AzRoleAssignment -ObjectId $PrincipalId -RoleDefinitionName 'Key Vault Secrets User' -Scope $Vault.ResourceId
```

## 4. Configure and deploy

```powershell
$Settings=@{
  KEY_VAULT_URL="https://$VaultName.vault.azure.net/"
  ALLOWED_SECRET_NAMES='DemoApiKey,OperationsBanner,ThirdPartyEndpoint'
  SCM_DO_BUILD_DURING_DEPLOYMENT='true'
}
Set-AzWebApp -ResourceGroupName $ResourceGroup -Name $AppName -AppSettings $Settings
$WebConfigProperties=@{ linuxFxVersion='PYTHON|3.11'; appCommandLine='startup.sh' }
Set-AzResource -ResourceGroupName $ResourceGroup -ResourceType 'Microsoft.Web/sites/config' -ResourceName "$AppName/web" -Properties $WebConfigProperties -ApiVersion '2024-11-01' -Force
Compress-Archive -Path .\app,.\requirements.txt,.\startup.sh -DestinationPath .\publish.zip -Force
Publish-AzWebApp -ResourceGroupName $ResourceGroup -Name $AppName -ArchivePath (Resolve-Path .\publish.zip) -Clean -Restart -Force
```

If your installed Az module rejects the configuration API version, set `startup.sh` in Portal under **Configuration > General settings**, or use a currently supported `Microsoft.Web/sites/config` API version for your environment.

## 5. Verify

```powershell
Invoke-RestMethod "https://$AppName.azurewebsites.net/health/live" | Format-List
Invoke-RestMethod "https://$AppName.azurewebsites.net/health/keyvault" | Format-List
```

Expected Key Vault values: `status=healthy`, `keyVault=connected`, and `identity=authorized`.

## 6. Negative test

```powershell
Remove-AzRoleAssignment -ObjectId $PrincipalId -RoleDefinitionName 'Key Vault Secrets User' -Scope $Vault.ResourceId
```

After propagation, expect HTTP 503 from the Key Vault health endpoint. Restore access:

```powershell
New-AzRoleAssignment -ObjectId $PrincipalId -RoleDefinitionName 'Key Vault Secrets User' -Scope $Vault.ResourceId
```

## 7. Troubleshooting

```powershell
Get-AzWebApp -ResourceGroupName $ResourceGroup -Name $AppName
Get-AzRoleAssignment -ObjectId $PrincipalId -Scope $Vault.ResourceId
Get-AzKeyVaultSecret -VaultName $VaultName | Select-Object Name,Enabled
```

Wait up to ten minutes after role changes. Use App Service Log stream for startup and Key Vault errors. Never print real secret values during troubleshooting.

## 8. Cleanup

```powershell
Remove-AzResourceGroup -Name $ResourceGroup -Force
```
