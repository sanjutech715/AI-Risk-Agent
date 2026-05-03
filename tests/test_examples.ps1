# ──────────────────────────────────────────────────────────────────────────────
# Decision, Summary & Risk Agent — Quick curl Tests (PowerShell)
# Usage: PowerShell.exe -ExecutionPolicy Bypass -File .\tests\test_examples.ps1
# ──────────────────────────────────────────────────────────────────────────────

$BASE = "http://localhost:8000"

Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  1. HEALTH CHECK"
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$BASE/health" | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  2. SINGLE DOCUMENT — approve (clean invoice)"
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green
$body = @{
    document_id = "DOC001"
    standardized_data = @{
        document_type = "invoice"; issuer = "Acme Corp"
        amount = 15000.00; currency = "USD"
        issue_date = "2024-01-15"; expiry_date = "2024-04-15"
        counterparty = "Globex Ltd"; jurisdiction = "US"; metadata = @{}
    }
    validation_result = @{
        is_valid = $true; missing_fields = @(); anomalies = @()
        schema_errors = @(); completeness_score = 0.97
    }
} | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "$BASE/api/v1/analyze" -Method POST -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  3. SINGLE DOCUMENT — review (missing fields)"
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Yellow
$body = @{
    document_id = "DOC002"
    standardized_data = @{
        document_type = "contract"; issuer = "Unknown Vendor"
        amount = 450000.00; currency = "EUR"
        issue_date = "2024-01-10"; counterparty = $null
        jurisdiction = "UK"; metadata = @{}
    }
    validation_result = @{
        is_valid = $false; missing_fields = @("counterparty","expiry_date")
        anomalies = @("amount exceeds threshold"); schema_errors = @()
        completeness_score = 0.65
    }
} | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "$BASE/api/v1/analyze" -Method POST -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Red
Write-Host "  4. SINGLE DOCUMENT — reject (high risk)"
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Red
$body = @{
    document_id = "DOC003"
    standardized_data = @{
        document_type = "purchase_order"; issuer = $null
        amount = 2500000.00; currency = "USD"
        issue_date = $null; expiry_date = $null
        counterparty = $null; jurisdiction = $null; metadata = @{}
    }
    validation_result = @{
        is_valid = $false; missing_fields = @("issuer","counterparty","issue_date")
        anomalies = @("duplicate signature","amount mismatch")
        schema_errors = @("missing required field: issuer")
        completeness_score = 0.22
    }
} | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "$BASE/api/v1/analyze" -Method POST -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  5. BATCH TEST — 3 documents at once"
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
$batch = @(
    @{
        document_id = "BATCH001"
        standardized_data = @{
            document_type = "invoice"; issuer = "Acme Corp"; amount = 15000.00
            currency = "USD"; issue_date = "2024-01-15"; expiry_date = "2024-04-15"
            counterparty = "Globex Ltd"; jurisdiction = "US"; metadata = @{}
        }
        validation_result = @{
            is_valid = $true; missing_fields = @(); anomalies = @()
            schema_errors = @(); completeness_score = 0.97
        }
    },
    @{
        document_id = "BATCH002"
        standardized_data = @{
            document_type = "contract"; issuer = "Unknown Vendor"; amount = 450000.00
            currency = "EUR"; issue_date = "2024-01-10"; counterparty = $null
            jurisdiction = "UK"; metadata = @{}
        }
        validation_result = @{
            is_valid = $false; missing_fields = @("counterparty","expiry_date")
            anomalies = @("amount exceeds threshold"); schema_errors = @()
            completeness_score = 0.65
        }
    },
    @{
        document_id = "BATCH003"
        standardized_data = @{
            document_type = "purchase_order"; issuer = $null; amount = 2500000.00
            currency = "USD"; issue_date = $null; expiry_date = $null
            counterparty = $null; jurisdiction = $null; metadata = @{}
        }
        validation_result = @{
            is_valid = $false; missing_fields = @("issuer","counterparty","issue_date")
            anomalies = @("duplicate signature","amount mismatch")
            schema_errors = @("missing required field: issuer")
            completeness_score = 0.22
        }
    }
$results = Invoke-RestMethod -Uri "$BASE/api/v1/batch" -Method POST -ContentType "application/json" -Body $batch

Write-Host "-------------------------------------------------------" -ForegroundColor White
foreach ($r in $results) {
    $rec = $r.recommendation
    if ($rec -eq "approve") {
        $emoji = "🟢"
    } elseif ($rec -eq "review") {
        $emoji = "🟡"
    } elseif ($rec -eq "reject") {
        $emoji = "🔴"
    } else {
        $emoji = "❓"
    }
    Write-Host ("{0} {1,10} | rec={2,7} | score={3,6:F4} | conf={4,6:F4}" -f $emoji, $r.document_id, $r.recommendation, $r.risk_score, $r.confidence)
}
Write-Host "-------------------------------------------------------" -ForegroundColor White

Write-Host ""
Write-Host "Full response:" -ForegroundColor Cyan
$results | ConvertTo-Json -Depth 10
