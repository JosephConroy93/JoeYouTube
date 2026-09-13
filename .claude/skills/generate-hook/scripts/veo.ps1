<#
.SYNOPSIS  Veo 3.1 image-to-video for a video's hook shots via the Gemini API (predictLongRunning + poll + download).
.USAGE     .\veo.ps1 -Project <series>/<slug> [-Model lite|standard|fast] [-Shot N] [-DryRun] [-Resolution 720p|1080p]
           .\veo.ps1 -Image <path> -Prompt "<motion>" -Out <file.mp4> [-Duration 4|6|8] [-Model lite] [-Resolution 720p]   # single-clip test mode
.NOTES     Reads GEMINI_API_KEY from the user environment. Plan file: content/<series>/<slug>/claude/hook-plan.md
           (| shot | scene_id | motion_prompt | duration_s | beat |). Output: content/<series>/<slug>/hook/raw/shot-NN.mp4
           1080p requires durationSeconds 8. Exercised live: one 4 s 720p lite clip (image as bytesBase64Encoded, numeric durationSeconds, personGeneration allow_adult). UNTESTED: multi-shot plan run, 1080p, fast model id, beat trimming.
#>
[CmdletBinding()]
param(
  [string] $Project = '',
  [ValidateSet('lite','standard','fast')] [string] $Model = 'lite',
  [ValidateSet('720p','1080p')] [string] $Resolution = '1080p',
  [int]    $Shot = 0,
  [switch] $DryRun,
  # single-clip test mode
  [string] $Image = '',
  [string] $Prompt = '',
  [string] $Out = '',
  [ValidateSet(4,6,8)] [int] $Duration = 8,
  [string] $Root = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if (-not $Root) { $Root = (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..\..\..\..')).Path }
function Run-Ff([string] $cmdline) { $out = cmd /c "$cmdline 2>&1"; return (($out | ForEach-Object { "$_" }) -join "`n") }

$modelIds = @{ lite = 'veo-3.1-lite-generate-preview'; standard = 'veo-3.1-generate-preview'; fast = 'veo-3.1-fast-generate-preview' }
$modelId = $modelIds[$Model]
$apiKey = [System.Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User'); if (-not $apiKey) { $apiKey = $env:GEMINI_API_KEY }
if (-not $apiKey -and -not $DryRun) { throw 'GEMINI_API_KEY not set in the user environment' }
$base = 'https://generativelanguage.googleapis.com/v1beta'
$headers = @{ 'x-goog-api-key' = $apiKey; 'Content-Type' = 'application/json' }
$scratch = Join-Path $env:TEMP 'veo-hook'; New-Item -ItemType Directory -Force $scratch | Out-Null

function Build-Body([string] $imgPath, [string] $motion, [int] $dur, [string] $res) {
  $mime = if ($imgPath -match '\.png$') { 'image/png' } else { 'image/jpeg' }
  $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($imgPath))
  if ($res -eq '1080p' -and $dur -ne 8) { Write-Warning "1080p requires 8 s; forcing durationSeconds 8 (was $dur)"; $dur = 8 }
  return (@{ instances = @(@{ prompt = $motion; image = @{ bytesBase64Encoded = $b64; mimeType = $mime } })
             parameters = @{ aspectRatio = '16:9'; durationSeconds = $dur; resolution = $res; personGeneration = 'allow_adult' } } | ConvertTo-Json -Depth 8 -Compress)
}
function Submit([string] $body, [string] $label) {
  try { $r = Invoke-RestMethod -Method Post -Uri "$base/models/${modelId}:predictLongRunning" -Headers $headers -Body ([Text.Encoding]::UTF8.GetBytes($body)) }
  catch {
    $detail = $_.Exception.Message
    try { $rs = $_.Exception.Response.GetResponseStream(); $sr = New-Object IO.StreamReader($rs); $detail = $sr.ReadToEnd() } catch {}
    throw "submit $label failed: $detail"
  }
  Write-Host ("  submitted {0} -> {1}" -f $label, $r.name); return $r.name
}
function Wait-Op([string] $opName) {
  for ($i = 0; $i -lt 80; $i++) {
    $op = Invoke-RestMethod -Uri "$base/$opName" -Headers @{ 'x-goog-api-key' = $apiKey }
    if ($op.PSObject.Properties['done'] -and $op.done) { return $op }
    Start-Sleep -Seconds 15
  }
  throw "operation $opName not done after 20 minutes"
}
function Download-Op($op, [string] $outPath) {
  if ($op.PSObject.Properties['error']) { throw ("generation failed: " + ($op.error | ConvertTo-Json -Compress)) }
  $uri = $op.response.generateVideoResponse.generatedSamples[0].video.uri
  if (-not $uri) { throw ("no video uri in response: " + ($op.response | ConvertTo-Json -Depth 6 -Compress)) }
  New-Item -ItemType Directory -Force (Split-Path $outPath) | Out-Null
  Invoke-WebRequest -Uri $uri -Headers @{ 'x-goog-api-key' = $apiKey } -OutFile $outPath -MaximumRedirection 5
  $probe = Run-Ff "ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_frames:format=duration -of csv=p=0 `"$outPath`""
  Write-Host ("  saved {0}  [{1}]" -f $outPath, ($probe -replace "`n", ' | '))
}

# ---------- single-clip test mode ----------
if ($Image) {
  if (-not $Out) { throw '-Out is required with -Image' }
  $body = Build-Body $Image $Prompt $Duration $Resolution
  if ($DryRun) { $p = Join-Path $scratch 'test.request.json'; [IO.File]::WriteAllText($p, $body, (New-Object Text.UTF8Encoding($false))); Write-Host "[dry-run] $p ($($body.Length) bytes)"; return }
  Write-Host ("Veo {0} {1} {2}s from {3}" -f $modelId, $Resolution, $Duration, (Split-Path $Image -Leaf))
  $op = Submit $body 'test'
  Download-Op (Wait-Op $op) $Out
  return
}

# ---------- plan mode ----------
if (-not $Project) { throw 'Give -Project <series>/<slug> or -Image for a single test clip' }
$series, $slug = $Project -split '/', 2
$videoDir = Join-Path $Root "content\$series\$slug"
$plan = Join-Path $videoDir 'claude\hook-plan.md'
if (-not (Test-Path $plan)) { throw "No hook plan at $plan" }
$rows = @()
foreach ($line in Get-Content $plan -Encoding UTF8) {
  if ($line -match '^\|\s*(\d+)\s*\|\s*`?([^`|]+?)`?\s*\|\s*(.*?)\s*\|\s*(\d)\s*\|\s*(.*?)\s*\|\s*$') {
    $rows += [pscustomobject]@{ shot = [int]$Matches[1]; scene_id = $Matches[2].Trim(); motion = $Matches[3]; dur = [int]$Matches[4]; beat = $Matches[5] }
  }
}
if ($rows.Count -eq 0) { throw 'hook-plan.md has no shot rows' }
if ($rows.Count -gt 8) { throw "hook plan has $($rows.Count) shots; cap is 8" }
if ($Shot -gt 0) { $rows = @($rows | Where-Object shot -eq $Shot) }
$ops = @()
foreach ($r in $rows) {
  $still = Get-ChildItem (Join-Path $videoDir 'scene-generation') -File | Where-Object { $_.BaseName -eq $r.scene_id } | Select-Object -First 1
  if (-not $still) { throw "shot $($r.shot): no canonical image for scene_id $($r.scene_id)" }
  $body = Build-Body $still.FullName $r.motion $r.dur $Resolution
  $label = ('shot-{0:D2}' -f $r.shot)
  if ($DryRun) { $p = Join-Path $scratch "$label.request.json"; [IO.File]::WriteAllText($p, $body, (New-Object Text.UTF8Encoding($false))); Write-Host "[dry-run] $label -> $p"; continue }
  $ops += [pscustomobject]@{ label = $label; op = (Submit $body $label); dur = $r.dur }
}
if ($DryRun) { return }
foreach ($o in $ops) {
  $done = Wait-Op $o.op
  Download-Op $done (Join-Path $videoDir "hook\raw\$($o.label).mp4")
}
$secs = ($rows | Measure-Object dur -Sum).Sum
$rate = @{ lite = @{ '720p' = 0.04; '1080p' = 0.06 }; fast = @{ '720p' = 0.08; '1080p' = 0.09 }; standard = @{ '720p' = 0.31; '1080p' = 0.31 } }[$Model][$Resolution]
Write-Host ("Done: {0} shots, {1}s requested, approx GBP {2:N2}. Next: trim to beats once scene-timing.md exists (see SKILL.md step 2)." -f $rows.Count, $secs, ($secs * $rate))
