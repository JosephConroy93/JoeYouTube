<#
.SYNOPSIS
  Screenshot one DaVinci Resolve top-level window to PNG, without rendering.

.DESCRIPTION
  UNTESTED AS WRITTEN - assembled from an in-session recipe while Resolve was
  unavailable. First run: capture once, open the PNG, confirm it is not black.

  Uses user32 PrintWindow with PW_RENDERFULLCONTENT (flag 2). Flag 0 returns
  black for GPU-accelerated windows like Resolve. Captures only the target
  window, at full resolution, whether or not it is focused or covered.

  Window handles change on every Resolve restart - this script re-finds them
  each call. Resolve's Console is a SEPARATE top-level window titled just
  "Resolve"; the main window is "DaVinci Resolve Studio - <project>".

.PARAMETER OutPath   Destination PNG. Default: %TEMP%\resolve-capture.png
.PARAMETER Title     Window title to capture: exact match first, then substring.
                     Omit for the process's main window. Use "Resolve" (exact)
                     for the Console/Lua output window.
.PARAMETER ListWindows  Print the visible windows owned by Resolve and exit.

.EXAMPLE
  .\capture-window.ps1 -OutPath C:\Users\<user>\Videos\check.png
  .\capture-window.ps1 -Title Resolve -OutPath C:\Users\<user>\Videos\console.png
  .\capture-window.ps1 -ListWindows
#>
param(
  [string]$OutPath = (Join-Path $env:TEMP "resolve-capture.png"),
  [string]$Title = "",
  [switch]$ListWindows
)

Add-Type -AssemblyName System.Drawing
if (-not ("Win32Capture" -as [type])) {
Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class Win32Capture {
  public struct RECT { public int Left, Top, Right, Bottom; }
  public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdc, uint flags);
  public static List<KeyValuePair<IntPtr,string>> Windows(uint pid) {
    var list = new List<KeyValuePair<IntPtr,string>>();
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      uint p; GetWindowThreadProcessId(h, out p);
      if (p == pid && IsWindowVisible(h)) {
        var sb = new StringBuilder(512); GetWindowText(h, sb, 512);
        list.Add(new KeyValuePair<IntPtr,string>(h, sb.ToString()));
      }
      return true;
    }, IntPtr.Zero);
    return list;
  }
}
"@
}

$proc = Get-Process | Where-Object { $_.ProcessName -like "*Resolve*" -and $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $proc) { Write-Error "No Resolve process with a main window found."; exit 1 }

$wins = [Win32Capture]::Windows([uint32]$proc.Id)
if ($ListWindows) {
  $wins | ForEach-Object { "{0}`t{1}" -f $_.Key, $_.Value }
  exit 0
}

if ($Title -eq "") {
  $hwnd = [IntPtr]$proc.MainWindowHandle
} else {
  $match = $wins | Where-Object { $_.Value -eq $Title } | Select-Object -First 1
  if (-not $match) { $match = $wins | Where-Object { $_.Value -like "*$Title*" } | Select-Object -First 1 }
  if (-not $match) { Write-Error "No Resolve window matching '$Title'. Try -ListWindows."; exit 1 }
  $hwnd = $match.Key
}

$rect = New-Object Win32Capture+RECT
[Win32Capture]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
if ($width -le 0 -or $height -le 0) { Write-Error "Window has zero size (minimised?)."; exit 1 }

$bmp = New-Object System.Drawing.Bitmap $width, $height
$gfx = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $gfx.GetHdc()
[Win32Capture]::PrintWindow($hwnd, $hdc, 2) | Out-Null   # 2 = PW_RENDERFULLCONTENT
$gfx.ReleaseHdc($hdc)
$dir = Split-Path -Parent $OutPath
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
$bmp.Save($OutPath, [System.Drawing.Imaging.ImageFormat]::Png)
$gfx.Dispose(); $bmp.Dispose()
"Saved {0} ({1}x{2})" -f $OutPath, $width, $height
