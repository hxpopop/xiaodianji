param(
    [string]$ApiBase = 'http://localhost:8080/api/v1',
    [string]$ShopId = '00000000-0000-0000-0000-000000000101'
)

$ErrorActionPreference = 'Stop'
$headers = @{ 'X-Shop-Id' = $ShopId }
$body = @{ model_name = 'configured' } | ConvertTo-Json
Invoke-RestMethod `
    -Method Post `
    -Uri "$ApiBase/evaluations/run" `
    -Headers $headers `
    -ContentType 'application/json' `
    -Body $body |
    ConvertTo-Json -Depth 8
