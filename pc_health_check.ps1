#requires -Version 5.1
<#
    电脑一键体检脚本（只读检查，不修改任何系统设置）
    用法：双击同目录下的「电脑一键体检.bat」，或右键“使用 PowerShell 运行”
#>

$ErrorActionPreference = 'SilentlyContinue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { $Host.UI.RawUI.WindowTitle = '电脑一键体检' } catch {}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
$desktop = [Environment]::GetFolderPath('Desktop')
if (-not $desktop) { $desktop = $scriptDir }
$stamp  = Get-Date -Format 'yyyyMMdd_HHmmss'
$report = Join-Path $desktop ("电脑体检报告_" + $stamp + ".txt")

$issues = New-Object System.Collections.ArrayList

function Write-Title([string]$text) {
    Write-Host ''
    Write-Host ('=' * 62) -ForegroundColor DarkCyan
    Write-Host ('  ' + $text) -ForegroundColor Cyan
    Write-Host ('=' * 62) -ForegroundColor DarkCyan
}
function Write-OK([string]$t)   { Write-Host ('  [正常] ' + $t) -ForegroundColor Green }
function Write-Note([string]$t) { Write-Host ('  [注意] ' + $t) -ForegroundColor Yellow; [void]$issues.Add($t) }
function Write-Bad([string]$t)  { Write-Host ('  [异常] ' + $t) -ForegroundColor Red;    [void]$issues.Add($t) }
function Show-Table($data) {
    $s = $data | Format-Table -AutoSize | Out-String -Width 220
    Write-Host $s.TrimEnd()
}

try { Start-Transcript -Path $report -Force | Out-Null } catch {}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# ---------------------------------------------------------------- 头部
Write-Title '电脑一键体检'
Write-Host ('  检查时间 ：' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
if ($isAdmin) {
    Write-Host '  运行权限 ：管理员（硬件信息完整）' -ForegroundColor Green
} else {
    Write-Host '  运行权限 ：普通用户（部分硬盘健康信息可能缺失，建议右键“以管理员身份运行”）' -ForegroundColor Yellow
    [void]$issues.Add('未以管理员身份运行，硬盘 SMART 等健康信息可能不完整')
}

# ---------------------------------------------------------------- 一、系统概要
Write-Title '一、系统与硬件概要'
$os  = Get-CimInstance Win32_OperatingSystem
$cs  = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$cpuName = if ($cpu -and $cpu.Name) { $cpu.Name.Trim() } else { '未知' }
$gpuNames = @(Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name })
$cores = if ($cpu.NumberOfCores) { $cpu.NumberOfCores } else { '?' }
$threads = if ($cpu.NumberOfLogicalProcessors) { $cpu.NumberOfLogicalProcessors } else { '?' }

Write-Host ('  操作系统 ：' + $os.Caption + '  ' + $os.Version + '（Build ' + $os.BuildNumber + '）')
Write-Host ('  设备名称 ：' + $cs.Name + '   ' + $cs.Manufacturer + ' ' + $cs.Model)
Write-Host ('  处理器   ：' + $cpuName + '（' + $cores + ' 核 / ' + $threads + ' 线程）')
Write-Host ('  显卡     ：' + ($gpuNames -join ' / '))
Write-Host ('  内存总量 ：' + [math]::Round($cs.TotalPhysicalMemory / 1GB, 1) + ' GB')
Write-Host ('  上次开机 ：' + $os.LastBootUpTime.ToString('yyyy-MM-dd HH:mm:ss'))
$up = (Get-Date) - $os.LastBootUpTime
Write-Host ('  已运行   ：' + $up.Days + ' 天 ' + $up.Hours + ' 小时 ' + $up.Minutes + ' 分钟')
if ($up.TotalDays -ge 7) {
    Write-Note ('系统已连续运行 ' + [math]::Round($up.TotalDays, 0) + ' 天，建议重启一次以释放内存、清理临时状态')
}

