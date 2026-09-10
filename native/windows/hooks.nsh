; Kill UI + backend before install/uninstall (backend locks resources/*.exe).
!macro KillGoogleDocsMcpProcesses
  DetailPrint "Stopping google-docs-mcp processes..."
  ExecWait 'taskkill /F /IM google-docs-mcp-backend.exe /T' $0
  ExecWait 'taskkill /F /IM google-docs-mcp-operator.exe /T' $0
  !if "${INSTALLMODE}" == "currentUser"
    nsis_tauri_utils::KillProcessCurrentUser "google-docs-mcp-backend.exe"
    Pop $0
    nsis_tauri_utils::KillProcessCurrentUser "google-docs-mcp-operator.exe"
    Pop $0
  !else
    nsis_tauri_utils::KillProcess "google-docs-mcp-backend.exe"
    Pop $0
    nsis_tauri_utils::KillProcess "google-docs-mcp-operator.exe"
    Pop $0
  !endif
  Sleep 2000
!macroend

!macro NSIS_HOOK_PREINSTALL
  !insertmacro KillGoogleDocsMcpProcesses
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  !insertmacro KillGoogleDocsMcpProcesses
!macroend
