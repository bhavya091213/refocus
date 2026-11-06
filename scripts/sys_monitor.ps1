# Posts this PC's temperatures/load to the Refocus dashboard every 5 s.
# GPU temps: LibreHardwareMonitor (AMD, no driver needed). CPU temp: only if the CPU sensors return values
# (Intel needs the PawnIO driver; if absent the field is null and the dashboard shows "n/a").
$ErrorActionPreference = 'Continue'
$key = (Get-Content D:\Refocus\dashboard\token.txt).Trim()
$url = "http://127.0.0.1:8791/api/ingest/sys?key=$key"
Add-Type -Path D:\Refocus\tools\lhm\LibreHardwareMonitorLib.dll
$c = New-Object LibreHardwareMonitor.Hardware.Computer
$c.IsCpuEnabled = $true; $c.IsGpuEnabled = $true; $c.Open()
while ($true) {
  try {
    $o = @{ gpu_core=$null; gpu_hot=$null; gpu_load=$null; cpu_temp=$null; cpu_load=$null; board=$null }
    foreach ($h in $c.Hardware) {
      $h.Update()
      foreach ($s in $h.Sensors) {
        if ($s.Value -eq $null) { continue }
        if ($h.HardwareType -like 'Gpu*') {
          if ($s.SensorType -eq 'Temperature' -and $s.Name -eq 'GPU Core') { $o.gpu_core = [double]$s.Value }
          if ($s.SensorType -eq 'Temperature' -and $s.Name -eq 'GPU Hot Spot') { $o.gpu_hot = [double]$s.Value }
          if ($s.SensorType -eq 'Load' -and $s.Name -eq 'GPU Core') { $o.gpu_load = [double]$s.Value }
        }
        if ($h.HardwareType -eq 'Cpu') {
          if ($s.SensorType -eq 'Temperature' -and $s.Name -eq 'CPU Package') { $o.cpu_temp = [double]$s.Value }
          if ($s.SensorType -eq 'Load' -and $s.Name -eq 'CPU Total') { $o.cpu_load = [double]$s.Value }
        }
      }
    }
    try { $z = Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction Stop | Select -First 1
          $o.board = [math]::Round($z.CurrentTemperature/10 - 273.15, 1) } catch {}
    Invoke-RestMethod -Method Post -Uri $url -Body ($o | ConvertTo-Json) -ContentType 'application/json' | Out-Null
  } catch { Start-Sleep 2 }
  Start-Sleep 5
}
