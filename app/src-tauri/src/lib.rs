use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::Manager;

/// 持有后端子进程句柄，应用退出时回收。
struct BackendHandle(Mutex<Option<Child>>);

/// GPT-SoVITS 可选包位置（资源目录内或旁）。
const SOVITS_PACK_MARKER: &str = "gpt-sovits-pack/pack.json";
const SOVITS_PORT: u16 = 9880;

/// 应用资源根目录（打包模式）。
/// 依次探测：Tauri resource_dir() → deb/AppDir 布局（usr/bin → usr/lib/<产品>/resources）
/// → 仓库根（dev）。
fn resource_root(app: &tauri::AppHandle) -> PathBuf {
    let manifest_root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap();

    // dev 模式（debug 编译）直接使用仓库根，避免命中 target/debug/resources 旧副本
    if cfg!(debug_assertions) {
        return manifest_root.to_path_buf();
    }

    // 1. Tauri 资源目录
    if let Ok(res) = app.path().resource_dir() {
        if _looks_like_root(&res) {
            return res;
        }
    }
    // 2. exe 旁 / 上一级 lib 布局（AppImage AppDir 手动构建）
    if let Ok(exe) = std::env::current_exe() {
        let exe_dir = exe.parent().unwrap();
        let candidates = [
            exe_dir.join("resources"),
            exe_dir.join("../resources"),
            exe_dir.join("../lib/AI 配音工作台/resources"),
            exe_dir.join("lib/AI 配音工作台/resources"),
        ];
        for c in candidates {
            if _looks_like_root(&c) {
                return c;
            }
        }
    }
    manifest_root.to_path_buf()
}

fn _looks_like_root(p: &Path) -> bool {
    p.join("backend/server.py").exists() || p.join("env").exists()
}

/// 用户数据目录（打包=OS app-data，dev=仓库 workdir）。
/// dev 判定：仓库根含 pyproject.toml（打包资源目录只含 backend/scripts/env）。
fn data_dir(root: &Path) -> PathBuf {
    if root.join("pyproject.toml").exists() {
        return root.join("workdir");
    }
    dirs_base_dir().join("aidubbing")
}

/// OS 用户数据目录（跨平台）。
fn dirs_base_dir() -> PathBuf {
    #[cfg(target_os = "linux")]
    {
        std::env::var_os("XDG_DATA_HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|| std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".local/share")).unwrap())
    }
    #[cfg(target_os = "windows")]
    {
        std::env::var_os("APPDATA").map(PathBuf::from).unwrap()
    }
    #[cfg(not(any(target_os = "linux", target_os = "windows")))]
    {
        std::env::var_os("HOME").map(PathBuf::from).unwrap()
    }
}

/// 让系统分配一个空闲端口。
fn find_free_port() -> u16 {
    let listener = TcpListener::bind("127.0.0.1:0").expect("无法分配端口");
    listener.local_addr().unwrap().port()
}

/// 解析后端 python 可执行路径。
fn backend_python(root: &Path) -> PathBuf {
    let candidates = [
        root.join("env/bin/python"),           // 打包：env/ 是捆绑 venv
        root.join(".venv/bin/python"),          // dev：仓库 venv
    ];
    candidates
        .iter()
        .find(|p| p.exists())
        .cloned()
        .unwrap_or_else(|| candidates[1].to_path_buf())
}

/// 启动 Python 后端（前台运行，父进程看门狗保证随应用退出）。
fn launch_backend(root: &Path, data: &Path, port: u16) -> Child {
    let python = backend_python(root);
    let script = root.join("backend/server.py");
    Command::new(python)
        .arg(script)
        .arg("--host")
        .arg("127.0.0.1")
        .arg("--port")
        .arg(port.to_string())
        .arg("--parent-pid")
        .arg(std::process::id().to_string())
        .env("AIDUBBING_ROOT", root)
        .env("AIDUBBING_DATA", data)
        .current_dir(root)
        .spawn()
        .expect("无法启动后端进程")
}

/// 检测并启动 GPT-SoVITS 可选包（若存在）。
fn launch_sovits_if_present(root: &Path) -> Option<Child> {
    let marker = root.join(SOVITS_PACK_MARKER);
    if !marker.exists() {
        return None;
    }
    let pack_root = marker.parent().unwrap().to_path_buf();
    let python = backend_python(&pack_root);
    let api_script = pack_root.join("api_v2.py");
    if !api_script.exists() {
        return None;
    }
    Some(
        Command::new(python)
            .arg(api_script)
            .env("AIDUBBING_ROOT", &pack_root)
            .current_dir(&pack_root)
            .spawn()
            .expect("无法启动 GPT-SoVITS"),
    )
}

/// 极简 HTTP GET 健康检查（避免额外依赖）。
fn http_ok(host: &str, port: u16, path: &str) -> bool {
    let mut stream = match TcpStream::connect((host, port)) {
        Ok(s) => s,
        Err(_) => return false,
    };
    let req = format!(
        "GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
    );
    if stream.write_all(req.as_bytes()).is_err() {
        return false;
    }
    let mut buf = [0u8; 64];
    if stream.read(&mut buf).is_err() {
        return false;
    }
    String::from_utf8_lossy(&buf).contains("200 OK")
}

/// 轮询健康检查，直到就绪或超时。
fn wait_ready(port: u16, path: &str, timeout: Duration) -> bool {
    let deadline = std::time::Instant::now() + timeout;
    while std::time::Instant::now() < deadline {
        if http_ok("127.0.0.1", port, path) {
            return true;
        }
        thread::sleep(Duration::from_millis(500));
    }
    false
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let root = resource_root(app.handle());
            let data = data_dir(&root);
            std::fs::create_dir_all(&data).ok();

            // GPT-SoVITS 可选包：存在则启动并等就绪
            let sovits_child = launch_sovits_if_present(&root);
            if let Some(_c) = &sovits_child {
                thread::spawn(move || {
                    wait_ready(SOVITS_PORT, "/", Duration::from_secs(60));
                });
            }

            let port = find_free_port();
            let child = launch_backend(&root, &data, port);
            app.manage(BackendHandle(Mutex::new(Some(child))));

            // 复用配置中创建的主窗口，后端就绪后导航到工作台
            let window = app.get_webview_window("main").expect("缺少主窗口");
            let url = format!("http://127.0.0.1:{port}/");
            thread::spawn(move || {
                if wait_ready(port, "/api/health", Duration::from_secs(30)) {
                    let _ = window.navigate(url.parse().unwrap());
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("构建 Tauri 应用失败")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                // 清理后端子进程（前台子进程可直接 kill）
                if let Some(state) = app.try_state::<BackendHandle>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(mut child) = guard.take() {
                            let _ = child.kill();
                            let _ = child.wait();
                        }
                    }
                }
            }
        });
}
