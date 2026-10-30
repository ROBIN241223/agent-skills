param(
    [string]$Out = "",
    [switch]$Force
)

# Save an image currently on the Windows clipboard to a file so it can be OCR'd.
# Prints "SAVED:<path>" on success, or "NO_IMAGE_ON_CLIPBOARD" if there is none.
# Exit codes: 0 saved, 1 no image, 4 failed to save.

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$img = [System.Windows.Forms.Clipboard]::GetImage()
if ($null -eq $img) {
    Write-Output "NO_IMAGE_ON_CLIPBOARD"
    exit 1
}

if ($Out -eq "") {
    $dir = Join-Path $env:TEMP "opencode"
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $Out = Join-Path $dir ("clipboard_$stamp.png")
}
elseif ((Test-Path -LiteralPath $Out) -and (-not $Force)) {
    $base = [System.IO.Path]::GetFileNameWithoutExtension($Out)
    $ext = [System.IO.Path]::GetExtension($Out)
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $Out = [System.IO.Path]::Combine([System.IO.Path]::GetDirectoryName($Out), "${base}_$stamp$ext")
}

$parent = [System.IO.Path]::GetDirectoryName($Out)
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}

try {
    $img.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output "SAVED:$Out"
    exit 0
} catch {
    Write-Error "failed to save clipboard image: $_"
    exit 4
}
