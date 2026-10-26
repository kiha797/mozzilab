//! 모찌한글 — HWP · HWPX 문서 편집기 (Windows 데스크톱)
//!
//! - 창 안의 편집 화면은 빌드할 때 넣은 웹 화면(rhwp-studio 를 모찌한글로 바꾼 것)이다.
//! - 탐색기에서 .hwp 파일을 두 번 누르면 그 파일을 `mozzidoc` 주소로 화면에 넘겨 바로 연다.
//! - 모찌LAB. 로그인 · 광고 · 자동 업데이트는 mozzi.rs 가 하고, 화면 표시는 overlay.js 가 한다.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod mozzi;

use std::path::PathBuf;
use std::sync::{Mutex, OnceLock};
use std::time::Duration;

use tauri::http::{Response, StatusCode};
use tauri::{WebviewUrl, WebviewWindowBuilder};

/// 처음 열 문서 (명령줄로 받은 파일)
fn opened() -> &'static Mutex<Option<PathBuf>> {
    static F: OnceLock<Mutex<Option<PathBuf>>> = OnceLock::new();
    F.get_or_init(|| Mutex::new(None))
}

#[tauri::command]
fn mozzi_state() -> serde_json::Value {
    mozzi::snapshot()
}

#[tauri::command]
fn mozzi_action(name: String, arg: serde_json::Value) {
    mozzi::action(&name, &arg);
}

fn encode(s: &str) -> String {
    let mut out = String::new();
    for b in s.as_bytes() {
        match *b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => out.push(*b as char),
            _ => out.push_str(&format!("%{b:02X}")),
        }
    }
    out
}

const OVERLAY: &str = include_str!("../overlay.js");

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|a| a == "--version") {
        println!("{} {}", mozzi::APP_NAME, mozzi::VERSION);
        return;
    }
    let file = args.iter().find(|a| !a.starts_with("--")).map(PathBuf::from).filter(|p| p.is_file());
    *opened().lock().unwrap_or_else(std::sync::PoisonError::into_inner) = file.clone();

    let result = tauri::Builder::default()
        // 명령줄로 받은 문서를 화면에 넘겨 주는 주소: mozzidoc://localhost/doc (Windows: http://mozzidoc.localhost/doc)
        .register_uri_scheme_protocol("mozzidoc", |_ctx, _req| {
            let path = opened().lock().unwrap_or_else(std::sync::PoisonError::into_inner).clone();
            let builder = Response::builder().header("Access-Control-Allow-Origin", "*");
            match path.and_then(|p| std::fs::read(p).ok()) {
                Some(bytes) => builder.header("Content-Type", "application/octet-stream").body(bytes),
                None => builder.status(StatusCode::NOT_FOUND).body(Vec::new()),
            }
            .unwrap_or_else(|_| Response::new(Vec::new()))
        })
        .invoke_handler(tauri::generate_handler![mozzi_state, mozzi_action])
        .setup(move |app| {
            let page = match &file {
                Some(p) => {
                    let name = p.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_else(|| "문서.hwp".into());
                    let doc = if cfg!(windows) { "http://mozzidoc.localhost/doc" } else { "mozzidoc://localhost/doc" };
                    format!("index.html?url={}&filename={}", encode(doc), encode(&name))
                }
                None => "index.html".into(),
            };
            WebviewWindowBuilder::new(app, "main", WebviewUrl::App(page.into()))
                .title(mozzi::APP_NAME)
                .inner_size(1440.0, 920.0)
                .min_inner_size(900.0, 600.0)
                .center()
                .initialization_script(OVERLAY)
                .build()?;
            // 0.5초마다 서버 응답 처리 · 로그인 확인 · 자동 업데이트
            let handle = app.handle().clone();
            std::thread::spawn(move || loop {
                std::thread::sleep(Duration::from_millis(500));
                if mozzi::tick() {
                    handle.exit(0);
                    break;
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!());
    if let Err(e) = result {
        eprintln!("모찌한글을 시작하지 못했어요: {e}");
    }
}
