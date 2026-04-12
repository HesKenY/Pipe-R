## Query Windows System Media Transport Controls for the currently playing
## media session (Spotify, YouTube, Groove, etc.). Emits compact JSON on
## stdout so the Pipe-R server can forward it to the deck's player strip.
##
## No auth, no OAuth, no API keys. Works with any app that registers with
## Windows SMTC (Spotify Desktop does, Spotify Web does not — use the app).

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
        '{"available":false,"playing":false}'
        return
    }
    $props = Await ($session.TryGetMediaPropertiesAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
    $info = $session.GetPlaybackInfo()
    $status = $info.PlaybackStatus.ToString()
    $out = [ordered]@{
        available = $true
        playing = ($status -eq 'Playing')
        status = $status
        title = $props.Title
        artist = $props.Artist
        album = $props.AlbumTitle
        source = $session.SourceAppUserModelId
    }
    $out | ConvertTo-Json -Compress
} catch {
    '{"available":false,"error":"' + ($_.Exception.Message -replace '"','\"') + '"}'
}
