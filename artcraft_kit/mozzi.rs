//! 모찌랩 연동 (모찌포토 · 모찌벡터 공통)
//! - 로그인: 웹에서 승인하는 '기기 연결' 방식 (/api/device/start → /api/device/poll → /api/me)
//! - 광고: 무료 사용자에게 제목 표시줄 오른쪽 배너 + 저장 후 팝업 (/api/ads), 모찌 플러스 구독자는 광고 없음
//! - 자동 업데이트: GitHub 최신 릴리스의 설치파일을 받아 조용히 설치하고 다시 켠다
//!
//! 이 파일은 mozzilab 저장소 artcraft_kit/mozzi.rs 가 원본이며, 빌드할 때 각 앱에 복사된다.
//! (@@ 로 둘러싼 값은 빌드 스크립트가 앱마다 바꿔 넣는다.)
#![allow(dead_code)]

use std::path::PathBuf;
use std::sync::mpsc::{Receiver, Sender, channel};
use std::sync::{Mutex, OnceLock};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use egui::{Align2, Color32, Context, CornerRadius, FontId, RichText, Sense, Stroke, vec2};
use serde_json::{Value, json};

pub const SLUG: &str = "@@SLUG@@";
pub const APP_ID: &str = "@@APP_ID@@";
pub const APP_NAME: &str = "@@NAME@@";
pub const VERSION: &str = "@@VERSION@@";
pub const SERVER: &str = "https://mozzilab.labelpos.com";
const RELEASE_API: &str = "https://api.github.com/repos/kiha797/mozzilab/releases/latest";
const ACCENT: Color32 = Color32::from_rgb(0xff, 0x6f, 0x91);
const OFFLINE_GRACE_SECS: u64 = 7 * 24 * 3600;
const UPDATE_EVERY_SECS: u64 = 20 * 3600;

fn now() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0)
}

fn appdata() -> PathBuf {
    std::env::var_os("APPDATA").map(PathBuf::from).unwrap_or_else(|| {
        std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".config")).unwrap_or_else(std::env::temp_dir)
    })
}

fn cfg_path() -> PathBuf {
    appdata().join(APP_ID).join("mozzi.json")
}

/// 이 PC 고유번호: 모든 모찌랩 프로그램이 함께 쓴다 (%APPDATA%\MozziLab\device.json)
fn device_id() -> String {
    let path = appdata().join("MozziLab").join("device.json");
    if let Some(id) = std::fs::read_to_string(&path).ok().and_then(|t| serde_json::from_str::<Value>(&t).ok()).and_then(|v| v["device_id"].as_str().map(String::from)) {
        if !id.is_empty() {
            return id;
        }
    }
    let seed = format!("{:x}{:x}{}", now(), std::process::id(), std::env::var("COMPUTERNAME").unwrap_or_default());
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for b in seed.bytes() {
        h = (h ^ u64::from(b)).wrapping_mul(0x100_0000_01b3);
    }
    let id = format!("{h:016x}{:08x}", now() as u32);
    let _ = std::fs::create_dir_all(path.parent().unwrap_or(&path));
    let _ = std::fs::write(&path, json!({"device_id": id}).to_string());
    id
}

fn device_name() -> String {
    std::env::var("COMPUTERNAME").or_else(|_| std::env::var("HOSTNAME")).unwrap_or_else(|_| "내 PC".into())
}

/// 웹 브라우저로 주소 열기
pub fn open_url(url: &str) {
    let url = if url.starts_with('/') { format!("{SERVER}{url}") } else { url.to_string() };
    #[cfg(windows)]
    let r = std::process::Command::new("rundll32").args(["url.dll,FileProtocolHandler", &url]).spawn();
    #[cfg(target_os = "macos")]
    let r = std::process::Command::new("open").arg(&url).spawn();
    #[cfg(all(unix, not(target_os = "macos")))]
    let r = std::process::Command::new("xdg-open").arg(&url).spawn();
    if let Err(e) = r {
        log::warn!("모찌랩: 브라우저를 열 수 없음: {e}");
    }
}

