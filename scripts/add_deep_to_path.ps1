$dir="C:\Users\Aryan\Aryan_Private"
$cur=[System.Environment]::GetEnvironmentVariable("PATH","User")
if ($cur -notlike "*$dir*") {
    [System.Environment]::SetEnvironmentVariable("PATH",$cur+";"+$dir,"User")
    Write-Host "Added to PATH. Open a new terminal and type: deep" -ForegroundColor Green
} else {
    Write-Host "Already in PATH. Just type: deep" -ForegroundColor Cyan
}
