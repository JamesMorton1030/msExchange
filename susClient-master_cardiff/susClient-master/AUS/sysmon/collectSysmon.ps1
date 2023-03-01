# Copy-convert script created by Michael Lendvai & Harry Miller & Max Chunsi @ the University of Warwick.
# Modified by Joshua Hawking
#Creates a directory on a network fileshare with the current date-time
# 2020-09-17
# - client-0-HH-MM.csv
# - client-1-HH-MM.csv
# - client-2-HH-MM.csv
# ...

# Where should the logs be placed? This should be the shared drive that SUS is running on, such as \\windows-server\SUSLogs
# Path should NOT have a trailing slash
$destinationShare = "\\windows-server\SUS\Logs"
# Where should temporary logs be stored?
# Path should NOT have a trailing slash
$temporaryPath = "C:\tempLogs"
# Should files be converted to CSV before copying them to the destination drive?
# True = csv is copied to the destination drive
# False = evtx is copied to the destination drive
$convertToCSV = $false

# we can remove temporary folders from over 3 days ago
echo "Deleting logs from $temporaryPath from over 3 days ago..."
Get-ChildItem $temporaryPath -Recurse -Directory | Where CreationTime -lt  (Get-Date).AddDays(-3)  | Remove-Item -Force -Recurse


$today = (get-date -UFormat "%Y-%m-%d")
$todayTime = (get-date -Format "HH-mm")
$computerName = $env:COMPUTERNAME

# Check folders exist on the share + temporary folder
$folderPath = "$destinationShare\$today"
if( -Not (Test-Path -Path $folderPath ) )
{
    New-Item -ItemType directory -Path $folderPath
    echo "Created folder on share for $today."
}

$tempFolderPath = "$temporaryPath\$today"
if( -Not (Test-Path -Path $tempFolderPath ) )
{
    New-Item -ItemType directory -Path $tempFolderPath
    echo "Created folder on temporary share for $today."
}

$sysmonLogsPath = "C:\Windows\System32\Winevt\Logs\Microsoft-Windows-Sysmon%4Operational.evtx"
$eventLogPath = "$tempFolderPath\Sysmon-Logs-$todayTime.evtx"
$csvPath = "$tempFolderPath\Sysmon-Logs-$todayTime.csv"

# Now copy the files from event logs
echo "Copying sysmon logs to $eventLogPath"

if(Test-Path -Path $sysmonLogsPath)
{
    Copy-Item -Path $sysmonLogsPath -Destination $eventLogPath 
}
else
{
    echo "No sysmon logs found! Is Sysmon installed?"
    return
}

# Now clear the logs
echo "Logs collected, now clearing Sysmon logs"
[System.Diagnostics.Eventing.Reader.EventLogSession]::GlobalSession.ClearLog("Microsoft-Windows-Sysmon/Operational")

if($convertToCSV)
{
    # Converting from evtx to csv (takes less time compared to xml)
    echo "Converting evtx sysmon log to csv and writing to $csvPath"
    # Get-Winevent -Path C:\tempLogs\$newname | Select-Object -Property LevelDisplayName,TimeCreated,ProviderName,Id,TaskDisplayName,Message | Export-csv -path C:\tempLogs\$csvname -NoTypeInformation
    # Export to CSV
    Get-Winevent -Path $eventLogPath | Select-Object -Property LevelDisplayName,TimeCreated,ProviderName,Id,TaskDisplayName,Message | ConvertTo-CSV -NoTypeInformation | Out-File $csvPath -fo -en UTF8
    (Get-Content $csvPath) -replace '^"(.*?)","(.*?)","(.*?)","(.*?)","(.*?)",(.*?)$', '$1,$2,$3,$4,$5,$6' | % {$_.replace('LevelDisplayName,TimeCreated,ProviderName,Id,TaskDisplayName,"Message"', 'Level,Date and Time,Source,Event ID,Task Category')} | Out-File $csvPath -fo -en UTF8

    echo "Copying $csvPath to $folderPath\$computerName-$todayTime.csv"
    # Now the files have been created, copy them to the destination share
    if(Test-Path -Path $csvPath)
    {
        Copy-Item -Path $csvPath -Destination "$folderPath\$computerName-$todayTime.csv" 
    }
    else
    {
        echo "CSV file could not be found"
    }
}
else
{
    echo "Copying evtx sysmon log to $folderPath\$computerName-$todayTime.evtx"
    Copy-Item -Path $eventLogPath -Destination "$folderPath\$computerName-$todayTime.evtx" 
}