// ---------------------------------------------------------------- 네트워크
fn agent(timeout: u64) -> ureq::Agent {
    ureq::Agent::config_builder()
        .tls_config(ureq::tls::TlsConfig::builder().root_certs(ureq::tls::RootCerts::PlatformVerifier).build())
        .timeout_global(Some(Duration::from_secs(timeout)))
        .http_status_as_error(false)
        .build()
        .new_agent()
}

/// (상태코드, JSON) — 연결 실패는 상태코드 0
fn request(method: &str, path: &str, body: Option<Value>, token: Option<&str>) -> (u16, Value) {
    let url = if path.starts_with("http") { path.to_string() } else { format!("{SERVER}{path}") };
    let a = agent(20);
    let ua = format!("{APP_ID}/{VERSION}");
    let res = if method == "POST" {
        let mut r = a.post(&url).header("User-Agent", &ua).header("Content-Type", "application/json");
        if let Some(t) = token {
            r = r.header("Authorization", &format!("Bearer {t}"));
        }
        r.send(body.unwrap_or(json!({})).to_string())
    } else {
        let mut r = a.get(&url).header("User-Agent", &ua).header("Accept", "application/json");
        if let Some(t) = token {
            r = r.header("Authorization", &format!("Bearer {t}"));
        }
        r.call()
    };
    match res {
        Ok(mut resp) => {
            let code = resp.status().as_u16();
            let text = resp.body_mut().with_config().limit(2 * 1024 * 1024).read_to_string().unwrap_or_default();
            (code, serde_json::from_str(&text).unwrap_or(Value::Null))
        }
        Err(e) => {
            log::warn!("모찌랩 서버 연결 실패 {path}: {e}");
            (0, Value::Null)
        }
    }
}

enum Msg {
    Me(u16, Value),
    Ads(u16, Value),
    DeviceStart(u16, Value),
    DevicePoll(u16, Value),
    Release(bool, u16, Value),
    Downloaded(Result<PathBuf, String>),
    Progress(f32),
}

fn spawn(tx: &Sender<Msg>, f: impl FnOnce() -> Msg + Send + 'static) {
    let tx = tx.clone();
    let _ = std::thread::Builder::new().name("mozzilab".into()).spawn(move || {
        let _ = tx.send(f());
    });
}

// ---------------------------------------------------------------- 상태
#[derive(Default)]
struct Login {
    open: bool,
    device_code: String,
    user_code: String,
    verify_url: String,
    info: String,
    next_poll: Option<Instant>,
    interval: u64,
    failed: bool,
}

struct Update {
    tag: String,
    notes: String,
    url: String,
    mandatory: bool,
    downloading: bool,
    progress: f32,
    error: String,
}

struct State {
    cfg: Value,
    device_id: String,
    ads: Value,
    tx: Sender<Msg>,
    rx: Receiver<Msg>,
    login: Login,
    banner: usize,
    banner_at: Instant,
    popup: Option<Value>,
    update: Option<Update>,
    manual_check: bool,
    info_msg: Option<String>,
    started: Option<Instant>,
    last_sync: Instant,
    was_dirty: bool,
    quit: bool,
    auto_checked: bool,
    refresh_needed: bool,
}

fn house_ads() -> Value {
    json!({
        "show_ads": true, "popup_every": 1, "pricing_url": format!("{SERVER}/pricing"),
        "banner": [{"title": "광고 없이 쾌적하게, 모찌 플러스", "subtitle": "월 5,500원 · 모든 모찌랩 광고 제거", "bg_color": "#ff6f91", "button_text": "자세히 알아보기"}],
        "popup": [{"title": "광고가 신경 쓰이나요?", "subtitle": "모찌 플러스로 모든 모찌랩 프로그램을 광고 없이 쓰세요. 언제든 해지 가능!", "bg_color": "#ff8fab", "button_text": "광고 없이 쓰기"}],
    })
}

