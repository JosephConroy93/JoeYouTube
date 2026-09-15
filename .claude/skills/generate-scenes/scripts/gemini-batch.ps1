<#
.SYNOPSIS
  Gemini Batch API driver for scene generation: submit, status, fetch.

.DESCRIPTION
  Shared by the generate-scenes (submit), get-scenes (status, fetch) skills.
  Layouts, schemas and status words: .claude/conventions.md.

  submit  Builds one request per selected manifest row (content_prompt +
          style-bible STYLE/NEGATIVE block + universal negatives; reference
          images inlined base64 in the row's stated order; metadata.key =
          scene_id), one model per job, splits at 14 MB of request JSON, POSTs
          each job and appends a batch-log.md row at status `submitted`.
  status  One GET per `submitted` row (or -BatchId); updates checked_at, and
          marks a terminal non-success state `failed`. Never loops.
  fetch   Same GET; for a SUCCEEDED job decodes every result to
          scene-generation/<scene_id>.jpg (or .attempt-N.jpg if the file
          exists) and marks the row `fetched`.
  expand  Prints each selected row's content_prompt after prompt-block
          expansion (claude/cast.md, or a legacy claude/prompt-blocks.md).
          Posts nothing, logs nothing.

  Prompt blocks: a content_prompt token [[ID]] is replaced by that block's
  text; {ref} in the text becomes " shown in the <Nth> attached reference
  image" when the row's reference cell attaches (ID) as imageN, else nothing
  (a variant block ID.variant binds to ID's reference).
  A token at a sentence start is capitalised. The guards of every block used
  are appended as one preservation sentence, then each sentence of the
  `_closing` block on illustrated rows that the prompt does not already hold. An
  unknown token fails the row.

.PARAMETER Action      submit | status | fetch | expand
.PARAMETER Project     <series>/<slug>
.PARAMETER Chapter     chapter filename from the manifest index (e.g. chapter-03.md)
.PARAMETER SceneIds    explicit scene ids (full id or 3-digit prefix), comma-separated
.PARAMETER Model       overrides the model for every selected row
.PARAMETER Resolution  1K | 2K, overrides the resolution for every selected row
.PARAMETER BatchId     status/fetch: act on this one batch instead of every `submitted` row
.PARAMETER Notes       submit: free text for the log row's notes cell
.PARAMETER DryRun      submit: write request JSON to -OutDir, post nothing, log nothing.
                       fetch: write images to -OutDir, update no log row.
.PARAMETER OutDir      DryRun output folder (default $env:TEMP\gemini-batch\<slug>)
.PARAMETER Root        project root (default: four levels above this script)
.PARAMETER RefMaxPx    submit: downscale each reference in memory to this long edge (JPEG q90) before inlining; default 1376 (1K), 0 = as on disk

.NOTES
  Defaults: illustrated -> gemini-3.1-flash-image @ 2K; text-card ->
  gemini-3.1-flash-lite-image @ 1K. gemini-3-pro-image only via -Model.
  Inline body cap is 20 MB; jobs are split at 14 MB.
  The API key is read from the user environment (GEMINI_API_KEY) and is never
  written to disk or printed.
  Output images are saved with a .jpg name whatever mime type the API reports
  (the pipeline's canonical name is <scene_id>.jpg); the reported type is echoed.

  TEST STATUS
  - status against a real batch id via -BatchId on an older-schema log
    (report only): exercised.
  - status and fetch on an 8-column log, including the checked_at /
    fetched_at / status writes, attempt-N naming and footer preservation:
    exercised on a scratch project tree via -Root.
  - submit -DryRun on real chapters, with -Chapter and with -SceneIds alone:
    exercised (stitch, character and generated-scene references, per-model
    grouping, 14 MB split, body JSON on disk).
  - submit without -DryRun (the POST and the Add-LogRow that follows): exercised
  - a job ending FAILED / CANCELLED / EXPIRED (the `failed` branch): # UNTESTED
  - expand and prompt-block stitching: exercised on rewritten Embalmer rows.
  - -RefMaxPx 1376: blind six-scene test, identity equal to full-size references (research/artifacts/reftest-2026-09-13)
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet('submit', 'status', 'fetch', 'expand')][string]$Action,
    [Parameter(Mandatory = $true)][string]$Project,
    [string]$Chapter,
    [string[]]$SceneIds,
    [string]$Model,
    [ValidateSet('1K', '2K')][string]$Resolution,
    [string]$BatchId,
    [string]$Notes,
    [switch]$DryRun,
    [switch]$Direct,    # submit: one interactive generateContent call per row (about twice the batch price), saved and logged as fetched; use when the batch queue stalls
    [string]$OutDir,
    [string]$Root,
    [int]$RefMaxPx = 1376   # 0 sends references as they are on disk
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Web.Extensions
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
# $PSScriptRoot is unreliable in PS 5.1 param defaults; resolve once in the body.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# ---------------------------------------------------------------- constants
$ApiBase = 'https://generativelanguage.googleapis.com/v1beta'
$DefaultIllustratedModel = 'gemini-3.1-flash-image'
$DefaultIllustratedRes = '2K'
$DefaultTextCardModel = 'gemini-3.1-flash-lite-image'
$DefaultTextCardRes = '1K'
$SplitBytes = 14 * 1024 * 1024
$LogHeader = '| batch_id | scenes | model | requested_at | status | checked_at | fetched_at | notes |'
$LogColumns = @('batch_id', 'scenes', 'model', 'requested_at', 'status', 'checked_at', 'fetched_at', 'notes')

# ---------------------------------------------------------------- helpers
function Fail([string]$Message) { throw "gemini-batch: $Message" }

function Now-Utc { [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ') }

function Get-Serializer {
    $s = New-Object System.Web.Script.Serialization.JavaScriptSerializer
    $s.MaxJsonLength = [int]::MaxValue
    $s.RecursionLimit = 100
    return $s
}

function ConvertTo-JsonText($Object) { (Get-Serializer).Serialize($Object) }
function ConvertFrom-JsonText([string]$Text) { (Get-Serializer).DeserializeObject($Text) }

function Get-Key($Dict, [string]$Name) {
    if ($null -eq $Dict) { return $null }
    if ($Dict -is [System.Collections.IDictionary]) {
        # ContainsKey, not Contains: the deserializer returns Dictionary[string,object],
        # whose public Contains() overload takes a KeyValuePair in PS 5.1.
        if ($Dict.ContainsKey($Name)) { return $Dict[$Name] } else { return $null }
    }
    $p = $Dict.PSObject.Properties[$Name]
    if ($null -ne $p) { return $p.Value }
    return $null
}

function Get-ApiKey {
    $k = [System.Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')
    if ([string]::IsNullOrWhiteSpace($k)) { $k = $env:GEMINI_API_KEY }
    if ([string]::IsNullOrWhiteSpace($k)) { Fail 'GEMINI_API_KEY is not set in the user environment.' }
    return $k
}

function Invoke-Gemini([string]$Method, [string]$Url, [byte[]]$Body) {
    $headers = @{ 'x-goog-api-key' = (Get-ApiKey) }
    try {
        if ($Method -eq 'POST') {
            $r = Invoke-WebRequest -Method Post -Uri $Url -Headers $headers -Body $Body `
                -ContentType 'application/json; charset=utf-8' -UseBasicParsing -TimeoutSec 600
        } else {
            $r = Invoke-WebRequest -Method Get -Uri $Url -Headers $headers -UseBasicParsing -TimeoutSec 600
        }
    } catch [System.Net.WebException] {
        $detail = ''
        if ($null -ne $_.Exception.Response) {
            $stream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($stream)
            $detail = $reader.ReadToEnd()
            $reader.Dispose()
        }
        Fail "$Method $Url failed: $($_.Exception.Message)`n$detail"
    }
    return ConvertFrom-JsonText $r.Content
}

# ---------------------------------------------------------------- project paths
function Resolve-Project([string]$ProjectArg, [string]$RootArg) {
    if ($ProjectArg -notmatch '^([^/\\]+)[/\\]([^/\\]+)$') { Fail "-Project must be <series>/<slug>, got '$ProjectArg'." }
    $series = $Matches[1]; $slug = $Matches[2]
    if ([string]::IsNullOrWhiteSpace($RootArg)) {
        $RootArg = (Resolve-Path (Join-Path $ScriptDir '..\..\..\..')).Path
    }
    $videoDir = Join-Path $RootArg "content\$series\$slug"
    if (-not (Test-Path $videoDir)) { Fail "project folder not found: $videoDir" }
    $claude = Join-Path $videoDir 'claude'
    return [pscustomobject]@{
        Root       = $RootArg
        Series     = $series
        Slug       = $slug
        SeriesDir  = Join-Path $RootArg "content\$series"
        VideoDir   = $videoDir
        ClaudeDir  = $claude
        Index      = Join-Path $claude 'scene-prompts.md'
        ChapterDir = Join-Path $claude 'scene-prompts'
        Log        = Join-Path $claude 'batch-log.md'
        Blocks     = if (Test-Path (Join-Path $claude 'cast.md')) { Join-Path $claude 'cast.md' } else { Join-Path $claude 'prompt-blocks.md' }
        RefDir     = Join-Path $videoDir 'reference-images'
        SceneDir   = Join-Path $videoDir 'scene-generation'
        StyleBible = Join-Path $RootArg 'content\styles\style-bible.md'
    }
}

# ---------------------------------------------------------------- manifest
function Split-TableRow([string]$Line) {
    $t = $Line.Trim()
    if (-not $t.StartsWith('|')) { return $null }
    $t = $t.Substring(1)
    if ($t.EndsWith('|')) { $t = $t.Substring(0, $t.Length - 1) }
    return @($t.Split('|') | ForEach-Object { $_.Trim() })
}

function Get-ChapterFiles($P) {
    if (-not (Test-Path $P.Index)) { Fail "manifest index not found: $($P.Index)" }
    $files = New-Object System.Collections.ArrayList
    foreach ($line in Get-Content -LiteralPath $P.Index -Encoding UTF8) {
        if ($line -notmatch '^\s*\|') { continue }
        # first `<name>.md` token on the row, with or without a scene-prompts/ prefix or markdown link
        if ($line -match '(?:scene-prompts/)?([\w.-]+\.md)') {
            $f = $Matches[1]
            if (-not $files.Contains($f)) { [void]$files.Add($f) }
        }
    }
    if ($files.Count -eq 0) { Fail "no chapter files listed in the index table of $($P.Index)" }
    return @($files)
}

function Read-ChapterRows($P, [string]$File) {
    $File = ($File -replace '^.*[/\\]', '')   # accept scene-prompts/<file> or a bare filename
    $path = Join-Path $P.ChapterDir $File
    if (-not (Test-Path $path)) { Fail "chapter file not found: $path" }
    $rows = New-Object System.Collections.ArrayList
    foreach ($line in Get-Content -LiteralPath $path -Encoding UTF8) {
        $cells = Split-TableRow $line
        if ($null -eq $cells -or $cells.Count -lt 7) { continue }
        $id = ($cells[0] -replace '`', '').Trim()
        if ($id -notmatch '^\d{3}_[\w-]+$') { continue }
        [void]$rows.Add([pscustomobject]@{
            scene_id       = $id
            prefix         = $id.Substring(0, 3)
            script_bookmark = $cells[1]
            scene_type     = $cells[2].Trim()
            content_prompt = $cells[3]
            style          = ($cells[4] -replace '`', '').Trim()
            refs           = $cells[5]
            notes          = $cells[6]
            chapter        = $File
        })
    }
    return @($rows)
}

function Select-Rows($P) {
    $wantIds = @()
    if ($SceneIds) { $wantIds = @($SceneIds | ForEach-Object { $_.Split(',') } | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }
    if (-not $Chapter -and $wantIds.Count -eq 0) { Fail "$Action needs -Chapter <file> and/or -SceneIds a,b,c." }

    $files = if ($Chapter) { @($Chapter) } else { Get-ChapterFiles $P }
    $all = @()
    foreach ($f in $files) {
        # an index-derived list includes planned chapters, which have no file yet
        if (-not $Chapter -and -not (Test-Path (Join-Path $P.ChapterDir ($f -replace '^.*[/\\]', '')))) { continue }
        $all += @(Read-ChapterRows $P $f | Where-Object { $_ })
    }

    if ($wantIds.Count -eq 0) { return $all }
    $picked = New-Object System.Collections.ArrayList
    foreach ($w in $wantIds) {
        $m = @($all | Where-Object { $_.scene_id -eq $w -or $_.prefix -eq $w })
        if ($m.Count -ne 1) { Fail "scene id '$w' matched $($m.Count) manifest rows (need exactly 1)." }
        [void]$picked.Add($m[0])
    }
    return @($picked)
}

# ---------------------------------------------------------------- style bible
function Get-SectionQuote([string[]]$Lines, [string]$Heading) {
    $inSection = $false; $quote = New-Object System.Collections.ArrayList; $started = $false
    foreach ($l in $Lines) {
        if ($l -match '^##\s+(.+?)\s*$') {
            if ($inSection) { break }
            if ($Matches[1] -like "$Heading*") { $inSection = $true }
            continue
        }
        if (-not $inSection) { continue }
        if ($l -match '^\s*>\s?(.*)$') { $started = $true; [void]$quote.Add($Matches[1]) }
        elseif ($started -and $quote.Count -gt 0) { break }
    }
    if ($quote.Count -eq 0) { Fail "style bible: no blockquote found under heading '$Heading'." }
    $text = (($quote | Where-Object { $_.Trim() -ne '' }) -join ' ') -replace '\*\*', ''
    return ($text -replace '\s+', ' ').Trim()
}

function Get-StyleText($P) {
    $lines = Get-Content -LiteralPath $P.StyleBible -Encoding UTF8
    $universal = Get-SectionQuote $lines 'Universal negatives'
    $cache = @{}
    return [pscustomobject]@{ Lines = $lines; Universal = $universal; Cache = $cache }
}

function Get-StyleBlock($Bible, [string]$Name) {
    if ($Bible.Cache.ContainsKey($Name)) { return $Bible.Cache[$Name] }
    $q = Get-SectionQuote $Bible.Lines $Name
    if ($q -notmatch '^STYLE:\s*(.*?)\s*NEGATIVE:\s*(.*)$') { Fail "style '$Name': blockquote lacks STYLE:/NEGATIVE: markers." }
    $block = [pscustomobject]@{ Style = $Matches[1]; Negative = $Matches[2] }
    $Bible.Cache[$Name] = $block
    return $block
}

# ---------------------------------------------------------------- prompt blocks
$Ordinals = @('', 'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth')

function Read-PromptBlocks($P) {
    $blocks = @{}
    if (-not (Test-Path $P.Blocks)) { return $blocks }
    foreach ($line in Get-Content -LiteralPath $P.Blocks -Encoding UTF8) {
        $c = Split-TableRow $line
        if ($null -eq $c -or $c.Count -lt 2) { continue }
        $id = ($c[0] -replace '`', '').Trim()
        if ($id -notmatch '^[A-Za-z_][\w.-]*$' -or $id -eq 'block') { continue }
        $guard = if ($c.Count -ge 3) { $c[2].Trim() } else { '' }
        $blocks[$id] = [pscustomobject]@{ Text = $c[1].Trim(); Guard = $guard }
    }
    return $blocks
}

function Expand-Prompt($Blocks, $Row) {
    $text = $Row.content_prompt.Trim()
    $pos = @{}
    foreach ($e in [regex]::Matches([string]$Row.refs, 'image(\d+)\s*=\s*[^;(]*\(([^)]+)\)')) { $pos[$e.Groups[2].Value.Trim()] = [int]$e.Groups[1].Value }
    $guards = New-Object System.Collections.ArrayList
    $attached = $false
    $sb = New-Object System.Text.StringBuilder
    $last = 0
    foreach ($m in [regex]::Matches($text, '\[\[([A-Za-z_][\w.-]*)\]\]')) {
        $id = $m.Groups[1].Value
        if (-not $Blocks.ContainsKey($id)) { Fail "row $($Row.scene_id): prompt block [[$id]] is not defined in prompt-blocks.md." }
        $b = $Blocks[$id]
        $refId = $id -replace '\..*$', ''   # a variant block ID.variant binds to ID's reference
        $ref = if ($pos.ContainsKey($refId)) { $attached = $true; " shown in the $($Ordinals[$pos[$refId]]) attached reference image" } else { '' }
        $piece = $b.Text.Replace('{ref}', $ref)
        $before = $text.Substring(0, $m.Index)
        if ($before.Trim() -eq '' -or $before -match '[.!?]\s+$') { $piece = $piece.Substring(0, 1).ToUpper() + $piece.Substring(1) }
        [void]$sb.Append($text.Substring($last, $m.Index - $last)).Append($piece)
        $last = $m.Index + $m.Length
        if ($b.Guard -and -not $guards.Contains($b.Guard)) { [void]$guards.Add($b.Guard) }
    }
    [void]$sb.Append($text.Substring($last))
    $out = $sb.ToString().Trim()
    if ($guards.Count -gt 0) {
        $lead = if ($attached) { "Preserve every attached reference image's exact colouring and locked attributes" } else { 'Keep these locked attributes exactly' }
        $out += " ${lead}: $($guards -join '; '). Do not reinterpret, recolour, invent or substitute any of them."
    }
    if ($Row.scene_type -eq 'illustrated' -and $Blocks.ContainsKey('_closing')) {
        # sentence by sentence, so a row already carrying part of the closing gains only the rest
        foreach ($sentence in [regex]::Split($Blocks['_closing'].Text, '(?<=[.!?])\s+')) {
            if ($sentence -and -not $out.Contains($sentence)) { $out += " $sentence" }
        }
    }
    return $out
}

# ---------------------------------------------------------------- reference images
function Find-CanonicalScene($P, [string]$Prefix) {
    $m = @(Get-ChildItem -LiteralPath $P.SceneDir -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "^${Prefix}_[^.]+\.(jpg|jpeg|png)$" })
    if ($m.Count -ne 1) { Fail "reference to generated scene $Prefix matched $($m.Count) canonical files in scene-generation/." }
    return $m[0].FullName
}

function Resolve-References($P, [string]$Cell) {
    $out = New-Object System.Collections.ArrayList
    if ($Cell -match '^\s*\*?\(none') { return @() }
    $entries = [regex]::Matches($Cell, 'image(\d+)\s*=\s*([^;]+)')
    $sorted = @($entries | Sort-Object { [int]$_.Groups[1].Value })
    $expect = 1
    foreach ($e in $sorted) {
        $n = [int]$e.Groups[1].Value
        if ($n -ne $expect) { Fail "reference cell numbering is not contiguous (expected image$expect): '$Cell'" }
        $expect++
        $text = $e.Groups[2].Value.Trim()
        $path = $null
        if ($text -match '\(\s*(?:re)?generated scene\s+(\d{3})') { $path = Find-CanonicalScene $P $Matches[1] }
        elseif ($text -match '^(\d{3})_[\w-]+') { $path = Find-CanonicalScene $P $Matches[1] }
        elseif ($text -match '^([A-Za-z][\w.-]*(?:[/\\][\w.-]+)+)') {
            $rel = $Matches[1]
            $path = Join-Path $P.SeriesDir $rel
            if (-not (Test-Path $path)) { $path = Join-Path $P.Root $rel }
        }
        elseif ($text -match '^([A-Za-z][\w-]*)') {
            $name = $Matches[1]
            foreach ($ext in @('.jpg', '.jpeg', '.png')) {
                $cand = Join-Path $P.RefDir ($name + $ext)
                if (Test-Path $cand) { $path = $cand; break }
            }
            if ($null -eq $path) { $path = Join-Path $P.RefDir ($name + '.jpg') }
        }
        else { Fail "cannot parse reference entry '$text'." }
        if (-not (Test-Path $path)) { Fail "reference image not found for entry '$text': $path" }
        [void]$out.Add($path)
    }
    return @($out)
}

function Get-ReferenceBytes([string]$Path) {
    if (-not $RefMaxPx) { return , [IO.File]::ReadAllBytes($Path) }
    Add-Type -AssemblyName System.Drawing
    $img = [System.Drawing.Image]::FromFile($Path)
    try {
        $long = [Math]::Max($img.Width, $img.Height)
        if ($long -le $RefMaxPx) { return , [IO.File]::ReadAllBytes($Path) }
        $w = [int][Math]::Round($img.Width * $RefMaxPx / $long); $h = [int][Math]::Round($img.Height * $RefMaxPx / $long)
        $bmp = New-Object System.Drawing.Bitmap($w, $h)
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $g.DrawImage($img, 0, 0, $w, $h)
        $g.Dispose()
        $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
        $ep = New-Object System.Drawing.Imaging.EncoderParameters(1)
        $ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]90)
        $ms = New-Object IO.MemoryStream
        $bmp.Save($ms, $codec, $ep)
        $bmp.Dispose()
        return , $ms.ToArray()
    } finally { $img.Dispose() }
}

function Get-MimeType([string]$Path) {
    if ($RefMaxPx) { return 'image/jpeg' }
    switch ([IO.Path]::GetExtension($Path).ToLower()) {
        '.png' { 'image/png' }
        default { 'image/jpeg' }
    }
}

# ---------------------------------------------------------------- batch log
function Read-Log($P) {
    if (-not (Test-Path $P.Log)) { return $null }
    $lines = @(Get-Content -LiteralPath $P.Log -Encoding UTF8)
    $headerIdx = -1; $columns = @()
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $c = Split-TableRow $lines[$i]
        if ($null -ne $c -and $c[0] -eq 'batch_id') { $headerIdx = $i; $columns = $c; break }
    }
    if ($headerIdx -lt 0) { Fail "batch-log.md has no header row starting with '| batch_id |': $($P.Log)" }
    $rows = New-Object System.Collections.ArrayList
    for ($i = $headerIdx + 2; $i -lt $lines.Count; $i++) {
        $c = Split-TableRow $lines[$i]
        if ($null -eq $c -or $c.Count -lt $columns.Count) { continue }
        $cells = @{}
        for ($k = 0; $k -lt $columns.Count; $k++) { $cells[$columns[$k]] = $c[$k] }
        $cells['batch_id'] = ($cells['batch_id'] -replace '`', '').Trim()
        [void]$rows.Add([pscustomobject]@{ Line = $i; Cells = $cells })
    }
    $isCurrent = ($columns -join '|') -eq ($LogColumns -join '|')
    return [pscustomobject]@{ Lines = $lines; HeaderIndex = $headerIdx; Columns = $columns; Rows = @($rows); IsCurrentSchema = $isCurrent }
}

function Write-LogRowUpdate($P, $Log, $Row) {
    $vals = foreach ($c in $Log.Columns) {
        $v = [string]$Row.Cells[$c]
        if ($c -eq 'batch_id') { "``$v``" } else { $v -replace '\|', '/' }
    }
    $Log.Lines[$Row.Line] = '| ' + ($vals -join ' | ') + ' |'
    Set-Content -LiteralPath $P.Log -Value $Log.Lines -Encoding UTF8
}

function Add-LogRow($P, [hashtable]$Cells) {
    if (-not (Test-Path $P.Log)) {
        $pre = @("# Batch log", '', "Schema: ``.claude/conventions.md`` (batch-log.md). Written by ``gemini-batch.ps1``.", '', $LogHeader, '|---|---|---|---|---|---|---|---|')
        Set-Content -LiteralPath $P.Log -Value $pre -Encoding UTF8
    }
    $log = Read-Log $P
    if (-not $log.IsCurrentSchema) { Fail "batch-log.md uses an older column set; new rows need the 8-column schema in conventions.md (start a new log for this video)." }
    $vals = foreach ($c in $LogColumns) {
        $v = [string]$Cells[$c]
        if ($c -eq 'batch_id') { "``$v``" } else { $v -replace '\|', '/' }
    }
    $line = '| ' + ($vals -join ' | ') + ' |'
    # insert after the last table row so footer lines (FINALIZED/CLOSED) stay last
    $insertAt = $log.HeaderIndex + 2
    if ($log.Rows.Count -gt 0) { $insertAt = $log.Rows[-1].Line + 1 }
    $new = New-Object System.Collections.ArrayList
    for ($i = 0; $i -lt $log.Lines.Count; $i++) {
        if ($i -eq $insertAt) { [void]$new.Add($line) }
        [void]$new.Add($log.Lines[$i])
    }
    if ($insertAt -ge $log.Lines.Count) { [void]$new.Add($line) }
    Set-Content -LiteralPath $P.Log -Value $new -Encoding UTF8
}

function Format-SceneRange([string[]]$Prefixes) {
    $nums = @($Prefixes | ForEach-Object { [int]$_ } | Sort-Object)
    if ($nums.Count -eq 1) { return $Prefixes[0] }
    $contiguous = $true
    for ($i = 1; $i -lt $nums.Count; $i++) { if ($nums[$i] -ne $nums[$i - 1] + 1) { $contiguous = $false; break } }
    if ($contiguous) { return ('{0:000}-{1:000}' -f $nums[0], $nums[-1]) }
    return (($nums | ForEach-Object { '{0:000}' -f $_ }) -join ',')
}

# ---------------------------------------------------------------- submit
function Invoke-Submit($P) {
    $rows = @(Select-Rows $P | Where-Object { $_ })
    if ($rows.Count -eq 0) { Fail 'no manifest rows selected.' }
    $bible = Get-StyleText $P
    $blocks = Read-PromptBlocks $P

    # one model/resolution per row; group rows into jobs by that pair
    $groups = [ordered]@{}
    foreach ($r in $rows) {
        if ([string]::IsNullOrWhiteSpace($r.style)) { Fail "row $($r.scene_id) has an empty style column; stop and ask the operator which style to use." }
        if ([string]::IsNullOrWhiteSpace($r.content_prompt)) { Fail "row $($r.scene_id) has no content_prompt (chapter still at beats); write the prompts first." }
        if ($r.scene_type -notin @('illustrated', 'text-card')) { Fail "row $($r.scene_id): scene_type '$($r.scene_type)' is not illustrated|text-card." }
        $m = if ($Model) { $Model } elseif ($r.scene_type -eq 'text-card') { $DefaultTextCardModel } else { $DefaultIllustratedModel }
        $res = if ($Resolution) { $Resolution } elseif ($r.scene_type -eq 'text-card') { $DefaultTextCardRes } else { $DefaultIllustratedRes }
        $key = "$m|$res"
        if (-not $groups.Contains($key)) { $groups[$key] = New-Object System.Collections.ArrayList }
        [void]$groups[$key].Add($r)
    }

    $chapters = @($rows | ForEach-Object { $_.chapter } | Select-Object -Unique)
    $outDir = if ($OutDir) { $OutDir } else { Join-Path $env:TEMP "gemini-batch\$($P.Slug)" }
    if ($DryRun -and -not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

    foreach ($key in $groups.Keys) {
        $m, $res = $key.Split('|')
        $items = New-Object System.Collections.ArrayList   # {Json, Size, Row}
        foreach ($r in $groups[$key]) {
            $sb = Get-StyleBlock $bible $r.style
            $text = "$(Expand-Prompt $blocks $r) STYLE: $($sb.Style) NEGATIVE: $($sb.Negative) $($bible.Universal)"
            $parts = New-Object System.Collections.ArrayList
            [void]$parts.Add(@{ text = $text })
            $refPaths = @()
            if ($r.scene_type -ne 'text-card') { $refPaths = @(Resolve-References $P $r.refs | Where-Object { $_ }) }
            foreach ($rp in $refPaths) {
                $b64 = [Convert]::ToBase64String((Get-ReferenceBytes $rp))
                [void]$parts.Add(@{ inline_data = @{ mime_type = (Get-MimeType $rp); data = $b64 } })
            }
            $request = @{
                contents = @(@{ parts = @($parts) })
                generationConfig = @{ responseModalities = @('TEXT', 'IMAGE'); imageConfig = @{ imageSize = $res } }
            }
            $entry = @{ request = $request; metadata = @{ key = $r.scene_id } }
            $json = ConvertTo-JsonText $entry
            $size = [Text.Encoding]::UTF8.GetByteCount($json)
            if ($size -gt $SplitBytes) { Fail "request for $($r.scene_id) alone is $([math]::Round($size/1MB,1)) MB (> 14 MB); shrink its reference images first." }
            [void]$items.Add([pscustomobject]@{ Json = $json; Size = $size; Row = $r; Refs = $refPaths.Count; Request = $request })
        }

        if ($Direct -and -not $DryRun) {
            if (-not (Test-Path $P.SceneDir)) { New-Item -ItemType Directory -Path $P.SceneDir | Out-Null }
            $saved = 0; $errors = New-Object System.Collections.ArrayList
            foreach ($it in $items) {
                $sid = $it.Row.scene_id
                $bytes = [Text.Encoding]::UTF8.GetBytes((ConvertTo-JsonText $it.Request))
                $resp = $null
                for ($try = 1; $try -le 3 -and $null -eq $resp; $try++) {
                    try { $resp = Invoke-Gemini 'POST' "$ApiBase/models/${m}:generateContent" $bytes }
                    catch { if ($try -lt 3 -and "$_" -match '429|500|502|503|504|timed out') { Write-Output "  RETRY  $sid  ($try)"; Start-Sleep -Seconds 30 } else { [void]$errors.Add("$sid ($($_.ToString().Split("`n")[0]))"); Write-Output "  NO-IMAGE  $sid  request failed"; break } }
                }
                if ($null -eq $resp) { continue }
                $img = Get-ImagePart @{ response = $resp }
                if ($null -eq $img) { [void]$errors.Add("$sid (no image part in response)"); Write-Output "  NO-IMAGE  $sid  no image part in response"; continue }
                $target = Get-TargetFileName $P.SceneDir $sid
                [IO.File]::WriteAllBytes($target, [Convert]::FromBase64String([string](Get-Key $img 'data')))
                $saved++
                Write-Output "  SAVED  $sid  -> $target"
            }
            $range = Format-SceneRange @($items | ForEach-Object { $_.Row.prefix })
            $styles = (@($items | ForEach-Object { $_.Row.style } | Select-Object -Unique) -join ',')
            $noteText = "$res; $styles; direct generateContent"
            if ($errors.Count -gt 0) { $noteText += "; no image for: " + ($errors -join ', ') }
            if ($Notes) { $noteText += "; $Notes" }
            Add-LogRow $P @{
                batch_id = 'direct'; scenes = "$($chapters -join ',') $range"; model = $m
                requested_at = (Now-Utc); status = 'fetched'; checked_at = ''; fetched_at = (Now-Utc); notes = $noteText
            }
            Write-Output "DIRECT  model=$m res=$res saved=$saved missing=$($errors.Count)"
            continue
        }

        # split into chunks of <= 14 MB
        $chunks = New-Object System.Collections.ArrayList
        $cur = New-Object System.Collections.ArrayList; $curSize = 0
        foreach ($it in $items) {
            if ($cur.Count -gt 0 -and ($curSize + $it.Size) -gt $SplitBytes) { [void]$chunks.Add(@($cur)); $cur = New-Object System.Collections.ArrayList; $curSize = 0 }
            [void]$cur.Add($it); $curSize += $it.Size
        }
        if ($cur.Count -gt 0) { [void]$chunks.Add(@($cur)) }

        $part = 0
        foreach ($chunk in $chunks) {
            $part++
            $prefixes = @($chunk | ForEach-Object { $_.Row.prefix })
            $range = Format-SceneRange $prefixes
            $chapterTag = (($chapters | ForEach-Object { [IO.Path]::GetFileNameWithoutExtension($_) }) -join '+')
            $display = "$($P.Slug)-$chapterTag-$($range -replace ',', '+')"
            if ($chunks.Count -gt 1) { $display += "-part$part" }
            $body = '{"batch":{"display_name":' + (ConvertTo-JsonText $display) + ',"input_config":{"requests":{"requests":[' + (($chunk | ForEach-Object { $_.Json }) -join ',') + ']}}}}'
            $bytes = [Text.Encoding]::UTF8.GetBytes($body)
            $mb = [math]::Round($bytes.Length / 1MB, 2)
            $styles = (@($chunk | ForEach-Object { $_.Row.style } | Select-Object -Unique) -join ',')
            $summary = "$display  model=$m res=$res requests=$($chunk.Count) refs=$(($chunk | Measure-Object -Property Refs -Sum).Sum) body=${mb}MB scenes=$(($chunk | ForEach-Object { $_.Row.scene_id }) -join ',')"

            if ($DryRun) {
                $outFile = Join-Path $outDir "$display.json"
                [IO.File]::WriteAllBytes($outFile, $bytes)
                Write-Output "DRYRUN  $summary"
                Write-Output "        -> $outFile"
                continue
            }

            $resp = Invoke-Gemini 'POST' "$ApiBase/models/${m}:batchGenerateContent" $bytes
            $name = [string](Get-Key $resp 'name')
            if ([string]::IsNullOrWhiteSpace($name)) { Fail "submit response carried no 'name': $(ConvertTo-JsonText $resp)" }
            $noteText = "$res; $styles"
            if ($chunks.Count -gt 1) { $noteText += "; part $part/$($chunks.Count)" }
            if ($Notes) { $noteText += "; $Notes" }
            Add-LogRow $P @{
                batch_id = $name; scenes = "$($chapters -join ',') $range"; model = $m
                requested_at = (Now-Utc); status = 'submitted'; checked_at = ''; fetched_at = ''; notes = $noteText
            }
            Write-Output "SUBMITTED  $name  $summary"
        }
    }
}

# ---------------------------------------------------------------- expand
function Invoke-Expand($P) {
    $rows = @(Select-Rows $P | Where-Object { $_ })
    if ($rows.Count -eq 0) { Fail 'no manifest rows selected.' }
    $blocks = Read-PromptBlocks $P
    foreach ($r in $rows) {
        Write-Output "=== $($r.scene_id)  [$($r.refs)]"
        Write-Output (Expand-Prompt $blocks $r)
    }
}

# ---------------------------------------------------------------- status / fetch
function Get-BatchState($Resp) {
    $meta = Get-Key $Resp 'metadata'
    $s = Get-Key $meta 'state'
    if ([string]::IsNullOrWhiteSpace([string]$s)) { $s = Get-Key $Resp 'state' }
    return [string]$s
}

function Get-TargetRows($P) {
    $log = Read-Log $P
    if ($BatchId) {
        $row = $null
        if ($null -ne $log) { $row = @($log.Rows | Where-Object { $_.Cells['batch_id'] -eq $BatchId }) | Select-Object -First 1 }
        if ($null -eq $row) {
            Write-Warning "batch $BatchId is not a row in $($P.Log); reporting only, no log update."
            $row = [pscustomobject]@{ Line = -1; Cells = @{ batch_id = $BatchId; status = 'submitted' } }
        } elseif (-not $log.IsCurrentSchema) {
            Write-Warning "batch-log.md predates the 8-column schema; reporting only, no log update."
            $row = [pscustomobject]@{ Line = -1; Cells = $row.Cells }
        }
        return [pscustomobject]@{ Log = $log; Rows = @($row) }
    }
    if ($null -eq $log) { Fail "no batch-log.md at $($P.Log)." }
    if (-not $log.IsCurrentSchema) { Fail 'batch-log.md predates the 8-column schema; pass -BatchId to check one batch without updating the log.' }
    $pending = @($log.Rows | Where-Object { $_.Cells['status'] -eq 'submitted' })
    return [pscustomobject]@{ Log = $log; Rows = $pending }
}

function Save-Row($P, $Log, $Row) {
    if ($Row.Line -lt 0 -or $DryRun) { return }
    Write-LogRowUpdate $P $Log $Row
}

function Get-ResultItems($Resp) {
    $r = Get-Key $Resp 'response'
    $outer = Get-Key $r 'inlinedResponses'
    $inner = Get-Key $outer 'inlinedResponses'
    if ($null -eq $inner) { return @() }
    return @($inner)
}

function Get-ImagePart($Item) {
    $resp = Get-Key $Item 'response'
    $cands = Get-Key $resp 'candidates'
    if ($null -eq $cands) { return $null }
    foreach ($c in @($cands)) {
        $content = Get-Key $c 'content'
        $parts = Get-Key $content 'parts'
        if ($null -eq $parts) { continue }
        foreach ($p in @($parts)) {
            $d = Get-Key $p 'inlineData'
            if ($null -eq $d) { $d = Get-Key $p 'inline_data' }
            if ($null -ne $d) { return $d }
        }
    }
    return $null
}

function Get-TargetFileName([string]$Dir, [string]$SceneId) {
    $canon = Join-Path $Dir "$SceneId.jpg"
    if (-not (Test-Path $canon)) { return $canon }
    $n = 2
    $existing = @(Get-ChildItem -LiteralPath $Dir -File | Where-Object { $_.Name -match "^$([regex]::Escape($SceneId))\.attempt-(\d+)\.jpg$" } |
        ForEach-Object { [int]([regex]::Match($_.Name, 'attempt-(\d+)').Groups[1].Value) })
    if ($existing.Count -gt 0) { $n = ($existing | Measure-Object -Maximum).Maximum + 1 }
    return (Join-Path $Dir "$SceneId.attempt-$n.jpg")
}

function Invoke-StatusOrFetch($P, [bool]$DoFetch) {
    $t = Get-TargetRows $P
    if ($t.Rows.Count -eq 0) { Write-Output 'NOTHING PENDING  no rows at status submitted.'; return }
    $sceneDir =if ($DoFetch -and $DryRun) { if ($OutDir) { $OutDir } else { Join-Path $env:TEMP "gemini-batch\$($P.Slug)\fetched" } } else { $P.SceneDir }
    if ($DoFetch -and -not (Test-Path $sceneDir)) { New-Item -ItemType Directory -Path $sceneDir | Out-Null }

    foreach ($row in $t.Rows) {
        $id = $row.Cells['batch_id']
        if ($id -notmatch '^batches/') { Write-Output "SKIP  $id  not an API batch id"; continue }
        $resp = Invoke-Gemini 'GET' "$ApiBase/$id" $null
        $state = Get-BatchState $resp
        $row.Cells['checked_at'] = Now-Utc

        switch ($state) {
            'BATCH_STATE_SUCCEEDED' {
                $items = Get-ResultItems $resp
                if (-not $DoFetch) {
                    Write-Output "READY  $id  $state  results=$($items.Count)  -> run -Action fetch"
                    Save-Row $P $t.Log $row
                    break
                }
                $saved = 0; $errors = New-Object System.Collections.ArrayList
                foreach ($it in $items) {
                    $key = [string](Get-Key (Get-Key $it 'metadata') 'key')
                    $err = Get-Key $it 'error'
                    $img = Get-ImagePart $it
                    if ($null -ne $err -or $null -eq $img) {
                        $why = if ($null -ne $err) { ConvertTo-JsonText $err } else { 'no image part in response' }
                        [void]$errors.Add("$key ($why)")
                        Write-Output "  NO-IMAGE  $key  $why"
                        continue
                    }
                    $target = Get-TargetFileName $sceneDir $key
                    [IO.File]::WriteAllBytes($target, [Convert]::FromBase64String([string](Get-Key $img 'data')))
                    $saved++
                    Write-Output "  SAVED  $key  $([string](Get-Key $img 'mimeType'))  -> $target"
                }
                $row.Cells['status'] = 'fetched'
                $row.Cells['fetched_at'] = Now-Utc
                if ($errors.Count -gt 0) { $row.Cells['notes'] = ([string]$row.Cells['notes'] + "; no image for: " + ($errors -join ', ')).TrimStart('; ') }
                Save-Row $P $t.Log $row
                Write-Output "FETCHED  $id  saved=$saved  missing=$($errors.Count)"
            }
            { $_ -in @('BATCH_STATE_PENDING', 'BATCH_STATE_RUNNING', '') } {
                Write-Output "PENDING  $id  $state"
                Save-Row $P $t.Log $row
            }
            default {
                $row.Cells['status'] = 'failed'
                $errText = ConvertTo-JsonText (Get-Key $resp 'error')
                $row.Cells['notes'] = ([string]$row.Cells['notes'] + "; $state $errText").TrimStart('; ')
                Save-Row $P $t.Log $row
                Write-Output "FAILED  $id  $state  $errText"
            }
        }
    }
}

# ---------------------------------------------------------------- main
$P = Resolve-Project $Project $Root
switch ($Action) {
    'submit' { Invoke-Submit $P }
    'status' { Invoke-StatusOrFetch $P $false }
    'fetch'  { Invoke-StatusOrFetch $P $true }
    'expand' { Invoke-Expand $P }
}