# ---------------------------------------------------------------- 二、CPU 与内存
Write-Title '二、CPU 与内存'
$cpuLoad = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
Write-Host ('  CPU 占用 ：' + $cpuLoad + ' %')
if ($null -ne $cpuLoad) {
    if ($cpuLoad -ge 85) { Write-Bad ('CPU 占用 ' + $cpuLoad + '%，接近满载，请查看下方占用最高的进程') }
    elseif ($cpuLoad -ge 60) { Write-Note ('CPU 占用 ' + $cpuLoad + '%，偏高') }
    else { Write-OK ('CPU 占用 ' + $cpuLoad + '%') }
}

$totalMB = [math]::Round($os.TotalVisibleMemorySize / 1KB, 0)
$freeMB  = [math]::Round($os.FreePhysicalMemory / 1KB, 0)
$usedMB  = $totalMB - $freeMB
$usedPct = if ($totalMB -gt 0) { [math]::Round($usedMB / $totalMB * 100, 1) } else { 0 }
Write-Host ('  内存使用 ：共 ' + $totalMB + ' MB，已用 ' + $usedMB + ' MB，可用 ' + $freeMB + ' MB（占用 ' + $usedPct + '%）')
if ($usedPct -ge 85) { Write-Bad ('内存占用 ' + $usedPct + '%，会频繁使用虚拟内存导致卡顿，建议关闭后台程序或加内存条') }
elseif ($usedPct -ge 70) { Write-Note ('内存占用 ' + $usedPct + '%，偏高') }
else { Write-OK ('内存占用 ' + $usedPct + '%') }

# ---------------------------------------------------------------- 三、磁盘
Write-Title '三、磁盘空间与健康'
$vols = @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3')
if ($vols.Count -eq 0) { Write-Host '  未检测到本地磁盘' }
foreach ($v in $vols) {
    $sizeGB  = [math]::Round($v.Size / 1GB, 1)
    $freeGB  = [math]::Round($v.FreeSpace / 1GB, 1)
    $freePct = if ($v.Size -gt 0) { [math]::Round($v.FreeSpace / $v.Size * 100, 1) } else { 0 }
    Write-Host ('  ' + $v.DeviceID + ' 总 ' + $sizeGB + ' GB / 剩余 ' + $freeGB + ' GB（' + $freePct + '%）')
    if ($freePct -lt 10) { Write-Bad ($v.DeviceID + ' 剩余空间不足 10%，会明显拖慢系统，请立即清理') }
    elseif ($freePct -lt 20) { Write-Note ($v.DeviceID + ' 剩余空间仅 ' + $freePct + '%，建议清理') }
}

if (Get-Command Get-PhysicalDisk -ErrorAction SilentlyContinue) {
    $pd = @(Get-PhysicalDisk)
    if ($pd.Count -gt 0) {
        Write-Host ''
        Write-Host '  物理硬盘信息：'
        Show-Table ($pd | Select-Object DeviceId, FriendlyName, MediaType,
            @{n='容量(GB)'; e={[math]::Round($_.Size / 1GB, 0)}}, HealthStatus, OperationalStatus)
        foreach ($p in $pd) {
            if ($p.HealthStatus -and $p.HealthStatus -ne 'Healthy') {
                Write-Bad ('硬盘 ' + $p.FriendlyName + ' 健康状态为 ' + $p.HealthStatus + '，可能是卡顿根源，请尽快备份数据并检测硬盘')
            }
        }
        $rel = @($pd | ForEach-Object { $_ | Get-StorageReliabilityCounter })
        if ($rel.Count -gt 0) {
            $temps = @($rel | Where-Object { $_.Temperature -and $_.Temperature -gt 0 } | ForEach-Object { $_.Temperature })
            if ($temps.Count -gt 0) {
                $maxT = ($temps | Measure-Object -Maximum).Maximum
                Write-Host ('  硬盘最高温度 ：' + $maxT + ' ℃')
                if ($maxT -ge 60) { Write-Bad ('硬盘温度 ' + $maxT + '℃ 过高，散热不良会影响性能') }
                elseif ($maxT -ge 50) { Write-Note ('硬盘温度 ' + $maxT + '℃ 偏高') }
            }
            $wears = @($rel | Where-Object { $null -ne $_.Wear } | ForEach-Object { $_.Wear })
            if ($wears.Count -gt 0) {
                Write-Host ('  硬盘最大磨损度 ：' + ($wears | Measure-Object -Maximum).Maximum + ' / 100')
            }
        }
    }
}