fn load_cfg() -> Value {
    let mut cfg = std::fs::read_to_string(cfg_path()).ok().and_then(|t| serde_json::from_str::<Value>(&t).ok()).unwrap_or(json!({}));
    // 예전(파이썬) 모찌포토/모찌벡터의 로그인 정보를 이어받는다
    if cfg.get("account").is_none() {
        let old = appdata().join(APP_ID).join("config.json");
        if let Some(acc) = std::fs::read_to_string(old).ok().and_then(|t| serde_json::from_str::<Value>(&t).ok()).and_then(|v| v.get("account").cloned()) {
            if acc.get("token").and_then(Value::as_str).is_some_and(|t| !t.is_empty()) {
                cfg["account"] = json!({"token": acc["token"], "name": acc["name"], "email": acc["email"]});
            }
        }
    }
    cfg
}

impl State {
    fn new() -> Self {
        let (tx, rx) = channel();
        State {
            cfg: load_cfg(),
            device_id: device_id(),
            ads: house_ads(),
            tx,
            rx,
            login: Login::default(),
            banner: 0,
            banner_at: Instant::now(),
            popup: None,
            update: None,
            manual_check: false,
            info_msg: None,
            started: None,
            last_sync: Instant::now(),
            was_dirty: false,
            quit: false,
            auto_checked: false,
            refresh_needed: false,
        }
    }

    fn save(&self) {
        let p = cfg_path();
        let _ = std::fs::create_dir_all(p.parent().unwrap_or(&p));
        let _ = std::fs::write(&p, serde_json::to_string_pretty(&self.cfg).unwrap_or_default());
    }

    fn token(&self) -> Option<String> {
        self.cfg["account"]["token"].as_str().filter(|t| !t.is_empty()).map(String::from)
    }

    fn logged_in(&self) -> bool {
        self.token().is_some()
    }

    fn name(&self) -> String {
        let a = &self.cfg["account"];
        a["name"].as_str().filter(|s| !s.is_empty()).or(a["email"].as_str()).unwrap_or("회원").to_string()
    }

    fn premium(&self) -> bool {
        let a = &self.cfg["account"];
        self.logged_in() && a["premium"].as_bool() == Some(true) && now().saturating_sub(a["checked_at"].as_u64().unwrap_or(0)) < OFFLINE_GRACE_SECS
    }

    fn show_ads(&self) -> bool {
        !self.premium() && self.ads["show_ads"].as_bool() != Some(false)
    }

    fn refresh(&self) {
        if let Some(t) = self.token() {
            spawn(&self.tx, move || {
                let (c, v) = request("GET", "/api/me", None, Some(&t));
                Msg::Me(c, v)
            });
        }
        let t = self.token();
        spawn(&self.tx, move || {
            let (c, v) = request("GET", &format!("/api/ads?app={SLUG}"), None, t.as_deref());
            Msg::Ads(c, v)
        });
    }

    fn start_login(&mut self) {
        self.login = Login { open: true, info: "서버에 연결하는 중…".into(), ..Default::default() };
        let body = json!({"device_id": self.device_id, "device_name": device_name(), "app": SLUG, "version": VERSION});
        spawn(&self.tx, move || {
            let (c, v) = request("POST", "/api/device/start", Some(body), None);
            Msg::DeviceStart(c, v)
        });
    }

    fn logout(&mut self) {
        if let Some(t) = self.token() {
            spawn(&self.tx, move || {
                let _ = request("POST", "/api/logout", None, Some(&t));
                Msg::Me(0, Value::Null)
            });
        }
        self.cfg["account"] = json!({});
        self.save();
        self.ads = house_ads();
        self.refresh();
    }

    fn check_update(&mut self, manual: bool) {
        self.manual_check = manual;
        if !manual {
            if now().saturating_sub(self.cfg["update_checked_at"].as_u64().unwrap_or(0)) < UPDATE_EVERY_SECS {
                return;
            }
        }
        spawn(&self.tx, move || {
            let (c, v) = request("GET", RELEASE_API, None, None);
            Msg::Release(manual, c, v)
        });
    }

