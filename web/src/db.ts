// 데이터베이스(Cloudflare D1) - 표 만들기, 기본 데이터, 자주 쓰는 조회 함수
import { hashPassword } from "./auth";

export interface Env {
  DB: D1Database;
  ASSETS: Fetcher;
  SITE_URL: string;
  COMPANY_NAME?: string;
  SUPPORT_EMAIL?: string;
  CAPTURE_DOWNLOAD_URL?: string;
  SECRET_KEY?: string;
  ADMIN_EMAIL?: string;
  ADMIN_PASSWORD?: string;
  TOSS_CLIENT_KEY?: string;
  TOSS_SECRET_KEY?: string;
  NAVER_CLIENT_ID?: string;
  NAVER_CLIENT_SECRET?: string;
  KAKAO_CLIENT_ID?: string;
  KAKAO_CLIENT_SECRET?: string;
  GOOGLE_CLIENT_ID?: string;
  GOOGLE_CLIENT_SECRET?: string;
}

export interface User {
  id: number; email: string; password_hash: string | null; name: string; provider: string;
  provider_id: string | null; role: string; status: string; marketing: number; memo: string;
  created_at: string; last_login_at: string | null;
}
export interface Subscription {
  id: number; user_id: number; plan: string; status: string; price: number; method: string;
  billing_key: string | null; customer_key: string | null; card_info: string; started_at: string;
  current_period_end: string | null; canceled_at: string | null; note: string; created_at: string;
  email?: string;
}
export interface Payment {
  id: number; user_id: number; subscription_id: number | null; amount: number; status: string;
  order_id: string; order_name: string; payment_key: string | null; method: string; card: string;
  fail_reason: string; paid_at: string; refunded_at: string | null; email?: string;
}
export interface Device {
  id: number; user_id: number; device_id: string; device_name: string; app: string; app_version: string;
  token_hash: string; created_at: string; last_seen_at: string; revoked: number; email?: string;
}
export interface DeviceCode {
  id: number; device_code: string; user_code: string; device_id: string; device_name: string; app: string;
  app_version: string; status: string; user_id: number | null; token: string | null; created_at: string; expires_at: string;
}
export interface Ad {
  id: number; title: string; subtitle: string; image: string; link_url: string; button_text: string;
  placement: string; apps: string; bg_color: string; weight: number; active: number;
  start_at: string | null; end_at: string | null; views: number; clicks: number; created_at: string;
}
export interface Product {
  id: number; slug: string; name: string; tagline: string; description: string; version: string;
  download_url: string; status: string; color: string; sort: number; downloads: number;
}

// ---------- 시간 ----------
export const now = () => new Date().toISOString();

export function addMonths(iso: string, months: number): string {
  const d = new Date(iso);
  const day = d.getUTCDate();
  d.setUTCDate(1);
  d.setUTCMonth(d.getUTCMonth() + months);
  const last = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
  d.setUTCDate(Math.min(day, last));
  return d.toISOString();
}

export function addMinutes(iso: string, minutes: number): string {
  return new Date(new Date(iso).getTime() + minutes * 60_000).toISOString();
}

// 화면 표시는 한국 시간(UTC+9)
export function fmt(iso: string | null | undefined, kind: "datetime" | "date" | "short" | "korean" = "datetime"): string {
  if (!iso) return "-";
  const d = new Date(new Date(iso).getTime() + 9 * 3600_000);
  const p = (n: number) => String(n).padStart(2, "0");
  const Y = d.getUTCFullYear(), M = p(d.getUTCMonth() + 1), D = p(d.getUTCDate()), h = p(d.getUTCHours()), m = p(d.getUTCMinutes());
  if (kind === "date") return `${Y}-${M}-${D}`;
  if (kind === "short") return `${M}-${D} ${h}:${m}`;
  if (kind === "korean") return `${Y}년 ${M}월 ${D}일`;
  return `${Y}-${M}-${D} ${h}:${m}`;
}

export const won = (v: number | null | undefined) => `${Number(v || 0).toLocaleString("ko-KR")}원`;

