$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
    docker compose exec -T backend python -m xiaodianji.demo.seed
}
finally {
    Pop-Location
}
