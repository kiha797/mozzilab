// 비밀번호 암호화, 로그인 세션(쿠키), 폼 보안(CSRF), 소셜 로그인(네이버/카카오/구글)
import type { Context } from "hono";
import { getCookie, setCookie, deleteCookie } from "hono/cookie";
import type { Env, User } from "./db";

const enc = new TextEncoder();

function b64url(bytes: Uint8Array): string {
  let s = "";
  bytes.forEach((b) => (s += String.fromCharCode(b)));
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function fromB64url(s: string): Uint8Array {
  const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4));
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

export function randomToken(bytes = 32): string {
  return b64url(crypto.getRandomValues(new Uint8Array(bytes)));
}

export async function sha256(text: string): Promise<string> {
  const d = await crypto.subtle.digest("SHA-256", enc.encode(text));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// ---------- 비밀번호 (PBKDF2) ----------
const ITER = 50_000;

async function pbkdf2(password: string, salt: Uint8Array, iterations: number): Promise<Uint8Array> {
  const key = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt, iterations }, key, 256);
  return new Uint8Array(bits);
}

export async function hashPassword(password: string): Promise<string> {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  return `pbkdf2$${ITER}$${b64url(salt)}$${b64url(await pbkdf2(password, salt, ITER))}`;
}

export async function verifyPassword(password: string, stored: string | null): Promise<boolean> {
  if (!stored) return false;
  const [kind, iter, salt, hash] = stored.split("$");
  if (kind !== "pbkdf2") return false;
  const out = b64url(await pbkdf2(password, fromB64url(salt), Number(iter)));
  return safeEqual(out, hash);
}

export function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// ---------- 세션 쿠키 (서명해서 위조 방지) ----------
export interface Session { uid?: number; csrf: string; exp: number; oauth_state?: string; next?: string }

async function hmac(secret: string, data: string): Promise<string> {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return b64url(new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(data))));
}

const COOKIE = "ml_sess";
const secretOf = (env: Env) => env.SECRET_KEY || "dev-change-me";

export async function loadSession(c: Context<any>): Promise<Session> {
  const raw = getCookie(c, COOKIE);
  if (raw && raw.includes(".")) {
    const [body, sig] = raw.split(".");
    if ((await hmac(secretOf(c.env), body)) === sig) {
      try {
        const s = JSON.parse(new TextDecoder().decode(fromB64url(body))) as Session;
        if (s.exp > Date.now()) return s;
      } catch { /* 깨진 쿠키는 무시 */ }
    }
  }
  return { csrf: randomToken(18), exp: Date.now() + 30 * 86400_000 };
}

export async function saveSession(c: Context<any>, s: Session) {
  const body = b64url(enc.encode(JSON.stringify(s)));
  setCookie(c, COOKIE, `${body}.${await hmac(secretOf(c.env), body)}`, {
    path: "/", httpOnly: true, sameSite: "Lax", secure: c.req.url.startsWith("https://"), maxAge: 30 * 86400,
  });
}

// ---------- 한 번만 보여주는 알림 (flash) ----------
export type Flash = [string, string];

export function setFlash(c: Context, kind: "success" | "error" | "info", msg: string) {
  const prev = readFlashRaw(c);
  prev.push([kind, msg]);
  setCookie(c, "ml_flash", b64url(enc.encode(JSON.stringify(prev))), { path: "/", httpOnly: true, sameSite: "Lax" });
}
function readFlashRaw(c: Context): Flash[] {
  const raw = getCookie(c, "ml_flash");
  if (!raw) return [];
  try { return JSON.parse(new TextDecoder().decode(fromB64url(raw))); } catch { return []; }
}
export function takeFlash(c: Context): Flash[] {
  const f = readFlashRaw(c);
  if (f.length) deleteCookie(c, "ml_flash", { path: "/" });
  return f;
}

export function safeNext(v: string | undefined | null, fallback = "/"): string {
  return v && v.startsWith("/") && !v.startsWith("//") ? v : fallback;
}

// ---------- 소셜 로그인 ----------
export const PROVIDERS: Record<string, { name: string; auth: string; token: string; me: string; scope: string }> = {
  naver: { name: "네이버", auth: "https://nid.naver.com/oauth2.0/authorize", token: "https://nid.naver.com/oauth2.0/token",
    me: "https://openapi.naver.com/v1/nid/me", scope: "" },
  kakao: { name: "카카오", auth: "https://kauth.kakao.com/oauth/authorize", token: "https://kauth.kakao.com/oauth/token",
    me: "https://kapi.kakao.com/v2/user/me", scope: "account_email profile_nickname" },
  google: { name: "구글", auth: "https://accounts.google.com/o/oauth2/v2/auth", token: "https://oauth2.googleapis.com/token",
    me: "https://openidconnect.googleapis.com/v1/userinfo", scope: "openid email profile" },
};

export function providerKeys(env: Env, p: string): [string, string] {
  const e = env as unknown as Record<string, string | undefined>;
  return [e[`${p.toUpperCase()}_CLIENT_ID`] || "", e[`${p.toUpperCase()}_CLIENT_SECRET`] || ""];
}
export function providerEnabled(env: Env, p: string): boolean {
  const [id, secret] = providerKeys(env, p);
  return !!id && (!!secret || p === "kakao");
}

export interface OAuthProfile { pid: string; email: string | null; name: string | null }

export async function oauthProfile(env: Env, p: string, code: string, state: string, redirectUri: string): Promise<OAuthProfile | null> {
  const cfg = PROVIDERS[p];
  const [id, secret] = providerKeys(env, p);
  const form = new URLSearchParams({ grant_type: "authorization_code", client_id: id, code, redirect_uri: redirectUri, state });
  if (secret) form.set("client_secret", secret);
  const tok = (await (await fetch(cfg.token, { method: "POST", body: form })).json()) as Record<string, string>;
  if (!tok.access_token) return null;
  const me = (await (await fetch(cfg.me, { headers: { Authorization: `Bearer ${tok.access_token}` } })).json()) as any;
  if (p === "naver") {
    const r = me.response || {};
    return r.id ? { pid: r.id, email: r.email || null, name: r.name || r.nickname || null } : null;
  }
  if (p === "kakao") {
    const acc = me.kakao_account || {};
    return me.id ? { pid: String(me.id), email: acc.email || null, name: acc.profile?.nickname || null } : null;
  }
  return me.sub ? { pid: me.sub, email: me.email || null, name: me.name || null } : null;
}

export const displayName = (u: Pick<User, "name" | "email">) => u.name || u.email.split("@")[0];