    fn handle(&mut self, msg: Msg) {
        match msg {
            Msg::Me(200, v) => {
                let a = &mut self.cfg["account"];
                for k in ["email", "name", "expires_at", "plan_name", "mypage_url", "pricing_url"] {
                    a[k] = v[k].clone();
                }
                a["premium"] = json!(v["premium"].as_bool().unwrap_or(false));
                a["checked_at"] = json!(now());
                self.save();
            }
            Msg::Me(401, _) => {
                self.cfg["account"] = json!({});
                self.save();
            }
            Msg::Me(..) => {}
            Msg::Ads(200, v) if v.is_object() => {
                let mut ads = house_ads();
                for (k, val) in v.as_object().into_iter().flatten() {
                    ads[k] = val.clone();
                }
                for kind in ["banner", "popup"] {
                    if ads[kind].as_array().is_none_or(Vec::is_empty) {
                        ads[kind] = house_ads()[kind].clone();
                    }
                }
                self.ads = ads;
            }
            Msg::Ads(..) => {}
            Msg::DeviceStart(200, v) if v["device_code"].is_string() => {
                let l = &mut self.login;
                l.device_code = v["device_code"].as_str().unwrap_or_default().into();
                l.user_code = v["user_code"].as_str().unwrap_or_default().into();
                l.verify_url = v["verify_url"].as_str().unwrap_or_default().into();
                l.interval = v["interval"].as_u64().unwrap_or(3).max(2);
                l.info = "웹 브라우저에서 로그인(또는 회원가입)한 뒤\n아래 코드를 확인하고 [연결 승인]을 눌러 주세요.".into();
                l.next_poll = Some(Instant::now() + Duration::from_secs(l.interval));
                open_url(&l.verify_url);
            }
            Msg::DeviceStart(..) => {
                self.login.info = format!("모찌랩 서버에 연결할 수 없어요.\n인터넷 연결을 확인하고 다시 시도해 주세요.\n({SERVER})");
                self.login.failed = true;
            }
            Msg::DevicePoll(_, v) => {
                if !self.login.open {
                    return;
                }
                match v["status"].as_str().unwrap_or("") {
                    "approved" if v["token"].is_string() => {
                        self.cfg["account"] = json!({"token": v["token"]});
                        self.save();
                        self.login.open = false;
                        self.info_msg = Some("로그인했어요! 계정 정보를 불러오는 중이에요.".into());
                        self.refresh();
                    }
                    "expired" | "denied" | "invalid" | "used" => {
                        self.login.info = "시간이 지났거나 연결이 거절되었어요. [다시 시도]를 눌러 주세요.".into();
                        self.login.failed = true;
                        self.login.next_poll = None;
                    }
                    _ => self.login.next_poll = Some(Instant::now() + Duration::from_secs(self.login.interval)),
                }
            }
            Msg::Release(manual, code, v) => {
                self.cfg["update_checked_at"] = json!(now());
                self.save();
                if code != 200 {
                    if manual {
                        self.info_msg = Some("업데이트 정보를 가져오지 못했어요. 잠시 후 다시 시도해 주세요.".into());
                    }
                    return;
                }
                let tag = v["tag_name"].as_str().unwrap_or("").trim_start_matches('v').to_string();
                let notes = v["body"].as_str().unwrap_or("").to_string();
                let asset = format!("{APP_ID}_Setup.exe");
                let url = v["assets"].as_array().into_iter().flatten().find(|a| a["name"].as_str() == Some(asset.as_str()))
                    .and_then(|a| a["browser_download_url"].as_str()).unwrap_or("").to_string();
                let mandatory = notes.contains("[필수]");
                let newer = parse_ver(&tag) > parse_ver(VERSION);
                if !newer || url.is_empty() {
                    if manual {
                        self.info_msg = Some(format!("지금 최신 버전(v{VERSION})을 쓰고 있어요."));
                    }
                    return;
                }
                if !manual && !mandatory && self.cfg["update_skip"].as_str() == Some(tag.as_str()) {
                    return;
                }
                self.update = Some(Update { tag, notes, url, mandatory, downloading: false, progress: 0.0, error: String::new() });
            }
            Msg::Progress(p) => {
                if let Some(u) = &mut self.update {
                    u.progress = p;
                }
            }
            Msg::Downloaded(Ok(path)) => {
                let r = std::process::Command::new(&path).args(["/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/CLOSEAPPLICATIONS"]).spawn();
                match r {
                    Ok(_) => self.quit = true,
                    Err(e) => {
                        if let Some(u) = &mut self.update {
                            u.downloading = false;
                            u.error = format!("설치 프로그램을 실행하지 못했어요: {e}");
                        }
                    }
                }
            }
            Msg::Downloaded(Err(e)) => {
                if let Some(u) = &mut self.update {
                    u.downloading = false;
                    u.error = e;
                }
            }
        }
    }

