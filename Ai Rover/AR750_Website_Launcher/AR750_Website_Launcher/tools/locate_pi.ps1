# Prints the Raspberry Pi's IP address on this wifi, or nothing.
#
# Tries the address it was last seen at first, which is instant. Only if that
# does not answer does it ping the whole network and look for the machine with
# SSH open - preferring one whose network card is made by Raspberry Pi.
#
# Read only. It never logs in to anything.
param([string]$Last = "192.168.0.120")

function Test-Ssh([string]$ip) {
    $c = New-Object System.Net.Sockets.TcpClient
    try {
        $r = $c.BeginConnect($ip, 22, $null, $null)
        return ($r.AsyncWaitHandle.WaitOne(1500, $false) -and $c.Connected)
    } catch { return $false } finally { $c.Close() }
}

if ($Last -and (Test-Ssh $Last)) { $Last; return }

# which network are we on
$me = (Get-NetIPConfiguration | Where-Object { $_.NetAdapter.Status -eq 'Up' -and $_.IPv4DefaultGateway }).IPv4Address.IPAddress | Select-Object -First 1
if (-not $me) { return }
$net = ($me -split '\.')[0..2] -join '.'

# wake everything on it, all at once
$tasks = 1..254 | ForEach-Object {
    (New-Object System.Net.NetworkInformation.Ping).SendPingAsync("$net.$_", 400)
}
try { [System.Threading.Tasks.Task]::WaitAll($tasks) } catch { }

$piMacs = @('b8-27-eb','dc-a6-32','e4-5f-01','28-cd-c1','d8-3a-dd','2c-cf-67')
$found = @()
foreach ($line in (arp -a)) {
    if ($line -match '^\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-f\-]{17})\s') {
        $ip = $matches[1]; $mac = $matches[2].ToLower()
        if ($ip.StartsWith("$net.") -and -not $ip.EndsWith('.255') -and $ip -ne $me) {
            $isPi = $false
            foreach ($p in $piMacs) { if ($mac.StartsWith($p)) { $isPi = $true } }
            $found += [pscustomobject]@{ IP = $ip; IsPi = $isPi }
        }
    }
}
# Raspberry Pi network cards first, then anything else with SSH open
foreach ($f in ($found | Sort-Object -Property @{Expression='IsPi'; Descending=$true})) {
    if (Test-Ssh $f.IP) { $f.IP; return }
}