// ---------- 표 만들기 ----------
const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
    password_hash TEXT, name TEXT DEFAULT '', provider TEXT DEFAULT 'email', provider_id TEXT,
    role TEXT DEFAULT 'user', status TEXT DEFAULT 'active', marketing INTEGER DEFAULT 0, memo TEXT DEFAULT '',
    created_at TEXT, last_login_at TEXT)`,
  `CREATE INDEX IF NOT EXISTS idx_users_provider ON users(provider, provider_id)`,
  `CREATE TABLE IF NOT EXISTS subscriptions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
    plan TEXT DEFAULT 'plus', status TEXT DEFAULT 'active', price INTEGER DEFAULT 5500, method TEXT DEFAULT 'toss',
    billing_key TEXT, customer_key TEXT, card_info TEXT DEFAULT '', started_at TEXT, current_period_end TEXT,
    canceled_at TEXT, note TEXT DEFAULT '', created_at TEXT)`,
  `CREATE INDEX IF NOT EXISTS idx_subs_user ON subscriptions(user_id)`,
  `CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
    subscription_id INTEGER, amount INTEGER DEFAULT 0, status TEXT DEFAULT 'paid', order_id TEXT UNIQUE,
    order_name TEXT DEFAULT '', payment_key TEXT, method TEXT DEFAULT 'toss', card TEXT DEFAULT '',
    fail_reason TEXT DEFAULT '', paid_at TEXT, refunded_at TEXT)`,
  `CREATE INDEX IF NOT EXISTS idx_pay_user ON payments(user_id)`,
  `CREATE TABLE IF NOT EXISTS devices (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
    device_id TEXT, device_name TEXT DEFAULT '', app TEXT DEFAULT 'capture', app_version TEXT DEFAULT '',
    token_hash TEXT UNIQUE, created_at TEXT, last_seen_at TEXT, revoked INTEGER DEFAULT 0)`,
  `CREATE INDEX IF NOT EXISTS idx_dev_user ON devices(user_id)`,
  `CREATE TABLE IF NOT EXISTS device_codes (id INTEGER PRIMARY KEY AUTOINCREMENT, device_code TEXT UNIQUE,
    user_code TEXT UNIQUE, device_id TEXT, device_name TEXT DEFAULT '', app TEXT DEFAULT 'capture',
    app_version TEXT DEFAULT '', status TEXT DEFAULT 'pending', user_id INTEGER, token TEXT, created_at TEXT, expires_at TEXT)`,
  `CREATE TABLE IF NOT EXISTS ads (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, subtitle TEXT DEFAULT '',
    image TEXT DEFAULT '', link_url TEXT DEFAULT '', button_text TEXT DEFAULT '자세히 알아보기', placement TEXT DEFAULT 'banner',
    apps TEXT DEFAULT 'all', bg_color TEXT DEFAULT '#ff6f91', weight INTEGER DEFAULT 1, active INTEGER DEFAULT 1,
    start_at TEXT, end_at TEXT, views INTEGER DEFAULT 0, clicks INTEGER DEFAULT 0, created_at TEXT)`,
  `CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE, name TEXT,
    tagline TEXT DEFAULT '', description TEXT DEFAULT '', version TEXT DEFAULT '1.0.0', download_url TEXT DEFAULT '',
    status TEXT DEFAULT 'released', color TEXT DEFAULT '#ff6f91', sort INTEGER DEFAULT 0, downloads INTEGER DEFAULT 0)`,
  `CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT DEFAULT '')`,
  `CREATE TABLE IF NOT EXISTS files (id TEXT PRIMARY KEY, content_type TEXT, data BLOB, created_at TEXT)`,
];

let ready = false;

export async function ensureSchema(env: Env) {
  if (ready) return;
  await env.DB.batch(SCHEMA.map((s) => env.DB.prepare(s)));
  await seed(env);
  ready = true;
}

async function seed(env: Env) {
  const t = now();
  // 관리자: ADMIN_EMAIL 계정을 관리자로 (없으면 ADMIN_PASSWORD 로 새로 만듦)
  const adminEmail = (env.ADMIN_EMAIL || "").trim().toLowerCase();
  if (adminEmail) {
    const u = await env.DB.prepare("SELECT id, role FROM users WHERE email = ?").bind(adminEmail).first<{ id: number; role: string }>();
    if (u && u.role !== "admin") {
      await env.DB.prepare("UPDATE users SET role = 'admin' WHERE id = ?").bind(u.id).run();
    } else if (!u && env.ADMIN_PASSWORD) {
      await env.DB.prepare("INSERT INTO users (email, name, password_hash, role, created_at) VALUES (?, '관리자', ?, 'admin', ?)")
        .bind(adminEmail, await hashPassword(env.ADMIN_PASSWORD), t).run();
    }
  }
  const pc = await env.DB.prepare("SELECT COUNT(*) AS n FROM products").first<{ n: number }>();
  if (!pc?.n) {
    const ins = "INSERT INTO products (slug, name, sort, status, version, color, tagline, description, download_url) VALUES (?,?,?,?,?,?,?,?,?)";
    await env.DB.batch([
      env.DB.prepare(ins).bind("capture", "모찌캡처", 1, "released", "1.0.0", "#ff6f91", "클릭 한 번으로 쏙! 말랑한 화면 캡처",
        "직접지정 · 창 · 단위영역 · 전체화면 · 스크롤 · 크기지정 캡처와 도형·펜·모자이크 편집까지 한 번에.",
        env.CAPTURE_DOWNLOAD_URL || "https://github.com/kiha797/mozzilab/releases/latest/download/MochiCapture_Setup.exe"),
      env.DB.prepare(ins).bind("pdf", "모찌PDF", 2, "released", "1.0.0", "#7ec8a9", "PDF 변환·합치기·나누기를 말랑하게",
        "합치기 · 나누기 · 페이지 회전/삭제/순서 바꾸기 · 이미지→PDF · PDF→이미지 · 용량 줄이기 · 암호 걸기/풀기.",
        "https://github.com/kiha797/mozzilab/releases/latest/download/MochiPDF_Setup.exe"),
      env.DB.prepare(ins).bind("zip", "모찌압축", 3, "released", "1.0.0", "#ffb86b", "꾹 눌러 담는 압축 프로그램",
        "ZIP · 7Z 압축하기/풀기 · TAR 풀기 · 암호(AES-256) · 한글 이름 깨진 ZIP 복구 · 마우스 오른쪽 메뉴로 바로 풀기.",
        "https://github.com/kiha797/mozzilab/releases/latest/download/MochiZip_Setup.exe"),
      env.DB.prepare(ins).bind("photo", "모찌포토", 4, "released", "1.1.0", "#8a6cf0", "포토샵처럼 말랑하게, 사진 편집",
        "레이어 · 혼합 모드 · 브러시 · 선택(마술봉·올가미) · 복제 도장 · 색 보정 · 필터 · PSD 열기/저장.",
        "https://github.com/kiha797/mozzilab/releases/latest/download/MochiPhoto_Setup.exe"),
      env.DB.prepare(ins).bind("vector", "모찌벡터", 5, "released", "1.1.0", "#2f9be8", "일러스트처럼 쓱쓱, 벡터 디자인",
        "펜(베지어) · 도형 · 문자 · 그룹 · 정렬 · 패스파인더 · 그레이디언트 · SVG/PDF/PNG 내보내기.",
        "https://github.com/kiha797/mozzilab/releases/latest/download/MochiVector_Setup.exe"),
    ]);
  }
  const ac = await env.DB.prepare("SELECT COUNT(*) AS n FROM ads").first<{ n: number }>();
  if (!ac?.n) {
    const ins = "INSERT INTO ads (title, subtitle, link_url, placement, bg_color, button_text, created_at) VALUES (?,?,?,?,?,?,?)";
    await env.DB.batch([
      env.DB.prepare(ins).bind("광고 없이 쾌적하게, 모찌 플러스", "월 5,500원으로 모든 모찌랩 광고 제거", "/pricing", "banner", "#ff6f91", "구독하기", t),
      env.DB.prepare(ins).bind("모찌PDF 곧 출시!", "PDF 변환·합치기를 무료로", "/products/pdf", "banner", "#7ec8a9", "자세히 알아보기", t),
      env.DB.prepare(ins).bind("광고가 신경 쓰이나요?", "모찌 플러스로 광고 없이 캡처하세요. 언제든 해지 가능!", "/pricing", "popup", "#ff8fab", "광고 없이 쓰기", t),
    ]);
  }
}

// ---------- 설정 ----------
export const SETTING_DEFAULTS: Record<string, string> = {
  plan_name: "모찌 플러스",
  price: "5500",
  device_limit: "3",
  popup_every: "1",
};

export async function getSettings(env: Env): Promise<Record<string, string>> {
  const rows = await env.DB.prepare("SELECT key, value FROM settings").all<{ key: string; value: string }>();
  const s = { ...SETTING_DEFAULTS };
  for (const r of rows.results) if (!r.key.startsWith("_")) s[r.key] = r.value;   // _ 로 시작하는 값(암호키)은 화면에 쓰지 않음
  return s;
}

export async function setSetting(env: Env, key: string, value: string) {
  await env.DB.prepare("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value")
    .bind(key, value).run();
}

// ---------- 조회 ----------
export const getUser = (env: Env, id: number) =>
  env.DB.prepare("SELECT * FROM users WHERE id = ?").bind(id).first<User>();

export const getUserByEmail = (env: Env, email: string) =>
  env.DB.prepare("SELECT * FROM users WHERE email = ?").bind(email.toLowerCase()).first<User>();

export const validSubscription = (env: Env, userId: number) =>
  env.DB.prepare(`SELECT * FROM subscriptions WHERE user_id = ? AND status IN ('active','canceled','past_due')
    AND current_period_end > ? ORDER BY id DESC LIMIT 1`).bind(userId, now()).first<Subscription>();

export async function premiumUserIds(env: Env): Promise<Set<number>> {
  const r = await env.DB.prepare(`SELECT DISTINCT user_id FROM subscriptions WHERE status IN ('active','canceled','past_due')
    AND current_period_end > ?`).bind(now()).all<{ user_id: number }>();
  return new Set(r.results.map((x) => x.user_id));
}

export const activeDevices = async (env: Env, userId: number) =>
  (await env.DB.prepare("SELECT * FROM devices WHERE user_id = ? AND revoked = 0 ORDER BY id DESC").bind(userId).all<Device>()).results;

export const SUB_STATUS: Record<string, string> = { active: "이용 중", canceled: "해지 예약", past_due: "결제 실패", expired: "종료" };
export const SUB_METHOD: Record<string, string> = { toss: "카드 자동결제", test: "테스트 결제", manual: "관리자 부여" };
export const PAY_STATUS: Record<string, string> = { paid: "결제 완료", failed: "결제 실패", refunded: "환불" };
export const APP_NAMES: Record<string, string> = { capture: "모찌캡처", pdf: "모찌PDF", zip: "모찌압축", photo: "모찌포토", vector: "모찌벡터" };

export function adRunning(ad: Ad): boolean {
  const t = now();
  return !!ad.active && (!ad.start_at || ad.start_at <= t) && (!ad.end_at || ad.end_at >= t);
}
