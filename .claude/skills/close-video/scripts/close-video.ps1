<#
.SYNOPSIS  Close out a finished video: reconcile the batch log, archive disposables, print the checklist. Never deletes.
.USAGE     .\close-video.ps1 -Project watcher-pov/my-video [-DryRun] [-Step archive|log|all]
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)] [string] $Project,
  [switch] $DryRun,
  [ValidateSet('archive','log','all')] [string] $Step = 'all',
  [string] $Root = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $Root) { $Root = (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..\..\..\..')).Path }

$series, $slug = $Project -split '/', 2
if (-not $slug) { throw "Project must be <series>/<slug>" }
$videoDir  = Join-Path $Root "content\$series\$slug"
$claudeDir = Join-Path $videoDir 'claude'
$archive   = Join-Path $videoDir '_archive'
$examples  = Join-Path $Root 'content\styles\examples'
$bible     = Join-Path $Root 'content\styles\style-bible.md'
if (-not (Test-Path $videoDir)) { throw "No video folder at $videoDir" }
$tag = if ($DryRun) { '[dry-run] ' } else { '' }
$today = Get-Date -Format 'yyyy-MM-dd'

function Move-Rel([string] $src) {
  # move $src (file or dir) into _archive keeping its path relative to the video folder
  $rel  = $src.Substring($videoDir.Length).TrimStart('\')
  $dest = Join-Path $archive $rel
  $bytes = if (Test-Path $src -PathType Container) { (Get-ChildItem $src -Recurse -File | Measure-Object Length -Sum).Sum } else { (Get-Item $src).Length }
  if (-not $bytes) { $bytes = 0 }
  Write-Host ("{0}move  {1,-70} {2,10:N0} bytes" -f $tag, $rel, $bytes)
  if (-not $DryRun) {
    New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
    if (Test-Path $dest) { throw "Archive target already exists: $dest" }
    Move-Item -LiteralPath $src -Destination $dest
  }
  return [long]$bytes
}

$total = 0L; $count = 0

if ($Step -in 'archive','all') {
  Write-Host "== archive =="
  # 1. style previews: save exemplars, repoint the bible
  $previews = Join-Path $claudeDir 'style-previews'
  if (Test-Path $previews) {
    New-Item -ItemType Directory -Force $examples | Out-Null
    foreach ($dir in Get-ChildItem $previews -Directory) {
      $style = ($dir.Name -split '-scenes-')[0]
      $first = Get-ChildItem $dir.FullName -File -Include *.jpg,*.png -Recurse | Sort-Object Name | Select-Object -First 1
      $ex = Join-Path $examples "$style.jpg"
      if ($first -and -not (Test-Path $ex)) {
        Write-Host ("{0}copy  exemplar {1} -> content/styles/examples/{2}.jpg" -f $tag, $first.Name, $style)
        if (-not $DryRun) { Copy-Item $first.FullName $ex }
      }
      if (Test-Path $bible) {
        $b = Get-Content $bible -Raw -Encoding UTF8
        $pattern = [regex]::Escape("style-previews/$($dir.Name)/")
        if ($b -match $pattern) {
          Write-Host ("{0}edit  style-bible.md: links into {1} -> examples/{2}.jpg" -f $tag, $dir.Name, $style)
          if (-not $DryRun) {
            $b = [regex]::Replace($b, "\([^)]*$pattern[^)]*\)", "(examples/$style.jpg)")
            Set-Content -Path $bible -Value $b -Encoding UTF8 -NoNewline
          }
        }
      }
    }
  }
  # 2. disposables
  $targets = @(
    (Join-Path $videoDir 'scene-generation\_archive'),
    (Join-Path $videoDir 'scene-generation\failed'),
    (Join-Path $videoDir 'reference-images\_archive'),
    $previews,
    (Join-Path $claudeDir 'pipeline-pilot'),
    (Join-Path $videoDir 'hook-tests')
  )
  foreach ($t in $targets) { if (Test-Path $t) { $total += Move-Rel $t; $count++ } }
  foreach ($f in Get-ChildItem $claudeDir -File | Where-Object Name -like '*.bak*') { $total += Move-Rel $f.FullName; $count++ }
  $refDir = Join-Path $videoDir 'reference-images'
  if (Test-Path $refDir) {
    foreach ($f in Get-ChildItem $refDir -File | Where-Object { $_.Name -match '\.(failed|superseded)' }) { $total += Move-Rel $f.FullName; $count++ }
  }
  Write-Host ("{0}archived {1} items, {2:N1} MB -> {3}" -f $tag, $count, ($total / 1MB), '_archive/')
}

if ($Step -in 'log','all') {
  Write-Host "== log =="
  $log = Join-Path $claudeDir 'batch-log.md'
  if (Test-Path $log) {
    $lines = Get-Content $log -Encoding UTF8
    $fixed = 0
    for ($i = 0; $i -lt $lines.Count; $i++) {
      if ($lines[$i] -match '^\|\s*`?batches/' ) {
        $cells = $lines[$i] -split '\|'
        # status is cell 4 in the legacy 6-col shape, cell 5 in the 8-col shape (find the first cell that looks like a status word)
        for ($c = 1; $c -lt $cells.Count; $c++) {
          if ($cells[$c].Trim() -eq 'fetched') { $cells[$c] = ' validated (reconciled at close) '; $fixed++; break }
        }
        $lines[$i] = $cells -join '|'
      }
    }
    Write-Host ("{0}batch-log: {1} rows fetched -> validated (reconciled at close); append CLOSED {2}" -f $tag, $fixed, $today)
    if (-not $DryRun) { $lines += ''; $lines += "CLOSED $today"; Set-Content -Path $log -Value $lines -Encoding UTF8 }
  }
  $vm = Join-Path $videoDir 'video.md'
  if (Test-Path $vm) {
    $v = Get-Content $vm -Raw -Encoding UTF8
    if ($v -match '`published_id`\s*\|\s*\*\(unset\)\*') { Write-Warning "video.md: published_id is unset - publish before closing." }
    Write-Host ("{0}video.md: status -> closed" -f $tag)
    if (-not $DryRun) { $v = [regex]::Replace($v, '(\|\s*`status`\s*\|\s*)`[^`]*`[^|]*', '${1}`closed` '); Set-Content -Path $vm -Value $v -Encoding UTF8 -NoNewline }
  }
}

$checklist = @(
  '',
  'Manual checklist:',
  '  [ ] delete <slug>/_archive/ when sure (nothing else references it)',
  '  [ ] channel name / About copy / icon match the series',
  '  [ ] description follows the citation + "People & Sites Mentioned" pattern',
  '  [ ] title added to research/artifacts/competitor-titles-index.md (own channel section)',
  '  [ ] voice-register.md has this video''s voice and published id'
)
$checklist | ForEach-Object { Write-Host $_ }
