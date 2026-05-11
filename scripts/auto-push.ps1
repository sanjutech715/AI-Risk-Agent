# Auto-push script for Git - commits and pushes changes automatically
# Usage: ./scripts/auto-push.ps1 "Your commit message"

param(
    [string]$Message = "Auto-commit: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    [string]$Branch = "main"
)

# Navigate to repo root
$repoPath = "c:\Users\HP\Downloads\risk-agent"
Set-Location $repoPath

Write-Host "[*] Working in: $repoPath" -ForegroundColor Green

# Check if git is available
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Git is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Check if we're in a git repository
if (-not (Test-Path .git)) {
    Write-Host "[ERROR] Not a git repository" -ForegroundColor Red
    exit 1
}

# Get current branch
$currentBranch = git rev-parse --abbrev-ref HEAD 2>$null
Write-Host "[BRANCH] Current branch: $currentBranch" -ForegroundColor Cyan

# Check for changes
$status = git status --porcelain
if ([string]::IsNullOrEmpty($status)) {
    Write-Host "[OK] No changes to commit" -ForegroundColor Yellow
    exit 0
}

Write-Host "[CHANGES] Changes detected:" -ForegroundColor Cyan
Write-Host $status

# Stage all changes
Write-Host "[*] Staging changes..." -ForegroundColor Yellow
git add .

# Commit
Write-Host "[*] Committing with message: '$Message'" -ForegroundColor Yellow
git commit -m $Message

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Commit failed" -ForegroundColor Red
    exit 1
}

# Push
Write-Host "[*] Pushing to origin/$currentBranch..." -ForegroundColor Yellow
git push origin $currentBranch

if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] Successfully pushed to GitHub!" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Push failed" -ForegroundColor Red
    exit 1
}
