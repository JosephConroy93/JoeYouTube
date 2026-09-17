<#
.SYNOPSIS  Render test images for a named style-bible entry with direct Gemini calls, to validate a
           farmed STYLE/NEGATIVE block against the frames it was derived from.
.USAGE     .\style-test.ps1 -Style <Name> -Out <dir> [-Prompts <file>] [-Count N]   # a prompt line ending in [Name.jpg] saves under that name and is skipped if it exists [-Model gemini-3.1-flash-image] [-Resolution 2K] [-DryRun]
           -Prompts: a text file, one content prompt per line. Default: three built-in shots
           (wide establishing / medium two-figure / close object). -Count caps how many are rendered.
.NOTES     Reads GEMINI_API_KEY from the user environment (conventions.md). Cost ~0.037 GBP per 2K image.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)] [string] $Style,
  [Parameter(Mandatory)] [string] $Out,
  [string] $Prompts = '',
  [int]    $Count = 3,
  [string] $Model = 'gemini-3.1-flash-image',
  [ValidateSet('1K','2K')] [string] $Resolution = '2K',
  [switch] $DryRun,
  [string] $Root = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if (-not $Root) { $Root = (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..\..\..\..')).Path }
$bible = Join-Path $Root 'content\styles\style-bible.md'
if (-not (Test-Path $bible)) { throw "No style bible at $bible" }

# ---- style block: the blockquote under "## <Style>" with STYLE:/NEGATIVE: markers ----
$lines = Get-Content $bible -Encoding UTF8
$start = -1
for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match "^##\s+$([regex]::Escape($Style))\s*$") { $start = $i; break } }
if ($start -lt 0) { throw "Style '$Style' not found in style-bible.md" }
$quote = @()
for ($i = $start + 1; $i -lt $lines.Count -and $lines[$i] -notmatch '^##\s'; $i++) { if ($lines[$i] -match '^>\s?(.*)$') { $quote += $Matches[1] } }
$qtext = (($quote -join ' ') -replace '\*\*', '' -replace '\s+', ' ').Trim()
if ($qtext -notmatch '^STYLE:\s*(.*?)\s*NEGATIVE:\s*(.*)$') { throw "Style '$Style': blockquote lacks STYLE:/NEGATIVE: markers" }
$styleText = $Matches[1]; $negText = $Matches[2]

# ---- universal negatives ----
$u = @(); $inU = $false
foreach ($l in $lines) {
  if ($l -match '^##\s+Universal negatives') { $inU = $true; continue }
  if ($inU -and $l -match '^##\s') { break }
  if ($inU -and $l -match '^>\s?(.*)$') { $u += $Matches[1] }
}
$universal = (($u -join ' ') -replace '\*\*', '' -replace '\s+', ' ').Trim()

# ---- prompts ----
if ($Prompts) { $promptList = @(Get-Content $Prompts -Encoding UTF8 | Where-Object { $_.Trim() }) }
else {
  $promptList = @(
    'Wide establishing shot of a small riverside settlement at dawn: low buildings, a wooden jetty, boats pulled up on the bank, mist over the water, one figure walking along the shore carrying a basket. No text.',
    'Medium shot, two adults facing each other across a rough wooden table inside a dim workshop lit by a single window; one is explaining something with a raised hand, tools and cut timber around them. Exactly two people. No text.',
    'Close-up of weathered hands holding a small bronze key over an open iron-bound chest, warm lamplight from the left, dust in the air. No faces. No text.'
  )
}
$promptList = @($promptList | Select-Object -First $Count)

New-Item -ItemType Directory -Force $Out | Out-Null
$apiKey = [System.Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User'); if (-not $apiKey) { $apiKey = $env:GEMINI_API_KEY }
if (-not $apiKey -and -not $DryRun) { throw 'GEMINI_API_KEY not set in the user environment' }
$uri = "https://generativelanguage.googleapis.com/v1beta/models/${Model}:generateContent"

$n = 0
foreach ($p in $promptList) {
  $n++
  $target = $null
  if ($p -match '^(.*?)\s*\[([^\]]+\.(?:jpg|png))\]\s*$') { $p = $Matches[1]; $target = $Matches[2] }
  $text = "$p`n`nSTYLE: $styleText`n`nNEGATIVE: $negText`n`n$universal"
  $body = @{ contents = @(@{ parts = @(@{ text = $text }) }); generationConfig = @{ responseModalities = @('TEXT','IMAGE'); imageConfig = @{ imageSize = $Resolution } } } | ConvertTo-Json -Depth 8 -Compress
  $base = if ($target) { Join-Path $Out ([IO.Path]::GetFileNameWithoutExtension($target)) } else { Join-Path $Out ('{0}-{1:D2}' -f ($Style -replace '[^A-Za-z0-9]+','-'), $n) }
  if (-not $DryRun -and $target -and ((Test-Path "$base.jpg") -or (Test-Path "$base.png"))) { Write-Host "  skip $target (exists)"; continue }
  if ($DryRun) { [IO.File]::WriteAllText("$base.request.json", $body, (New-Object Text.UTF8Encoding($false))); Write-Host "[dry-run] wrote $base.request.json ($($text.Length) chars)"; continue }
  Write-Host ("Rendering {0}/{1} with {2} @ {3}..." -f $n, $promptList.Count, $Model, $Resolution)
  $resp = Invoke-RestMethod -Method Post -Uri $uri -Headers @{ 'x-goog-api-key' = $apiKey; 'Content-Type' = 'application/json' } -Body ([Text.Encoding]::UTF8.GetBytes($body))
  $saved = $false
  $cand = if ($resp.PSObject.Properties['candidates'] -and @($resp.candidates).Count -gt 0) { $resp.candidates[0] } else { $null }
  $parts = @()
  if ($cand -and $cand.PSObject.Properties['content'] -and $cand.content.PSObject.Properties['parts']) { $parts = @($cand.content.parts) }
  if ($parts.Count -eq 0) {
    $why = if ($cand -and $cand.PSObject.Properties['finishReason']) { $cand.finishReason } else { 'no candidate' }
    $fb = if ($resp.PSObject.Properties['promptFeedback']) { ($resp.promptFeedback | ConvertTo-Json -Compress) } else { '' }
    Write-Warning "prompt $n returned no image parts (finishReason: $why $fb); response saved, continuing"
  }
  foreach ($part in $parts) {
    $inl = $null
    if ($part.PSObject.Properties['inlineData']) { $inl = $part.inlineData } elseif ($part.PSObject.Properties['inline_data']) { $inl = $part.inline_data }
    if ($inl) {
      $ext = if ($inl.mimeType -match 'png') { 'png' } else { 'jpg' }
      [IO.File]::WriteAllBytes("$base.$ext", [Convert]::FromBase64String($inl.data)); Write-Host "  saved $base.$ext"; $saved = $true
    }
  }
  if (-not $saved) { Write-Warning "no image in response for prompt $n"; ($resp | ConvertTo-Json -Depth 6) | Out-File "$base.response.json" }
}
Write-Host ("Done: {0} image(s) in {1}. Compare against the channel frames before accepting the entry." -f $n, $Out)
