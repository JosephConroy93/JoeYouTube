<#
.SYNOPSIS
  ElevenLabs voiceover for one video: segment script.md, call the
  with-timestamps endpoint per segment, save MP3 + alignment JSON, normalise
  to -16 LUFS dual-mono 48 kHz WAV.

.USAGE
  .\tts.ps1 -Project watcher-pov/my-video [-Segment 3] [-DryRun] [-MaxChars 4500] [-Seed 12345]

.STATUS
  Live-tested on one 3,273-character segment (generate + normalise + alignment).
  Untested: a full multi-segment run and the -Segment regeneration path with a
  stored seed.

.NOTES
  Reads ELEVENLABS_API_KEY from the user environment (conventions.md).
  Requires ffmpeg on PATH. Voice id/model come from content/<series>/series.md
  (video.md may override `voice.id` / `voice.model`).
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)] [string] $Project,     # <series>/<slug>
  [int]    $Segment  = 0,                        # 0 = all
  [switch] $DryRun,
  [switch] $SkipGenerate,                       # normalise existing MP3s only (no API call)
  [double] $Speed = 0,                          # ElevenLabs voice_settings.speed (0.7-1.2); 0 = series.md/video.md voice.speed, else 1.0
  [string] $Tag = '',                           # optional test suffix: <slug>_voice_NN_<tag>
  [int]    $MaxChars = 4500,
  [int]    $Seed     = 0,                        # 0 = derive from slug (stable)
  [string] $Root = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
