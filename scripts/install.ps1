<#
.SYNOPSIS
    Cài bộ skill vào thư mục skill của agent.

.PARAMETER Target
    Thư mục đích. Mặc định: $env:USERPROFILE\.agents\skills

.PARAMETER Copy
    Luôn copy thay vì tạo symlink.

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Target "$env:USERPROFILE\.config\opencode\skills"
    .\install.ps1 -Copy
#>
[CmdletBinding()]
param(
    [string]$Target = (Join-Path $env:USERPROFILE ".agents\skills"),
    [switch]$Copy
)

$ErrorActionPreference = "Stop"

# Hiển thị đúng tiếng Việt trên console Windows
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$repoRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $repoRoot "skills"

if (-not (Test-Path $source)) {
    throw "Không tìm thấy thư mục skills tại: $source"
}

New-Item -ItemType Directory -Path $Target -Force | Out-Null

$skills = Get-ChildItem $source -Directory | Sort-Object Name
Write-Host "Nguồn : $source"
Write-Host "Đích  : $Target"
Write-Host ("Skill : {0}" -f $skills.Count)
Write-Host ""

$installed = 0
$skipped = 0
$failed = 0

foreach ($skill in $skills) {
    $dest = Join-Path $Target $skill.Name

    try {
        if (Test-Path $dest) {
            $item = Get-Item $dest -Force
            if ($item.LinkType -eq "SymbolicLink") {
                # symlink cũ trỏ về repo này -> tạo lại cho chắc
                Remove-Item $dest -Force
            }
            else {
                Write-Host ("  [bỏ qua] {0} đã tồn tại và không phải symlink" -f $skill.Name) -ForegroundColor Yellow
                $skipped++
                continue
            }
        }

        if ($Copy) {
            Copy-Item $skill.FullName $dest -Recurse -Force
        }
        else {
            try {
                New-Item -ItemType SymbolicLink -Path $dest -Target $skill.FullName -ErrorAction Stop | Out-Null
            }
            catch {
                Write-Host ("  [copy]   {0} (không tạo được symlink)" -f $skill.Name) -ForegroundColor DarkGray
                Copy-Item $skill.FullName $dest -Recurse -Force
            }
        }

        Write-Host ("  [ok]     {0}" -f $skill.Name) -ForegroundColor Green
        $installed++
    }
    catch {
        Write-Host ("  [lỗi]    {0}: {1}" -f $skill.Name, $_.Exception.Message) -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host ("Hoàn tất: {0} cài đặt, {1} bỏ qua, {2} lỗi." -f $installed, $skipped, $failed)
Write-Host "Khởi động lại agent để nạp skill mới."
