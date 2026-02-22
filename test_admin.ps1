# Test script for admin panel functionality

Write-Host "Testing WhoVoted Admin Panel..." -ForegroundColor Cyan

# Test 1: Login
Write-Host "`n1. Testing admin login..." -ForegroundColor Yellow
$loginBody = @{
    username = "admin"
    password = "admin2026!"
} | ConvertTo-Json

try {
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $loginResponse = Invoke-WebRequest -Uri "http://localhost:5000/admin/login" `
        -Method POST `
        -Body $loginBody `
        -ContentType "application/json" `
        -WebSession $session `
        -ErrorAction Stop
    
    Write-Host "✓ Login successful!" -ForegroundColor Green
    Write-Host "Response: $($loginResponse.Content)" -ForegroundColor Gray
    
    # Test 2: Access dashboard
    Write-Host "`n2. Testing dashboard access..." -ForegroundColor Yellow
    $dashboardResponse = Invoke-WebRequest -Uri "http://localhost:5000/admin/dashboard" `
        -WebSession $session `
        -ErrorAction Stop
    
    Write-Host "✓ Dashboard accessible!" -ForegroundColor Green
    
    # Test 3: Upload CSV
    Write-Host "`n3. Testing CSV upload..." -ForegroundColor Yellow
    $filePath = "sample_voter_data.csv"
    $boundary = [System.Guid]::NewGuid().ToString()
    $fileContent = [System.IO.File]::ReadAllBytes($filePath)
    
    $bodyLines = @(
        "--$boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"$filePath`"",
        "Content-Type: text/csv",
        "",
        [System.Text.Encoding]::UTF8.GetString($fileContent),
        "--$boundary--"
    ) -join "`r`n"
    
    $uploadResponse = Invoke-WebRequest -Uri "http://localhost:5000/admin/upload" `
        -Method POST `
        -Body $bodyLines `
        -ContentType "multipart/form-data; boundary=$boundary" `
        -WebSession $session `
        -ErrorAction Stop
    
    Write-Host "✓ CSV upload successful!" -ForegroundColor Green
    Write-Host "Response: $($uploadResponse.Content)" -ForegroundColor Gray
    
    # Test 4: Check progress
    Write-Host "`n4. Checking processing progress..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    
    $progressResponse = Invoke-WebRequest -Uri "http://localhost:5000/admin/progress" `
        -WebSession $session `
        -ErrorAction Stop
    
    Write-Host "✓ Progress check successful!" -ForegroundColor Green
    Write-Host "Response: $($progressResponse.Content)" -ForegroundColor Gray
    
    Write-Host "`n✓ All tests passed!" -ForegroundColor Green
    
} catch {
    Write-Host "✗ Test failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
}