    fn download(&mut self) {
        let Some(u) = &mut self.update else { return };
        u.downloading = true;
        u.error.clear();
        let url = u.url.clone();
        let tx = self.tx.clone();
        spawn(&self.tx, move || {
            let dest = std::env::temp_dir().join(format!("{APP_ID}_Setup.exe"));
            let r = (|| -> Result<PathBuf, String> {
                let resp = agent(600).get(&url).header("User-Agent", APP_ID).call().map_err(|e| format!("내려받지 못했어요: {e}"))?;
                if resp.status() != 200 {
                    return Err(format!("내려받지 못했어요 (HTTP {})", resp.status()));
                }
                let total: f32 = resp.headers().get("content-length").and_then(|v| v.to_str().ok()).and_then(|v| v.parse().ok()).unwrap_or(0.0);
                let mut reader = resp.into_body().into_with_config().limit(1024 * 1024 * 1024).reader();
                let part = dest.with_extension("part");
                let mut f = std::fs::File::create(&part).map_err(|e| e.to_string())?;
                let mut buf = vec![0u8; 256 * 1024];
                let mut got = 0f32;
                loop {
                    let n = std::io::Read::read(&mut reader, &mut buf).map_err(|e| format!("내려받다가 끊겼어요: {e}"))?;
                    if n == 0 {
                        break;
                    }
                    std::io::Write::write_all(&mut f, &buf[..n]).map_err(|e| e.to_string())?;
                    got += n as f32;
                    if total > 0.0 {
                        let _ = tx.send(Msg::Progress(got / total));
                    }
                }
                drop(f);
                std::fs::rename(&part, &dest).map_err(|e| e.to_string())?;
                Ok(dest)
            })();
            Msg::Downloaded(r)
        });
    }
}

fn parse_ver(s: &str) -> (u32, u32, u32) {
    let mut it = s.split(|c: char| !c.is_ascii_digit()).filter(|p| !p.is_empty()).map(|p| p.parse().unwrap_or(0));
    (it.next().unwrap_or(0), it.next().unwrap_or(0), it.next().unwrap_or(0))
}

fn state() -> &'static Mutex<State> {
    static S: OnceLock<Mutex<State>> = OnceLock::new();
    S.get_or_init(|| Mutex::new(State::new()))
}

fn with<R>(f: impl FnOnce(&mut State) -> R) -> R {
    let mut g = state().lock().unwrap_or_else(std::sync::PoisonError::into_inner);
    f(&mut g)
}

fn hex(s: Option<&str>, fallback: Color32) -> Color32 {
    let s = s.unwrap_or("").trim_start_matches('#');
    if s.len() == 6 {
        if let Ok(v) = u32::from_str_radix(s, 16) {
            return Color32::from_rgb((v >> 16) as u8, (v >> 8) as u8, v as u8);
        }
    }
    fallback
}

