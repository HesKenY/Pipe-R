## Send a transport control command to the currently active Windows media
## session. Usage: smtc-control.ps1 <play|pause|toggle|next|prev>
## Prints compact JSON with the result.

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("play","pause","toggle","next","prev")]
    [string]$Action
)

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asyncMethods = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }
$asyncTaskGeneric = $asyncMethods[0]

function Await($op, $type) {
    $task = $asyncTaskGeneric.MakeGenericMethod($type).Invoke($null, @($op))
    $task.Wait() | Out-Null
    $task.Result
}

try {
    [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime] | Out-Null
    $mgr = Await ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
    $session = $mgr.GetCurrentSession()
    if ($null -eq $session) {
        '{"ok":false,"error":"no active media session"}'
        return
    }

    $ok = $false
    switch ($Action) {
        'play'   { $ok = Await ($session.TryPlayAsync())         ([bool]) }
        'pause'  { $ok = Await ($session.TryPauseAsync())        ([bool]) }
        'toggle' { $ok = Await ($session.TryTogglePlayPauseAsync()) ([bool]) }
        'next'   { $ok = Await ($session.TrySkipNextAsync())     ([bool]) }
        'prev'   { $ok = Await ($session.TrySkipPreviousAsync()) ([bool]) }
    }

    $result = [ordered]@{
        ok     = [bool]$ok
        action = $Action
        source = $session.SourceAppUserModelId
    }
    $result | ConvertTo-Json -Compress
} catch {
    '{"ok":false,"error":"' + ($_.Exception.Message -replace '"','\"') + '"}'
}
