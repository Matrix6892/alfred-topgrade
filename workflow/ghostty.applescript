-- Alfred owns creation; the dedicated terminal owns running/idle state.
on run argv
    try
        set launchMode to item 1 of argv
        if launchMode is not "update" and launchMode is not "check" then error "Unknown launch mode."
        set homePath to POSIX path of (path to home folder)
        set workflowPath to do shell script "/bin/pwd"
        set dataPath to item 3 of argv
        set sessionCommand to quoted form of (item 2 of argv) & " " & quoted form of (workflowPath & "/session.py") & " --state-dir " & quoted form of dataPath & " --topgrade " & quoted form of (item 4 of argv)
        set terminalIDPath to dataPath & "/terminal-id"
        do shell script "/bin/mkdir -p " & quoted form of dataPath
        set managedTerminalID to ""
        try
            set managedTerminalID to do shell script "/bin/cat " & quoted form of terminalIDPath
        on error
            -- No saved session yet.
        end try

        tell application "Ghostty"
            set sessionExists to false
            if managedTerminalID is not "" then
                set sessionExists to exists terminal id managedTerminalID
            end if
            if not sessionExists then
                set processExists to false
                try
                    do shell script sessionCommand & " probe"
                    set processExists to true
                end try
                if processExists then
                    -- Saved windows get new surface IDs after a Ghostty restart.
                    -- Recover the dedicated session by its own title, only while
                    -- the matching supervisor is confirmed alive.
                    set candidates to every terminal whose name starts with "Topgrade —"
                    if (count candidates) is not 1 then error "Could not identify the restored Topgrade tab. Close it and try again."
                    set managedTerminalID to id of item 1 of candidates
                    set sessionExists to true
                    do shell script "/usr/bin/printf '%s' " & quoted form of managedTerminalID & " > " & quoted form of terminalIDPath
                end if
            end if
            if sessionExists then
                    -- The session ignores busy requests and runs idle requests
                    -- in the same terminal, with no tab switching or typing.
                    if launchMode is "check" then
                        set originalTerminalID to id of focused terminal of selected tab of front window
                        set tabsBefore to count tabs of front window
                    end if
                    do shell script sessionCommand & " request " & launchMode
                    if launchMode is "check" then
                        set actualTerminalID to id of focused terminal of selected tab of front window
                        set tabsAfter to count tabs of front window
                        set checkResult to "original=" & originalTerminalID & linefeed & "selected=" & actualTerminalID & linefeed & "managed=" & managedTerminalID & linefeed & "tabs_before=" & tabsBefore & linefeed & "tabs_after=" & tabsAfter & linefeed & "reused=true"
                        do shell script "/usr/bin/printf '%s\\n' " & quoted form of checkResult & " > " & quoted form of (dataPath & "/focus-check.txt")
                        if actualTerminalID is not originalTerminalID or tabsAfter is not tabsBefore then error "Session reuse or focus verification failed."
                    end if
                    return
            end if

            set originalTerminalID to ""
            if (count windows) > 0 then
                set originalTerminalID to id of focused terminal of selected tab of front window
            end if
            set terminalConfig to new surface configuration
            set initial working directory of terminalConfig to homePath
            -- Load the usual login environment before starting the supervisor.
            set command of terminalConfig to "/bin/zsh -l -c " & quoted form of ("exec " & sessionCommand & " serve")
            if originalTerminalID is "" then
                set createdWindow to new window with configuration terminalConfig
                set managedTerminalID to id of focused terminal of selected tab of createdWindow
            else
                set createdTab to new tab in front window with configuration terminalConfig
                set managedTerminalID to id of focused terminal of createdTab
                delay 0.1
                focus terminal id originalTerminalID
            end if
        end tell
        do shell script "/usr/bin/printf '%s' " & quoted form of managedTerminalID & " > " & quoted form of terminalIDPath
        -- Wait for the new terminal to become ready, then explicitly request its
        -- first run. The saved terminal command itself always starts idle.
        do shell script sessionCommand & " request " & launchMode
        if launchMode is "check" then
            delay 0.1
            tell application "Ghostty"
                set actualTerminalID to id of focused terminal of selected tab of front window
                set checkResult to "original=" & originalTerminalID & linefeed & "selected=" & actualTerminalID & linefeed & "managed=" & managedTerminalID & linefeed & "tabs=" & (count tabs of front window)
            end tell
            do shell script "/usr/bin/printf '%s\\n' " & quoted form of checkResult & " > " & quoted form of (dataPath & "/focus-check.txt")
            if originalTerminalID is not "" and actualTerminalID is not originalTerminalID then error "Ghostty did not restore focus to the previous tab."
        end if
    on error errorText number errorNumber
        if errorNumber is -1743 then
            set errorText to "Allow Alfred to control Ghostty in System Settings → Privacy & Security → Automation."
        end if
        display alert "Could not start Topgrade in Ghostty" message errorText as critical
        error errorText number errorNumber
    end try
end run
