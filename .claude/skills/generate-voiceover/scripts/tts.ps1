<#
.SYNOPSIS
  ElevenLabs voiceover for one video: segment script.md, call the
  with-timestamps endpoint per segment, save MP3 + alignment JSON, normalise
  to -16 LUFS dual-mono 48 kHz WAV.

.USAGE
  .\tts.ps1 -Project watcher-pov/my-video [-Segment 3] [-DryRun] [-MaxChars 4500] [-Seed 12345]

.STATUS
  UNTESTED against the live API (no key present when written). Exercised
  only with -DryRun. First live run: one segment.

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
  [int]    $MaxChars = 4500,
  [int]    $Seed     = 0,                        # 0 = derive from slug (stable)
  [string] $Root = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
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
    if ($line -match '^\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|\s*$') { $h[$matches[1]] = $matches[2] }
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

# labels: first 3 words of the segment, kebab
$labels = @()
for ($i = 0; $i -lt $segments.Count; $i++) {
  $first = (($segments[$i] -split '\s+') | Select-Object -First 3) -join ' '
  $lab = ($first.ToLower() -replace '[^a-z0-9]+', '-').Trim('-')
  $labels += ('{0:D2}-{1}' -f ($i + 1), $lab)
}

Write-Host ("Segments: {0}  (chars: {1})" -f $segments.Count, (($segments | ForEach-Object Length) -join ', '))
for ($i = 0; $i -lt $segments.Count; $i++) {
  Set-Content -Path (Join-Path $segDir "$($labels[$i]).txt") -Value $segments[$i] -Encoding UTF8 -NoNewline
}

# ---------- generation ----------
$endpointBase = 'https://api.elevenlabs.io/v1/text-to-speech'
$todo = if ($Segment -gt 0) { @($Segment - 1) } else { 0..($segments.Count - 1) }
foreach ($i in $todo) {
  $label = $labels[$i]
  $body = @{
    text          = $segments[$i]
    model_id      = $voiceModel
    seed          = $Seed
    previous_text = $(if ($i -gt 0) { $segments[$i - 1].Substring([math]::Max(0, $segments[$i - 1].Length - 600)) } else { $null })
    next_text     = $(if ($i -lt $segments.Count - 1) { $segments[$i + 1].Substring(0, [math]::Min(600, $segments[$i + 1].Length)) } else { $null })
    voice_settings = @{ stability = 0.5; similarity_boost = 0.75; style = 0; use_speaker_boost = $true; speed = 1.0 }
  }
  $json = $body | ConvertTo-Json -Depth 5 -Compress
  $uri  = "$endpointBase/$voiceId/with-timestamps?output_format=mp3_44100_128"

  if ($DryRun) {
    $scratch = Join-Path $env:TEMP "tts-dryrun-$slug"; New-Item -ItemType Directory -Force $scratch | Out-Null
    Set-Content -Path (Join-Path $scratch "$label.request.json") -Value $json -Encoding UTF8
    Write-Host "[dry-run] $label -> $uri  ($($segments[$i].Length) chars) request written to $scratch"
    continue
  }

  Write-Host "Generating $label ($($segments[$i].Length) chars)..."
  $resp = Invoke-RestMethod -Method Post -Uri $uri -Headers @{ 'xi-api-key' = $apiKey; 'Content-Type' = 'application/json' } -Body ([Text.Encoding]::UTF8.GetBytes($json))
  if (-not $resp.audio_base64) { throw "No audio_base64 in response for $label" }
  $mp3 = Join-Path $voDir "$label.mp3"
  [IO.File]::WriteAllBytes($mp3, [Convert]::FromBase64String($resp.audio_base64))
  $resp.alignment | ConvertTo-Json -Depth 4 -Compress | Set-Content -Path (Join-Path $alignDir "$label.alignment.json") -Encoding UTF8

  # ---------- normalise ----------
  $measure = & ffmpeg -hide_banner -i $mp3 -af ebur128=peak=true -f null - 2>&1 | Out-String
  $lufs = [double]([regex]::Match($measure, 'I:\s+(-?[\d.]+) LUFS').Groups[1].Value)
  $gain = [math]::Round(-16 - $lufs, 2)
  $wav = Join-Path $normDir "$label.wav"
  & ffmpeg -hide_banner -loglevel error -y -i $mp3 -af "volume=${gain}dB,alimiter=limit=0.8414:level=disabled:attack=5:release=50" -ar 48000 -ac 2 -c:a pcm_s24le $wav
  $check = & ffmpeg -hide_banner -i $wav -af "ebur128=peak=true" -f null - 2>&1 | Out-String
  $chk = [regex]::Match($check, 'I:\s+(-?[\d.]+) LUFS').Groups[1].Value
  $tp  = [regex]::Match($check, 'Peak:\s+(-?[\d.]+) dBFS').Groups[1].Value
  $lra = [regex]::Match($check, 'LRA:\s+(-?[\d.]+) LU').Groups[1].Value
  $rms = & ffmpeg -hide_banner -i $wav -af "channelsplit=channel_layout=stereo[l][r];[l]astats=measure_overall=RMS_level:measure_perchannel=none[l2];[r]astats=measure_overall=RMS_level:measure_perchannel=none[r2];[l2][r2]amerge" -f null - 2>&1 | Select-String 'RMS level dB' | ForEach-Object { ($_ -split ':')[-1].Trim() }
  $dur = (& ffprobe -v error -show_entries format=duration -of csv=p=0 $wav)
  Write-Host ("  {0}: gain {1:+0.00;-0.00} dB -> I {2} LUFS, TP {3} dBFS, LRA {4} LU, RMS L/R {5}, {6:N1}s" -f $label, $gain, $chk, $tp, $lra, ($rms -join '/'), [double]$dur)
}

if (-not $DryRun) {
  $total = 0.0
  Get-ChildItem $normDir -Filter *.wav | Sort-Object Name | ForEach-Object { $total += [double](& ffprobe -v error -show_entries format=duration -of csv=p=0 $_.FullName) }
  Write-Host ("Total narration: {0:N1}s ({1:N1} min). Seed {2}. Voice {3} / {4}." -f $total, ($total / 60), $Seed, $voiceId, $voiceModel)
  Write-Host "Now: log the voice in voice-register.md and video.md; then scene-prompter Mode 2, then align-scenes --source api."
}
