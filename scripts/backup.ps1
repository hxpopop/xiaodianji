param([string]$Output = ".\xiaodianji-backup.sql")
$ErrorActionPreference = 'Stop'
docker compose exec -T postgres pg_dump `
    -U xiaodianji `
    -d xiaodianji `
    --clean `
    --if-exists |
    Set-Content -LiteralPath $Output -Encoding utf8
Write-Host "Backup written to $Output"
