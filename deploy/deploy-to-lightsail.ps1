# PowerShell script to deploy WhoVoted to AWS Lightsail
# Run this from your local machine

$ErrorActionPreference = "Stop"

Write-Host "=== WhoVoted Lightsail Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Configuration
$INSTANCE_NAME = "whovoted-app"
$BUNDLE_ID = "micro_3_0"  # $10/month - 1 GB RAM, 2 vCPUs, 60 GB SSD
$REGION = "us-east-1"
$BLUEPRINT_ID = "ubuntu_22_04"
$KEY_PAIR_NAME = "whovoted-key"

# Check if AWS CLI is available
Write-Host "Checking AWS CLI..." -ForegroundColor Yellow
try {
    $awsVersion = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" --version
    Write-Host "AWS CLI found: $awsVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: AWS CLI not found!" -ForegroundColor Red
    exit 1
}

# Check AWS credentials
Write-Host "Checking AWS credentials..." -ForegroundColor Yellow
try {
    $identity = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" sts get-caller-identity | ConvertFrom-Json
    Write-Host "Authenticated as Account: $($identity.Account)" -ForegroundColor Green
} catch {
    Write-Host "ERROR: AWS credentials not configured!" -ForegroundColor Red
    exit 1
}

# Check if instance already exists
Write-Host "Checking for existing instance..." -ForegroundColor Yellow
$ErrorActionPreference = "SilentlyContinue"
$existingInstance = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" lightsail get-instance --instance-name $INSTANCE_NAME --region $REGION 2>$null
$ErrorActionPreference = "Stop"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Instance '$INSTANCE_NAME' already exists!" -ForegroundColor Yellow
    $response = Read-Host "Do you want to delete and recreate it? (yes/no)"
    if ($response -eq "yes") {
        Write-Host "Deleting existing instance..." -ForegroundColor Yellow
        & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" lightsail delete-instance --instance-name $INSTANCE_NAME --region $REGION
        Write-Host "Waiting for deletion to complete (30 seconds)..." -ForegroundColor Yellow
        Start-Sleep -Seconds 30
    } else {
        Write-Host "Deployment cancelled." -ForegroundColor Red
        exit 0
    }
} else {
    Write-Host "No existing instance found. Creating new instance..." -ForegroundColor Green
}

# Create key pair if it doesn't exist
Write-Host "Creating SSH key pair..." -ForegroundColor Yellow
$keyPairPath = ".\$KEY_PAIR_NAME.pem"
if (Test-Path $keyPairPath) {
    Write-Host "Key pair already exists at $keyPairPath" -ForegroundColor Green
} else {
    try {
        $keyPairJson = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" lightsail create-key-pair --key-pair-name $KEY_PAIR_NAME --region $REGION | ConvertFrom-Json
        $keyPairJson.privateKeyBase64 | Out-File -FilePath $keyPairPath -Encoding ASCII
        Write-Host "Key pair created and saved to $keyPairPath" -ForegroundColor Green
    } catch {
        Write-Host "Key pair might already exist in AWS, continuing..." -ForegroundColor Yellow
    }
}

# Read the setup script
$setupScriptPath = ".\lightsail-setup.sh"
if (-not (Test-Path $setupScriptPath)) {
    Write-Host "ERROR: Setup script not found at $setupScriptPath" -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    exit 1
}
$setupScript = Get-Content $setupScriptPath -Raw

# Create instance with user data
Write-Host "Creating Lightsail instance..." -ForegroundColor Yellow
Write-Host "  Name: $INSTANCE_NAME" -ForegroundColor Cyan
Write-Host "  Bundle: $BUNDLE_ID (1 GB RAM, 2 vCPUs, 60 GB SSD - `$10/month)" -ForegroundColor Cyan
Write-Host "  Region: $REGION" -ForegroundColor Cyan
Write-Host "  Blueprint: $BLUEPRINT_ID" -ForegroundColor Cyan

& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" lightsail create-instances `
    --instance-names $INSTANCE_NAME `
    --availability-zone "${REGION}a" `
    --blueprint-id $BLUEPRINT_ID `
    --bundle-id $BUNDLE_ID `
    --key-pair-name $KEY_PAIR_NAME `
    --user-data "file://lightsail-setup.sh" `
    --region $REGION

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create instance!" -ForegroundColor Red
    exit 1
}

Write-Host "Instance created successfully!" -ForegroundColor Green
Write-Host "Waiting for instance to start (60 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 60

# Get instance details
Write-Host "Getting instance details..." -ForegroundColor Yellow
$instanceJson = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" lightsail get-instance --instance-name $INSTANCE_NAME --region $REGION | ConvertFrom-Json
$publicIp = $instanceJson.instance.publicIpAddress

Write-Host ""
Write-Host "=== Instance Created Successfully! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Instance Name: $INSTANCE_NAME" -ForegroundColor Cyan
Write-Host "Public IP: $publicIp" -ForegroundColor Cyan
Write-Host "SSH Key: $keyPairPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "The setup script is running in the background. It will take 5-10 minutes to complete." -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Wait 5-10 minutes for setup to complete" -ForegroundColor White
Write-Host "2. SSH into the instance:" -ForegroundColor White
Write-Host "   ssh -i $keyPairPath ubuntu@$publicIp" -ForegroundColor Gray
Write-Host "3. Edit the environment file with your AWS credentials:" -ForegroundColor White
Write-Host "   sudo nano /opt/whovoted/.env" -ForegroundColor Gray
Write-Host "4. Restart the application:" -ForegroundColor White
Write-Host "   sudo supervisorctl restart whovoted" -ForegroundColor Gray
Write-Host "5. Access your application at:" -ForegroundColor White
Write-Host "   http://$publicIp" -ForegroundColor Cyan
Write-Host ""
Write-Host "To check setup progress:" -ForegroundColor Yellow
Write-Host "   ssh -i $keyPairPath ubuntu@$publicIp 'tail -f /var/log/cloud-init-output.log'" -ForegroundColor Gray
Write-Host ""
Write-Host "To open firewall port 80:" -ForegroundColor Yellow
Write-Host "   aws lightsail open-instance-public-ports --instance-name $INSTANCE_NAME --port-info fromPort=80,toPort=80,protocol=tcp --region $REGION" -ForegroundColor Gray
Write-Host ""
