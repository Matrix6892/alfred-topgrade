-- Terminal's supported API creates a window, not a tab. Reuse that one window.
on run argv
    try
        set launchMode to item 1 of argv
        if launchMode is not "update" and launchMode is not "check" then error "Unknown launch mode."
        set workflowPath to do shell script "/bin/pwd"
        set dataPath to item 3 of argv
        set sessionCommand to quoted form of (item 2 of argv) & " " & quoted form of (workflowPath & "/session.py") & " --state-dir " & quoted form of dataPath & " --topgrade " & quoted form of (item 4 of argv)
        set savedTTY to ""
        try
            set savedTTY to do shell script "/bin/cat " & quoted form of (dataPath & "/terminal-tty")
        end try
        tell application "Terminal"
            set matchingTabs to {}
            repeat with currentWindow in windows
                repeat with currentTab in tabs of currentWindow
                    if savedTTY is not "" and tty of currentTab is savedTTY then
                        set end of matchingTabs to currentTab
                    end if
                end repeat
            end repeat
            set processExists to false
            try
                do shell script sessionCommand & " probe"
                set processExists to true
            end try
            if processExists and (count matchingTabs) is 0 then
                repeat with currentWindow in windows
                    repeat with currentTab in tabs of currentWindow
                        if custom title of currentTab is "Topgrade" or custom title of currentTab starts with "Topgrade —" then set end of matchingTabs to currentTab
                    end repeat
                end repeat
            end if
            if (count matchingTabs) > 1 then error "More than one Topgrade window was found. Close the extra Topgrade windows and try again."
            if (count matchingTabs) is 1 then
                if launchMode is "check" then
                    set windowsBefore to count windows
                    set focusedWindowBefore to id of front window
                end if
                set savedTTY to tty of item 1 of matchingTabs
                do shell script "/usr/bin/printf '%s' " & quoted form of savedTTY & " > " & quoted form of (dataPath & "/terminal-tty")
                do shell script sessionCommand & " request " & launchMode
                if launchMode is "check" then
                    set windowsAfter to count windows
                    set focusedWindowAfter to id of front window
                    set checkResult to "backend=terminal" & linefeed & "tty=" & savedTTY & linefeed & "windows_before=" & windowsBefore & linefeed & "windows_after=" & windowsAfter & linefeed & "focused_before=" & focusedWindowBefore & linefeed & "focused_after=" & focusedWindowAfter & linefeed & "reused=true"
                    do shell script "/usr/bin/printf '%s\\n' " & quoted form of checkResult & " > " & quoted form of (dataPath & "/focus-check.txt")
                    if windowsBefore is not windowsAfter or focusedWindowBefore is not focusedWindowAfter then error "Terminal session reuse or focus verification failed."
                end if
                return
            end if
            if processExists then error "The Topgrade session is running in another terminal. Close that session before switching terminal apps."
            set originalWindowID to 0
            if (count windows) > 0 then set originalWindowID to id of front window
            set startupCommand to "exec /bin/zsh -l -c " & quoted form of ("exec " & sessionCommand & " serve")
            set createdTab to do script startupCommand
            set custom title of createdTab to "Topgrade"
            set savedTTY to tty of createdTab
            if originalWindowID is not 0 then
                set index of window id originalWindowID to 1
            end if
        end tell
        do shell script "/usr/bin/printf '%s' " & quoted form of savedTTY & " > " & quoted form of (dataPath & "/terminal-tty")
        do shell script sessionCommand & " request " & launchMode
        if launchMode is "check" then
            tell application "Terminal"
                set checkResult to "backend=terminal" & linefeed & "tty=" & savedTTY & linefeed & "windows=" & (count windows) & linefeed & "created=true"
            end tell
            do shell script "/usr/bin/printf '%s\\n' " & quoted form of checkResult & " > " & quoted form of (dataPath & "/focus-check.txt")
        end if
    on error errorText number errorNumber
        if errorNumber is -1743 then set errorText to "Allow Alfred to control Terminal in System Settings → Privacy & Security → Automation."
        display alert "Could not start Topgrade in Terminal" message errorText as critical
        error errorText number errorNumber
    end try
end run