# ffmpeg writes everything to stderr; PowerShell 5.1 turns that into errors under Stop, so route through cmd.
function Run-Ff([string] $cmdline) { $out = cmd /c "$cmdline 2>&1"; return (($out | ForEach-Object { "$_" }) -join "`n") }
if (-not $Root) { $Root = (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..\..\..\..')).Path }

# ---------- paths ----------
$series, $slug = $Project -split '/', 2
if (-not $slug) { throw "Project must be <series>/<slug>" }
$seriesDir = Join-Path $Root "content\$series"
$videoDir  = Join-Path $seriesDir $slug
$claudeDir = Join-Path $videoDir 'claude'
$script    = Join-Path $claudeDir 'script.md'
$segDir    = Join-Path $claudeDir 'voiceover-segments'
$alignDir  = Join-Path $claudeDir 'transcripts'
$voDir     = Join-Path $videoDir 'voiceovers'
$normDir   = Join-Path $voDir 'normalized'
foreach ($d in $segDir, $alignDir, $voDir, $normDir) { New-Item -ItemType Directory -Force $d | Out-Null }
if (-not (Test-Path $script)) { throw "No script at $script" }

# ---------- config lookup (key | value markdown tables) ----------
function Read-ConfigTable([string] $path) {
  $h = @{}
  if (-not (Test-Path $path)) { return $h }
  foreach ($line in Get-Content $path -Encoding UTF8) {
    if ($line -match '^\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|\s*$') { $h[$matches[1]] = ($matches[2] -replace '`','').Trim() }
  }
  return $h
}
$cfg = Read-ConfigTable (Join-Path $seriesDir 'series.md')
$vid = Read-ConfigTable (Join-Path $videoDir 'video.md')
$voiceId    = if ($vid['voice.id'])    { $vid['voice.id'] }    else { $cfg['voice.id'] }
$voiceModel = if ($vid['voice.model']) { $vid['voice.model'] } else { $cfg['voice.model'] }
if (-not $voiceModel) { $voiceModel = 'eleven_multilingual_v2' }
if (-not $voiceId -or $voiceId -match '^\*?\(?unset') {
  if ($DryRun) { $voiceId = 'VOICE_ID_UNSET' } else { throw "voice.id is unset in series.md/video.md - audition in the ElevenLabs MCP and record the id first" }
}
$voiceId = ($voiceId -replace '`','').Trim()
if ($Seed -eq 0) { $Seed = [math]::Abs([int]([System.BitConverter]::ToInt32([System.Security.Cryptography.SHA1]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($slug)), 0))) % 4294967295 }

$apiKey = [System.Environment]::GetEnvironmentVariable('ELEVENLABS_API_KEY', 'User')
if (-not $apiKey) { $apiKey = $env:ELEVENLABS_API_KEY }
if (-not $apiKey -and -not $DryRun) { throw "ELEVENLABS_API_KEY not set in the user environment" }

# ---------- segmentation ----------
$raw = Get-Content $script -Raw -Encoding UTF8
# drop handoff notes and any front matter
$raw = ($raw -split '(?m)^## Handoff notes')[0]
# chapters: a markdown heading or a --- rule starts a new chunk
$chunks = [System.Collections.Generic.List[string]]::new()
$cur = [System.Text.StringBuilder]::new()
foreach ($line in ($raw -split "`r?`n")) {
  if ($line -match '^#\s') { continue }   # the document title (H1) is never spoken
  if ($line -match '^(#{1,6}\s|---\s*$)') {
    if ($cur.Length -gt 0) { $chunks.Add($cur.ToString().Trim()); $cur.Clear() | Out-Null }
    if ($line -match '^#{1,6}\s+(.*)$') { $cur.AppendLine($matches[1].Trim()) | Out-Null }  # spoken heading (e.g. "Level one, the chosen.")
    continue
  }
  $cur.AppendLine($line) | Out-Null
}
if ($cur.Length -gt 0) { $chunks.Add($cur.ToString().Trim()) }
$chunks = $chunks | Where-Object { $_ }

function Clean-Text([string] $t) {
  $t = $t -replace '\*\*|__|\*|_', ''          # emphasis
  $t = $t -replace '\[([^\]]+)\]\([^)]+\)', '$1' # links
  $t = $t -replace '`', ''
  $t = $t -replace '(?m)^\s*>\s?', ''          # blockquotes
  return ($t -replace "[ \t]+`n", "`n").Trim()
}

# merge chunks until MaxChars
$segments = [System.Collections.Generic.List[string]]::new()
$buf = ''
foreach ($c in $chunks) {
  $c = Clean-Text $c
  if (($buf.Length + $c.Length + 2) -gt $MaxChars -and $buf) { $segments.Add($buf.Trim()); $buf = '' }
  $buf += ($(if ($buf) { "`n`n" } else { '' }) + $c)
}
if ($buf) { $segments.Add($buf.Trim()) }
if ($segments.Count -eq 0) { throw "Script produced no segments" }

# labels: <slug>_voice_NN (sorted filename order = playback order)
$labels = @()
for ($i = 0; $i -lt $segments.Count; $i++) {
  $labels += ('{0}_voice_{1:D2}' -f $slug, ($i + 1))
}
if ($Speed -eq 0) {
  $cfgSpeed = if ($vid['voice.speed']) { $vid['voice.speed'] } else { $cfg['voice.speed'] }
  $Speed = if ($cfgSpeed) { [double]$cfgSpeed } else { 1.0 }
}

Write-Host ("Segments: {0}  (chars: {1})" -f $segments.Count, (($segments | ForEach-Object Length) -join ', '))
for ($i = 0; $i -lt $segments.Count; $i++) {
  [IO.File]::WriteAllText((Join-Path $segDir "$($labels[$i]).txt"), $segments[$i], (New-Object System.Text.UTF8Encoding($false)))
}

# ---------- generation ----------
$endpointBase = 'https://api.elevenlabs.io/v1/text-to-speech'
$todo = if ($Segment -gt 0) { @($Segment - 1) } else { 0..($segments.Count - 1) }
foreach ($i in $todo) {
  $label = $labels[$i]
  if ($Tag) { $label = ('{0}_{1}' -f $label, $Tag) }
  $body = @{
    text          = $segments[$i]
    model_id      = $voiceModel
    seed          = $Seed
    previous_text = $(if ($i -gt 0) { $segments[$i - 1].Substring([math]::Max(0, $segments[$i - 1].Length - 600)) } else { $null })
    next_text     = $(if ($i -lt $segments.Count - 1) { $segments[$i + 1].Substring(0, [math]::Min(600, $segments[$i + 1].Length)) } else { $null })
    voice_settings = @{ stability = 0.5; similarity_boost = 0.75; style = 0; use_speaker_boost = $true; speed = $Speed }
  }
  $json = $body | ConvertTo-Json -Depth 5 -Compress
  $uri  = "$endpointBase/$voiceId/with-timestamps?output_format=mp3_44100_128"

  if ($DryRun) {
    $scratch = Join-Path $env:TEMP "tts-dryrun-$slug"; New-Item -ItemType Directory -Force $scratch | Out-Null
    Set-Content -Path (Join-Path $scratch "$label.request.json") -Value $json -Encoding UTF8
    Write-Host "[dry-run] $label -> $uri  ($($segments[$i].Length) chars) request written to $scratch"
    continue
  }

  $mp3 = Join-Path $voDir "$label.mp3"
  if ($SkipGenerate) {
    if (-not (Test-Path $mp3)) { throw "SkipGenerate: no MP3 at $mp3" }
    Write-Host "Normalising existing $label..."
  } else {
  Write-Host "Generating $label ($($segments[$i].Length) chars)..."
  $resp = Invoke-RestMethod -Method Post -Uri $uri -Headers @{ 'xi-api-key' = $apiKey; 'Content-Type' = 'application/json' } -Body ([Text.Encoding]::UTF8.GetBytes($json))
  if (-not $resp.audio_base64) { throw "No audio_base64 in response for $label" }
  [IO.File]::WriteAllBytes($mp3, [Convert]::FromBase64String($resp.audio_base64))
  [IO.File]::WriteAllText((Join-Path $alignDir "$label.alignment.json"), ($resp.alignment | ConvertTo-Json -Depth 4 -Compress), (New-Object System.Text.UTF8Encoding($false)))
  }

  # ---------- normalise ----------
  $measure = Run-Ff "ffmpeg -hide_banner -i `"$mp3`" -af ebur128=peak=true -f null -"
  $mm = [regex]::Matches($measure, 'I:\s+(-?[\d.]+) LUFS'); if ($mm.Count -eq 0) { throw "ebur128 measure failed:`n$measure" }
  $m = $mm[$mm.Count - 1]
  $lufs = [double]$m.Groups[1].Value
  $gain = [math]::Round(-16 - $lufs, 2)
  $wav = Join-Path $normDir "$label.wav"
  $null = Run-Ff "ffmpeg -hide_banner -loglevel error -y -i `"$mp3`" -af `"volume=${gain}dB,alimiter=limit=0.8414:level=disabled:attack=5:release=50`" -ar 48000 -ac 2 -c:a pcm_s24le `"$wav`""
  if (-not (Test-Path $wav)) { throw "normalise failed for $label" }
  $check = Run-Ff "ffmpeg -hide_banner -i `"$wav`" -af ebur128=peak=true -f null -"
  $cm = [regex]::Matches($check, 'I:\s+(-?[\d.]+) LUFS'); $chk = $cm[$cm.Count - 1].Groups[1].Value
  $tm = [regex]::Matches($check, 'Peak:\s+(-?[\d.]+) dBFS'); $tp = $tm[$tm.Count - 1].Groups[1].Value
  $lm = [regex]::Matches($check, 'LRA:\s+(-?[\d.]+) LU');     $lra = $lm[$lm.Count - 1].Groups[1].Value
  $rmsOut = Run-Ff "ffmpeg -hide_banner -i `"$wav`" -af astats=measure_overall=none:measure_perchannel=RMS_level -f null -"
  $rms = [regex]::Matches($rmsOut, 'RMS level dB:\s+(-?[\d.]+)') | ForEach-Object { $_.Groups[1].Value }
  $dur = (Run-Ff "ffprobe -v error -show_entries format=duration -of csv=p=0 `"$wav`"").Trim()
  Write-Host ("  {0}: gain {1:+0.00;-0.00} dB -> I {2} LUFS, TP {3} dBFS, LRA {4} LU, RMS L/R {5}, {6:N1}s" -f $label, $gain, $chk, $tp, $lra, ($rms -join '/'), [double]$dur)
}

if (-not $DryRun) {
  $total = 0.0
  Get-ChildItem $normDir -Filter *.wav | Sort-Object Name | ForEach-Object { $total += [double]((Run-Ff "ffprobe -v error -show_entries format=duration -of csv=p=0 `"$($_.FullName)`"").Trim()) }
  Write-Host ("Total narration: {0:N1}s ({1:N1} min). Seed {2}. Voice {3} / {4}, speed {5}." -f $total, ($total / 60), $Seed, $voiceId, $voiceModel, $Speed)
  Write-Host "Now: log the voice in voice-register.md and video.md; then scene-prompter Mode 2, then align-scenes --source api."
}
