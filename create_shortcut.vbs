Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get script directory
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Create shortcut on desktop
Set shortcut = WshShell.CreateShortcut(WshShell.SpecialFolders("Desktop") & "\GestureMaster.lnk")
shortcut.TargetPath = scriptDir & "\start.bat"
shortcut.WorkingDirectory = scriptDir
shortcut.IconLocation = scriptDir & "\assets\icon.ico"
shortcut.Description = "GestureMaster - Gesture Control Master"
shortcut.Save

' Create shortcut in start menu
startMenuPath = WshShell.SpecialFolders("Programs") & "\GestureMaster"
If Not fso.FolderExists(startMenuPath) Then
    fso.CreateFolder(startMenuPath)
End If

Set shortcut2 = WshShell.CreateShortcut(startMenuPath & "\GestureMaster.lnk")
shortcut2.TargetPath = scriptDir & "\start.bat"
shortcut2.WorkingDirectory = scriptDir
shortcut2.IconLocation = scriptDir & "\assets\icon.ico"
shortcut2.Description = "GestureMaster - Gesture Control Master"
shortcut2.Save

WScript.Echo "Shortcuts created successfully!"
