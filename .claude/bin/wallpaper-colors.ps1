## Extract dominant colors from the current Windows desktop wallpaper.
## Reads HKCU\Control Panel\Desktop\WallPaper, loads the image via
## System.Drawing.Bitmap, samples a grid of pixels, buckets by hue,
## and returns the top 3 saturated colors as compact JSON.
##
## Output shape:
##   {"ok":true,"wallpaper":"C:\\...jpg","colors":["#aabbcc","#112233","#...")]}
## or {"ok":false,"error":"..."}

try {
    Add-Type -AssemblyName System.Drawing

    # Prefer TranscodedWallpaper — Windows caches the active main-display
    # wallpaper here, and it follows Wallpaper Engine overrides too.
    $wallpaperPath = $null
    $transcoded = Join-Path $env:APPDATA 'Microsoft\Windows\Themes\TranscodedWallpaper'
    if (Test-Path $transcoded) {
        $wallpaperPath = $transcoded
    } else {
        $fromReg = (Get-ItemProperty -Path 'HKCU:\Control Panel\Desktop' -Name WallPaper -ErrorAction SilentlyContinue).WallPaper
        if ($fromReg -and (Test-Path $fromReg)) { $wallpaperPath = $fromReg }
    }
    if (-not $wallpaperPath) { throw 'no wallpaper source found' }

    $bmp = [System.Drawing.Bitmap]::FromFile($wallpaperPath)
    try {
        # Downsample — step across the image on a 48x48 grid so we look at
        # only 2304 pixels no matter how big the source is.
        $step = [Math]::Max(1, [int]([Math]::Min($bmp.Width, $bmp.Height) / 48))
        $buckets = @{}

        for ($y = 0; $y -lt $bmp.Height; $y += $step) {
            for ($x = 0; $x -lt $bmp.Width; $x += $step) {
                $c = $bmp.GetPixel($x, $y)
                $r = $c.R; $g = $c.G; $b = $c.B
                $max = [Math]::Max([Math]::Max($r, $g), $b)
                $min = [Math]::Min([Math]::Min($r, $g), $b)
                $value = $max / 255.0
                $sat = if ($max -eq 0) { 0 } else { ($max - $min) / $max }
                # Skip near-black, near-white, and washed-out pixels.
                if ($value -lt 0.14) { continue }
                if ($value -gt 0.95 -and $sat -lt 0.1) { continue }
                if ($sat -lt 0.18) { continue }
                # Bucket at 4-bits per channel so similar colors merge.
                $key = '{0:X1}{1:X1}{2:X1}' -f ([int]($r / 17)), ([int]($g / 17)), ([int]($b / 17))
                if (-not $buckets.ContainsKey($key)) {
                    $buckets[$key] = [pscustomobject]@{
                        Count = 0
                        R = 0
                        G = 0
                        B = 0
                        Sat = 0
                    }
                }
                $row = $buckets[$key]
                $row.Count++
                $row.R += $r
                $row.G += $g
                $row.B += $b
                $row.Sat += $sat
            }
        }

        # Score each bucket: count * (0.5 + sat) so saturated wins over neutral
        $ranked = $buckets.GetEnumerator() | ForEach-Object {
            $v = $_.Value
            $avgR = [int]($v.R / $v.Count)
            $avgG = [int]($v.G / $v.Count)
            $avgB = [int]($v.B / $v.Count)
            $avgSat = $v.Sat / $v.Count
            $score = $v.Count * (0.5 + $avgSat)
            [pscustomobject]@{
                Hex   = '#{0:X2}{1:X2}{2:X2}' -f $avgR, $avgG, $avgB
                Count = $v.Count
                Sat   = $avgSat
                Score = $score
            }
        } | Sort-Object -Property Score -Descending

        $top = $ranked | Select-Object -First 6 | ForEach-Object { $_.Hex }
        if (-not $top) { $top = @('#ff2bb8', '#00f5ff', '#d7c7ff') }

        $result = [ordered]@{
            ok = $true
            wallpaper = $wallpaperPath
            colors = $top
        }
        $result | ConvertTo-Json -Compress
    }
    finally {
        $bmp.Dispose()
    }
} catch {
    '{"ok":false,"error":"' + ($_.Exception.Message -replace '"','\"' -replace '\\','\\\\') + '"}'
}