# ---------------------------------------------------------------- 四、进程
Write-Title '四、资源占用最高的进程'
Write-Host '  按内存占用排序（前 10）：'
$topMem = Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 |
    Select-Object @{n='进程'; e={$_.ProcessName}}, Id,
        @{n='内存(MB)'; e={[math]::Round($_.WorkingSet64 / 1MB, 1)}},
        @{n='累计CPU(秒)'; e={ if ($_.CPU) { [math]::Round($_.CPU, 0) } else { 0 } }}
Show-Table $topMem

Write-Host '  按累计CPU时间排序（前 10，累计值不等于当前实时占用）：'
$topCpu = Get-Process | Where-Object { $null -ne $_.CPU } | Sort-Object CPU -Descending | Select-Object -First 10 |
    Select-Object @{n='进程'; e={$_.ProcessName}}, Id,
        @{n='累计CPU(秒)'; e={[math]::Round($_.CPU, 0)}},
        @{n='内存(MB)'; e={[math]::Round($_.WorkingSet64 / 1MB, 1)}}
Show-Table $topCpu

# ---------------------------------------------------------------- 五、自启动项
Write-Title '五、开机自启动项'
$startup = @(Get-CimInstance Win32_StartupCommand)
if ($startup.Count -gt 0) {
    Show-Table ($startup | Select-Object Name, Location, Command)
    if ($startup.Count -ge 15) {
        Write-Note ('开机自启项共 ' + $startup.Count + ' 个，数量偏多，建议在任务管理器“启动”页禁用不需要的')
    }
} else {
    Write-OK '未发现开机自启动项'
}

# ---------------------------------------------------------------- 六、服务
Write-Title '六、自动启动但未运行的服务'
$stopped = @(Get-Service | Where-Object { $_.StartType -eq 'Automatic' -and $_.Status -ne 'Running' })
if ($stopped.Count -gt 0) {
    Show-Table ($stopped | Select-Object -First 20 Status, Name, DisplayName)
    Write-Note ('有 ' + $stopped.Count + ' 个自动服务未运行，若系统功能异常可检查；多数第三方服务停止属正常')
} else {
    Write-OK '所有自动服务均在正常运行'
}

# ---------------------------------------------------------------- 七、网络
Write-Title '七、网络连接'
$nics = @(Get-CimInstance Win32_NetworkAdapterConfiguration -Filter 'IPEnabled=TRUE')
if ($nics.Count -eq 0) { Write-Note '未检测到已连接的网络适配器' }
foreach ($nic in $nics) {
    Write-Host ('  ' + $nic.Description)
    Write-Host ('    IP   ：' + (@($nic.IPAddress) -join ', '))
    Write-Host ('    网关 ：' + (@($nic.DefaultIPGateway) -join ', '))
    Write-Host ('    DNS  ：' + (@($nic.DNSServerSearchOrder) -join ', '))
}

# ---------------------------------------------------------------- 八、结论
Write-Title '八、体检结论'
if ($issues.Count -eq 0) {
    Write-Host '  未发现明显异常，系统与硬件状态良好。' -ForegroundColor Green
} else {
    Write-Host ('  共发现 ' + $issues.Count + ' 项需要注意：') -ForegroundColor Yellow
    $i = 0
    foreach ($it in $issues) { $i++; Write-Host ('   ' + $i + '. ' + $it) -ForegroundColor Yellow }
    Write-Host ''
    Write-Host '  通用建议：' -ForegroundColor Cyan
    Write-Host '   - 卡顿时在任务管理器分别按“磁盘”“CPU”“内存”排序，找占用大户'
    Write-Host '   - C 盘保持 20% 以上空闲；机械硬盘卡顿严重建议更换 SSD'
    Write-Host '   - 风扇噪音大、越用越卡多为散热积灰导致降频，清理灰尘'
    Write-Host '   - 怀疑系统文件损坏，可在管理员命令行运行：sfc /scannow'
}

Write-Host ''
Write-Host ('  完整报告已保存：' + $report) -ForegroundColor Cyan
Write-Host '  说明：本脚本仅做只读检查，不会修改任何系统设置。' -ForegroundColor DarkGray
try { Stop-Transcript | Out-Null } catch {}
Write-Host ''