// ---------------------------------------------------------------- 화면
/// 제목 표시줄 오른쪽 (오른쪽→왼쪽으로 쌓이는 줄에서 호출): [로그인] 버튼과 광고 배너
pub fn title_controls(ui: &mut egui::Ui) {
    with(|s| {
        let label = if s.logged_in() { format!("{}{} 님", if s.premium() { "[플러스] " } else { "" }, s.name()) } else { "로그인".to_string() };
        let btn = egui::Button::new(RichText::new(label).color(ACCENT).strong()).stroke(Stroke::new(1.2, ACCENT)).corner_radius(CornerRadius::same(6));
        if s.logged_in() {
            let r = ui.add(btn);
            egui::Popup::menu(&r).show(|ui| {
                if let Some(e) = s.cfg["account"]["email"].as_str() {
                    ui.weak(e);
                }
                ui.label(if s.premium() { "모찌 플러스 이용 중 · 광고 없음" } else { "무료 이용 중" });
                ui.separator();
                if ui.button("마이페이지").clicked() {
                    open_url(s.cfg["account"]["mypage_url"].as_str().unwrap_or("/mypage"));
                }
                if !s.premium() && ui.button("광고 없이 쓰기 (모찌 플러스)").clicked() {
                    open_url(s.cfg["account"]["pricing_url"].as_str().unwrap_or("/pricing"));
                }
                if ui.button("구독 상태 새로고침").clicked() {
                    s.refresh();
                }
                if ui.button("업데이트 확인").clicked() {
                    s.check_update(true);
                }
                ui.separator();
                if ui.button("로그아웃").clicked() {
                    s.logout();
                }
            });
        } else {
            let r = ui.add(btn).on_hover_text("모찌랩 계정으로 로그인 · 모찌 플러스 구독자는 광고 없이 사용");
            if r.clicked() {
                s.start_login();
            }
        }
        if s.show_ads() && ui.available_width() > 200.0 {
            let banners = s.ads["banner"].as_array().cloned().unwrap_or_default();
            if s.banner_at.elapsed() > Duration::from_secs(45) && !banners.is_empty() {
                s.banner = (s.banner + 1) % banners.len();
                s.banner_at = Instant::now();
            }
            if let Some(ad) = banners.get(s.banner % banners.len().max(1)) {
                let bg = hex(ad["bg_color"].as_str(), ACCENT);
                let title = ad["title"].as_str().unwrap_or("모찌 플러스").to_string();
                let w = (ui.available_width() - 20.0).clamp(120.0, 320.0);
                let (rect, resp) = ui.allocate_exact_size(vec2(w, 24.0), Sense::click());
                let p = ui.painter();
                p.rect_filled(rect, CornerRadius::same(12), bg);
                let tag = egui::Rect::from_min_size(rect.min + vec2(6.0, 5.0), vec2(22.0, 14.0));
                p.rect_filled(tag, CornerRadius::same(4), Color32::from_black_alpha(70));
                p.text(tag.center(), Align2::CENTER_CENTER, "AD", FontId::proportional(9.5), Color32::WHITE);
                let mut job = egui::text::LayoutJob::simple_singleline(title, FontId::proportional(12.0), Color32::WHITE);
                job.wrap = egui::text::TextWrapping::truncate_at_width(w - 44.0);
                let g = ui.painter().layout_job(job);
                ui.painter().galley(rect.min + vec2(34.0, (24.0 - g.size().y) / 2.0), g, Color32::WHITE);
                let resp = resp.on_hover_text(format!("{}\n{}", ad["subtitle"].as_str().unwrap_or(""), "누르면 자세히 볼 수 있어요"));
                if resp.clicked() {
                    open_url(ad["click_url"].as_str().or(s.ads["pricing_url"].as_str()).unwrap_or("/pricing"));
                }
                if resp.hovered() {
                    ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
                }
            }
        }
    });
}

/// 작업(저장·내보내기)이 끝날 때: 무료 사용자에게 가끔 팝업 광고
pub fn job_done() {
    with(|s| {
        if !s.show_ads() {
            return;
        }
        let n = s.cfg["job_count"].as_u64().unwrap_or(0) + 1;
        s.cfg["job_count"] = json!(n);
        s.save();
        let every = s.ads["popup_every"].as_u64().unwrap_or(1).max(1);
        if n % every == 0 {
            let list = s.ads["popup"].as_array().cloned().unwrap_or_default();
            if !list.is_empty() {
                s.popup = Some(list[(n as usize / every as usize) % list.len()].clone());
                if let Some(id) = s.popup.as_ref().and_then(|p| p["id"].as_i64()) {
                    spawn(&s.tx, move || {
                        let _ = request("POST", &format!("/api/ads/{id}/view"), None, None);
                        Msg::Me(0, Value::Null)
                    });
                }
            }
        }
    });
}

