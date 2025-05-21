$totalSpecies = 2534
$csvDirectory = "Complete CSVs"
$indexFile = "species_index.txt"
$logFile = "scraping_log.txt"

# Function to log messages both to console and log file
function Write-Log {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    
    Write-Host $logMessage
    Add-Content -Path $logFile -Value $logMessage
}

# Create log file if it doesn't exist
if (-not (Test-Path $logFile)) {
    New-Item -Path $logFile -ItemType File -Force | Out-Null
}

# Verify the index file exists
if (-not (Test-Path $indexFile)) {
    Write-Log "Index file not found. Setting initial index to 0."
    Set-Content -Path $indexFile -Value "0"
}

# Read current index
$currentIndex = [int](Get-Content -Path $indexFile)

# Verify CSV directory exists
if (-not (Test-Path $csvDirectory)) {
    Write-Log "Creating CSV directory: $csvDirectory"
    New-Item -Path $csvDirectory -ItemType Directory -Force | Out-Null
}

# Count existing files
$existingFiles = Get-ChildItem -Path $csvDirectory -Filter "*.csv" | Measure-Object
$processedCount = $existingFiles.Count

Write-Log "Starting process: $processedCount species already processed out of $totalSpecies"
Write-Log "Current index from index file: $currentIndex"

# Main loop - continue until all species are processed
$consecutiveFailures = 0
$maxConsecutiveFailures = 5

while ($currentIndex -lt $totalSpecies) {
    # Update current index from file (in case it was manually edited)
    $currentIndex = [int](Get-Content -Path $indexFile)
    
    Write-Log "Processing species at index $currentIndex (Progress: $currentIndex/$totalSpecies, ${([math]::Round($currentIndex/$totalSpecies*100, 2))}%)"
    
    # Run Python script to process the next species
    $pythonProcess = Start-Process -FilePath python -ArgumentList "scrap_with_index.py" -PassThru
    
    # Wait for Python process to complete with timeout
    $maxWaitTime = 300 # 5 minutes maximum wait time
    $waitTime = 0
    $checkInterval = 2 # Check every 2 seconds
    
    Write-Log "Waiting for Python process (PID: $($pythonProcess.Id)) to complete..."
    
    while (-not $pythonProcess.HasExited -and $waitTime -lt $maxWaitTime) {
        Start-Sleep -Seconds $checkInterval
        $waitTime += $checkInterval
        
        # Show progress message every 30 seconds
        if ($waitTime % 30 -eq 0) {
            Write-Log "Still waiting... ($waitTime seconds elapsed)"
        }
    }
    
    # Check if process completed naturally or timed out
    if ($pythonProcess.HasExited) {
        $exitCode = $pythonProcess.ExitCode
        Write-Log "Python process completed after $waitTime seconds with exit code: $exitCode"
        
        if ($exitCode -eq 0) {
            Write-Log "Process completed successfully"
            $consecutiveFailures = 0
        } else {
            Write-Log "Process failed with exit code $exitCode"
            $consecutiveFailures++
        }
    } else {
        Write-Log "Maximum wait time ($maxWaitTime seconds) exceeded. Terminating Python process..."
        Stop-Process -Id $pythonProcess.Id -Force
        Write-Log "Python process terminated"
        $consecutiveFailures++
    }
    
    # Allow system to stabilize
    Start-Sleep -Seconds 5
    
    # Count files again to verify progress
    $newIndex = [int](Get-Content -Path $indexFile)
    $newFiles = Get-ChildItem -Path $csvDirectory -Filter "*.csv" | Measure-Object
    $newCount = $newFiles.Count
    
    Write-Log "Current index is now: $newIndex (previous: $currentIndex)"
    Write-Log "CSV count: $newCount (previous: $processedCount)"
    
    # Verify progress
    if ($newIndex -gt $currentIndex) {
        Write-Log "Index progressed successfully from $currentIndex to $newIndex"
        $currentIndex = $newIndex
        $consecutiveFailures = 0
    }
    
    if ($newCount -gt $processedCount) {
        Write-Log "Success! $($newCount - $processedCount) new species file(s) downloaded"
        $processedCount = $newCount
    } else {
        Write-Log "No new species files downloaded in this run"
    }
    
    # Handle consecutive failures
    if ($consecutiveFailures -ge $maxConsecutiveFailures) {
        Write-Log "WARNING: $consecutiveFailures consecutive failures detected. Will restart browser and increment index manually."
        
        # Kill all chrome processes that might be hanging
        Get-Process -Name chrome, chromedriver -ErrorAction SilentlyContinue | Stop-Process -Force
        
        # Increment index manually to avoid getting stuck
        $currentIndex++
        Set-Content -Path $indexFile -Value $currentIndex
        
        Write-Log "Forcibly incremented index to $currentIndex and restarted browser"
        $consecutiveFailures = 0
        
        # Extra pause to ensure system stabilizes
        Start-Sleep -Seconds 10
    }
    
    # Clean up any orphaned Python processes
    $oldProcesses = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.StartTime -lt (Get-Date).AddSeconds(-$maxWaitTime - 10) }
    if ($oldProcesses) {
        Write-Log "Cleaning up $($oldProcesses.Count) orphaned Python processes"
        $oldProcesses | Stop-Process -Force
    }
    
    # Clean up any orphaned Chrome processes
    $oldChromeProcesses = Get-Process -Name chrome, chromedriver -ErrorAction SilentlyContinue | Where-Object { $_.StartTime -lt (Get-Date).AddSeconds(-$maxWaitTime - 10) }
    if ($oldChromeProcesses) {
        Write-Log "Cleaning up $($oldChromeProcesses.Count) orphaned Chrome processes"
        $oldChromeProcesses | Stop-Process -Force
    }
}

Write-Log "Complete! All $totalSpecies species have been processed."
