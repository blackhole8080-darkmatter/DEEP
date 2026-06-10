# DEEP Global Command Installer
# Run this script to add 'deep' command to your system PATH

$DeepPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$DeepBinPath = Join-Path $DeepPath "bin"

# Create bin directory
New-Item -ItemType Directory -Force -Path $DeepBinPath | Out-Null

# Create wrapper script in bin
$WrapperContent = @"
@echo off
python "$DeepPath\deep.py" %*
"@

$WrapperPath = Join-Path $DeepBinPath "deep.cmd"
$WrapperContent | Out-File -FilePath $WrapperPath -Encoding ASCII

Write-Host "Created wrapper script at: $WrapperPath"

# Get current user PATH
$CurrentPath = [Environment]::GetEnvironmentVariable("PATH", "User")

# Check if already in PATH
if ($CurrentPath -notlike "*$DeepBinPath*") {
    # Add to PATH
    $NewPath = "$CurrentPath;$DeepBinPath"
    [Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
    Write-Host "Added $DeepBinPath to your PATH"
    Write-Host ""
    Write-Host "IMPORTANT: Restart your terminal or run 'refreshenv' to use the 'deep' command"
} else {
    Write-Host "DEEP is already in your PATH"
}

Write-Host ""
Write-Host "You can now run 'deep' from any directory!"
Write-Host ""
Write-Host "Usage:"
Write-Host "  deep              # Start web server"
Write-Host "  deep --port 8080  # Custom port"
Write-Host "  deep --help       # Show all options"