/// 문서가 '저장 안 됨 → 저장됨'으로 바뀌었는지 알려 주면 저장 완료로 보고 job_done 을 부른다
pub fn note_dirty(dirty: bool) {
    let saved = with(|s| {
        let saved = s.was_dirty && !dirty;
        s.was_dirty = dirty;
        saved
    });
    if saved {
        job_done();
    }
}

/// 매 화면마다 한 번 호출: 서버 응답 처리 + 로그인 창 · 팝업 광고 · 업데이트 창
pub fn show(ctx: &Context) {
    let quit = with(|s| {
        while let Ok(m) = s.rx.try_recv() {
            s.handle(m);
        }
        let started = *s.started.get_or_insert_with(|| {
            s.refresh_needed = true;
            Instant::now()
        });
        if std::mem::take(&mut s.refresh_needed) {
            s.refresh();
        }
        if !s.auto_checked && started.elapsed() > Duration::from_secs(8) {
            s.auto_checked = true;
            s.check_update(false);
        }
        if s.last_sync.elapsed() > Duration::from_secs(3 * 3600) {
            s.last_sync = Instant::now();
            s.refresh();
        }
        if s.login.open {
            if let Some(t) = s.login.next_poll {
                if Instant::now() >= t {
                    s.login.next_poll = None;
                    let code = s.login.device_code.clone();
                    spawn(&s.tx, move || {
                        let (c, v) = request("POST", "/api/device/poll", Some(json!({"device_code": code})), None);
                        Msg::DevicePoll(c, v)
                    });
                }
            }
            login_window(ctx, s);
        }
        if s.popup.is_some() {
            popup_ad(ctx, s);
        }
        if s.update.is_some() {
            update_window(ctx, s);
        }
        if let Some(m) = s.info_msg.clone() {
            let mut open = true;
            egui::Window::new(APP_NAME).collapsible(false).resizable(false).anchor(Align2::CENTER_CENTER, [0.0, 0.0]).open(&mut open).show(ctx, |ui| {
                ui.label(&m);
                ui.add_space(6.0);
                if ui.button("확인").clicked() {
                    s.info_msg = None;
                }
            });
            if !open {
                s.info_msg = None;
            }
        }
        s.quit
    });
    // 응답을 기다리는 동안 가끔 다시 그려서 처리되게 한다
    ctx.request_repaint_after(Duration::from_millis(500));
    if quit {
        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
    }
}

fn login_window(ctx: &Context, s: &mut State) {
    let mut open = true;
    egui::Window::new("모찌랩 로그인").collapsible(false).resizable(false).anchor(Align2::CENTER_CENTER, [0.0, 0.0]).open(&mut open).show(ctx, |ui| {
        ui.set_width(360.0);
        ui.vertical_centered(|ui| {
            ui.label(RichText::new("모찌랩 계정 연결").size(17.0).strong().color(ACCENT));
            ui.add_space(8.0);
            ui.label(&s.login.info);
            if !s.login.user_code.is_empty() && !s.login.failed {
                ui.add_space(10.0);
                ui.label(RichText::new(&s.login.user_code).size(30.0).strong().monospace());
                ui.add_space(4.0);
                ui.weak("승인을 기다리는 중… (10분 안에 완료해 주세요)");
            }
            ui.add_space(12.0);
            ui.horizontal(|ui| {
                if !s.login.verify_url.is_empty() && ui.button("브라우저 다시 열기").clicked() {
                    open_url(&s.login.verify_url);
                }
                if s.login.failed && ui.button("다시 시도").clicked() {
                    s.start_login();
                }
                if ui.button("닫기").clicked() {
                    s.login.open = false;
                }
            });
        });
    });
    if !open {
        s.login.open = false;
    }
}

