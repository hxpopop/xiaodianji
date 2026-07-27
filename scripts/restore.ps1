param([Parameter(Mandatory = $true)][string]$InputFile)
$ErrorActionPreference = 'Stop'
$resolved = Resolve-Path -LiteralPath $InputFile
Get-Content -Raw -LiteralPath $resolved |
    docker compose exec -T postgres psql -U xiaodianji -d xiaodianji
Write-Host "Restored from $resolved"
