#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;

use backend::{spawn_backend, stop_managed_child, BackendProcess};
use tauri::{Emitter, Manager};

#[tauri::command]
async fn start_backend(app: tauri::AppHandle, state: tauri::State<'_, BackendProcess>) -> Result<String, String> {
    spawn_backend(app, &state)
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_process::init())
        .manage(BackendProcess(std::sync::Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![start_backend])
        .setup(|app| {
            let handle = app.handle().clone();
            if let Err(e) = spawn_backend(handle.clone(), app.state::<BackendProcess>().inner()) {
                eprintln!("Backend error: {e}");
                let _ = handle.emit("backend-status", format!("error: {e}"));
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error building tauri application")
        .run(|app, event| {
            // Kill the spawned backend on BOTH events, not just Exit — a
            // window close can fire ExitRequested without a later Exit in
            // some shutdown paths, orphaning the backend child, which then
            // keeps the port locked on stale code forever (see
            // TAURI_PRODUCTION_PITFALLS.md §G).
            match event {
                tauri::RunEvent::Exit | tauri::RunEvent::ExitRequested { .. } => {
                    stop_managed_child(app.state::<BackendProcess>().inner());
                }
                _ => {}
            }
        });
}
