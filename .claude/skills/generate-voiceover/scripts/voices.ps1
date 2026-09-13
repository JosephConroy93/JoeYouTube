<#
.SYNOPSIS  List the account's voices, or search the shared voice library, and show remaining credits.
.USAGE     .\voices.ps1                  # my voices + subscription/credits
           .\voices.ps1 -Search Jim      # shared library search by name
           .\voices.ps1 -Add <public_user_id>/<voice_id> -Name "Jim"   # add a library voice to my voices
#>
[CmdletBinding()]
param(
  [string] $Search = '',
  [string] $Add = '',
  [string] $Name = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$apiKey = [System.Environment]::GetEnvironmentVariable('ELEVENLABS_API_KEY', 'User')
if (-not $apiKey) { $apiKey = $env:ELEVENLABS_API_KEY }
if (-not $apiKey) { throw "ELEVENLABS_API_KEY not set in the user environment" }
$h = @{ 'xi-api-key' = $apiKey }
$base = 'https://api.elevenlabs.io/v1'

$sub = Invoke-RestMethod -Uri "$base/user/subscription" -Headers $h
Write-Host ("Plan: {0}   credits used {1:N0} / {2:N0}   (resets {3})" -f $sub.tier, $sub.character_count, $sub.character_limit, ([DateTimeOffset]::FromUnixTimeSeconds($sub.next_character_count_reset_unix).LocalDateTime))

if ($Add) {
  $pub, $vid = $Add -split '/', 2
  $r = Invoke-RestMethod -Method Post -Uri "$base/voices/add/$pub/$vid" -Headers ($h + @{ 'Content-Type' = 'application/json' }) -Body (@{ new_name = $Name } | ConvertTo-Json)
  Write-Host ("Added -> voice_id {0}" -f $r.voice_id)
  return
}

if ($Search) {
  $r = Invoke-RestMethod -Uri "$base/shared-voices?search=$([uri]::EscapeDataString($Search))&page_size=15" -Headers $h
  Write-Host "`nShared library matches for '$Search':"
  foreach ($v in $r.voices) {
    Write-Host ("  {0,-22} {1,-8} {2,-8} {3,-12} add: {4}/{5}" -f $v.name, $v.gender, $v.accent, $v.use_case, $v.public_owner_id, $v.voice_id)
    if ($v.description) { Write-Host ("      {0}" -f $v.description) }
    if ($v.preview_url) { Write-Host ("      preview: {0}" -f $v.preview_url) }
  }
  return
}

$r = Invoke-RestMethod -Uri "$base/voices" -Headers $h
Write-Host "`nMy voices:"
foreach ($v in $r.voices) {
  $labels = if ($v.labels) { ($v.labels.PSObject.Properties | ForEach-Object { $_.Value }) -join ', ' } else { '' }
  Write-Host ("  {0,-22} {1}   [{2}]  {3}" -f $v.name, $v.voice_id, $v.category, $labels)
}
