# What a double click on AR-750.bat does: find the rover, make sure its
# program is answering, open it on this laptop, and put a QR code up for the
# phone - so the laptop and the phone both show the live camera and both can
# drive, at the same time.
#
# Read only on the Pi. It never logs in to anything; it only asks the
# rover's website whether it is alive. Exit code 0 = open, 1 = not found.
param([string]$Root = (Split-Path -Parent $PSScriptRoot))

$ErrorActionPreference = 'SilentlyContinue'
$ProgressPreference = 'SilentlyContinue'
Set-Location $Root

function Last-Line([string]$file) {
    if (-not (Test-Path $file)) { return $null }
    Get-Content $file | Where-Object { $_ -and -not $_.TrimStart().StartsWith('#') } |
        Select-Object -Last 1 | ForEach-Object { $_.Trim() }
}
function Health([string]$addr) {
    # the rover's own "are you there" - no login needed for this one page
    try {
        $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 4 "http://$addr/api/health"
        if ($r.StatusCode -eq 200 -and $r.Content -match '"ok"\s*:\s*true') { return $r.Content }
    } catch { }
    return $null
}

Write-Host ''
Write-Host '  ================================================================'
Write-Host '     AR-750   -   SAB KUCH EK SAATH SHURU'
Write-Host '  ================================================================'
Write-Host ''

$rover = Last-Line 'rover_address.txt'      # like 192.168.0.120:8080
$piAt  = Last-Line 'pi_address.txt'         # like pi@192.168.0.120
$user = 'pi'
if ($piAt -and $piAt.Contains('@')) { $user = $piAt.Split('@')[0] }
$port = 8080
$ip = ''
if ($rover) {
    $ip = $rover.Split(':')[0]
    if ($rover.Contains(':')) { $port = [int]$rover.Split(':')[1] }
} elseif ($piAt) {
    $ip = $piAt.Split('@')[-1]
}

Write-Host "  [1/4] Rover dhoondh raha hoon$(if ($ip) { " ($ip par)" }) ..."
$h = $null
if ($ip) { $h = Health "$($ip):$port" }
if (-not $h) {
    Write-Host '        Wahan jawab nahi aaya. Poori WiFi par Raspberry Pi dhoondh raha hoon ...'
    $found = & (Join-Path $Root 'tools\locate_pi.ps1') -Last $ip
    if ($found) {
        if ($found -ne $ip) { Write-Host "        Mil gaya, naye address par: $found" }
        $ip = "$found".Trim()
    }
    if ($ip) {
        # a Pi that was just switched on needs about a minute
        Write-Host -NoNewline '        Rover ka program shuru hone ka intezaar (2 minute tak) '
        for ($i = 0; $i -lt 24 -and -not $h; $i++) {
            $h = Health "$($ip):$port"
            if (-not $h) { Write-Host -NoNewline '.'; Start-Sleep -Seconds 5 }
        }
        Write-Host ''
    }
}

if (-not $h) {
    Write-Host ''
    Write-Host '  Rover ne jawab nahi diya. Aam wajah:'
    Write-Host '    - rover (Pi) on nahi hai, ya abhi 1 minute se kam hua hai'
    Write-Host '    - laptop kisi aur WiFi par hai, rover kisi aur par'
    Write-Host '    - Pi par program kabhi dala hi nahi gaya: menu mein pehle 6, phir 5'
    exit 1
}

$addr = "$($ip):$port"
Set-Content -Path 'rover_address.txt' -Encoding ascii -Value @(
    "# The AR-750's address on your network. Written by AR-750.bat each time it finds it.",
    '# One line, no http:// in front.', $addr)
Set-Content -Path 'pi_address.txt' -Encoding ascii -Value @(
    '# The Raspberry Pi, as user@address. Kept up to date by AR-750.bat.', "$user@$ip")

$live = if ($h -match '"sim"\s*:\s*false') { 'wheels LIVE' } else { 'simulation' }
Write-Host "  [2/4] Rover chal raha hai:  http://$addr   ($live)"

$url = "http://$addr/#remote"
Write-Host '  [3/4] Laptop par khol raha hoon ...'
Start-Process $url

Write-Host '  [4/4] Phone ke liye QR code bana raha hoon ...'
$wifi = ''
try {
    $m = (netsh wlan show interfaces) | Select-String -Pattern '^\s*SSID\s*:\s*(.+)$' | Select-Object -First 1
    if ($m) { $wifi = $m.Matches[0].Groups[1].Value.Trim() }
} catch { }
$tpl = Get-Content (Join-Path $Root 'tools\phone_link.html') -Raw -Encoding UTF8
$wifiText = if ($wifi) { "&ldquo;$([System.Net.WebUtility]::HtmlEncode($wifi))&rdquo;" } else { 'wahi WiFi jis par yeh laptop hai' }
$page = $tpl.Replace('{{URL}}', $url).Replace('{{WIFI}}', $wifiText)
$out = Join-Path $env:TEMP 'AR-750 phone link.html'
Set-Content -Path $out -Value $page -Encoding utf8
Start-Process $out

Write-Host ''
Write-Host '  ================================================================'
Write-Host '     TAIYAAR.  Laptop aur phone dono ek saath chala sakte hain.'
Write-Host '  ================================================================'
Write-Host ''
Write-Host '   Laptop :  browser mein khul gaya hai'
Write-Host "   Phone  :  WiFi $(if ($wifi) { "'$wifi'" } else { 'wahi jo laptop par hai' }) se jodiye, phir QR code scan kijiye"
Write-Host "             ya yeh type kijiye:   $url"
Write-Host ''
Write-Host '   Pehli baar har device par login karna hoga, phir woh yaad rakhega.'
Write-Host '   Ek waqt mein ek hi jagah se chalaiye: jisne joystick aakhri baar hilaya, wahi chalega.'
Write-Host '   Joystick chhodte hi rover ruk jaata hai. Laal STOP dono jagah se kaam karta hai.'
exit 0