fn popup_ad(ctx: &Context, s: &mut State) {
    let Some(ad) = s.popup.clone() else { return };
    let bg = hex(ad["bg_color"].as_str(), ACCENT);
    egui::Area::new(egui::Id::new("mozzi-popup-ad")).anchor(Align2::LEFT_BOTTOM, [16.0, -36.0]).order(egui::Order::Foreground).show(ctx, |ui| {
        egui::Frame::new().fill(Color32::WHITE).stroke(Stroke::new(1.0, Color32::from_gray(220))).corner_radius(CornerRadius::same(12)).inner_margin(12.0).shadow(egui::Shadow { offset: [0, 4], blur: 18, spread: 0, color: Color32::from_black_alpha(60) }).show(ui, |ui| {
            ui.set_width(300.0);
            ui.horizontal(|ui| {
                ui.label(RichText::new("AD").size(10.0).color(Color32::WHITE).background_color(bg));
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui.small_button("닫기").on_hover_text("닫기").clicked() {
                        s.popup = None;
                    }
                });
            });
            ui.label(RichText::new(ad["title"].as_str().unwrap_or("")).size(15.0).strong().color(Color32::from_rgb(0x3b, 0x2f, 0x2f)));
            ui.label(RichText::new(ad["subtitle"].as_str().unwrap_or("")).color(Color32::from_gray(90)));
            ui.add_space(8.0);
            let cta = egui::Button::new(RichText::new(ad["button_text"].as_str().unwrap_or("자세히 알아보기")).color(Color32::WHITE).strong()).fill(bg).corner_radius(CornerRadius::same(8)).min_size(vec2(300.0, 32.0));
            if ui.add(cta).clicked() {
                open_url(ad["click_url"].as_str().or(s.ads["pricing_url"].as_str()).unwrap_or("/pricing"));
                s.popup = None;
            }
        });
    });
}

fn update_window(ctx: &Context, s: &mut State) {
    let mut close = false;
    let mut start = false;
    if let Some(u) = &s.update {
        egui::Window::new("새 버전이 나왔어요").collapsible(false).resizable(false).anchor(Align2::CENTER_CENTER, [0.0, 0.0]).show(ctx, |ui| {
            ui.set_width(380.0);
            ui.label(RichText::new(format!("{APP_NAME} v{} (지금 v{VERSION})", u.tag)).size(15.0).strong());
            if u.mandatory {
                ui.colored_label(ACCENT, "꼭 필요한 업데이트예요.");
            }
            let notes: String = u.notes.lines().take(12).collect::<Vec<_>>().join("\n");
            if !notes.is_empty() {
                egui::ScrollArea::vertical().max_height(160.0).show(ui, |ui| ui.weak(notes));
            }
            if !u.error.is_empty() {
                ui.colored_label(Color32::from_rgb(0xe5, 0x48, 0x4d), &u.error);
            }
            ui.add_space(8.0);
            if u.downloading {
                ui.add(egui::ProgressBar::new(u.progress).show_percentage().text("내려받는 중… 끝나면 자동으로 설치하고 다시 켜져요"));
            } else {
                ui.horizontal(|ui| {
                    if ui.add(egui::Button::new(RichText::new("지금 업데이트").color(Color32::WHITE).strong()).fill(ACCENT)).clicked() {
                        start = true;
                    }
                    if !u.mandatory {
                        if ui.button("나중에").clicked() {
                            close = true;
                        }
                        if ui.button("이 버전 건너뛰기").clicked() {
                            s.cfg["update_skip"] = json!(u.tag);
                            close = true;
                        }
                    }
                });
            }
        });
    }
    if start {
        s.download();
    }
    if close {
        s.save();
        s.update = None;
    }
}

/// 도움말 메뉴 · 정보 창에서 쓰는 '업데이트 확인'
pub fn check_update_now() {
    with(|s| s.check_update(true));
}

pub fn is_premium() -> bool {
    with(|s| s.premium())
}
