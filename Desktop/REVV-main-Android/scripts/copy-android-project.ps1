param(
  [string]$Source = (Join-Path $PSScriptRoot '..\android'),
  [string]$Destination = (Join-Path $PSScriptRoot '..\site\apps\revv-main\android')
)

$sourcePath = [System.IO.Path]::GetFullPath($Source)
$destinationPath = [System.IO.Path]::GetFullPath($Destination)

if (-not (Test-Path -LiteralPath $sourcePath)) {
  throw "Source Android project not found: $sourcePath"
}

New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null

Get-ChildItem -LiteralPath $destinationPath -Force | Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $sourcePath -Force | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination $destinationPath -Recurse -Force
}

@('.gradle','.idea','.kotlin','build','capacitor-cordova-android-plugins\\build','app\\build','local.properties') | ForEach-Object {
  $target = Join-Path $destinationPath $_
  if (Test-Path -LiteralPath $target) {
    Remove-Item -LiteralPath $target -Recurse -Force
  }
}

Write-Host "Copied Android project from $sourcePath to $destinationPath"
