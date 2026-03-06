$python = "C:\Path\To\Python\python.exe"
$project = "C:\Users\Tsitsi\Desktop\DD"
$taskName = "GraphDueDiligenceWeekly"

$action = "`"$python`" -m app.scripts.run_weekly"
schtasks /Create /F /SC WEEKLY /D MON /ST 07:00 /TN $taskName /TR "$action" /RL HIGHEST /WD "$project"

Write-Host "Scheduled task '$taskName' created. Update the time/paths as needed."
