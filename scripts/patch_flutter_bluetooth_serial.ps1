# Re-apply namespace fix to flutter_bluetooth_serial in pub cache (AGP 8+).
# Run this after "flutter pub get" if the plugin was re-downloaded and build fails with "Namespace not specified".

$pluginPath = "$env:LOCALAPPDATA\Pub\Cache\hosted\pub.dev\flutter_bluetooth_serial-0.4.0\android\build.gradle"
if (-not (Test-Path $pluginPath)) {
    Write-Host "Plugin not found. Run 'flutter pub get' first." -ForegroundColor Yellow
    exit 1
}

$content = Get-Content $pluginPath -Raw
if ($content -like "*namespace*io.github.edufolly.flutterbluetoothserial*") {
    Write-Host "Namespace already set. No change needed." -ForegroundColor Green
    exit 0
}

$lines = Get-Content $pluginPath
$newLines = @()
$inserted = $false
foreach ($line in $lines) {
    $newLines += $line
    if (-not $inserted -and $line -match "^\s*android\s*\{") {
        $newLines += "    namespace 'io.github.edufolly.flutterbluetoothserial'"
        $inserted = $true
    }
}
$newLines | Set-Content $pluginPath
Write-Host "Patched flutter_bluetooth_serial android/build.gradle with namespace." -ForegroundColor Green
