// 요청마다 함께 쓰는 정보와 도우미 함수
import type { Context } from "hono";
import { saveSession, setFlash, takeFlash, type Session } from "./auth";
import { tossEnabled } from "./billing";
import type { Env, User } from "./db";
import type { PageCtx } from "./views/layout";

export type AppEnv = {
  Bindings: Env;
  Variables: { session: Session; user: User | null; premium: boolean; settings: Record<string, string> };
};
export type C = Context<AppEnv>;

export function pageCtx(c: C): PageCtx {
  return {
    me: c.get("user"),
    premium: c.get("premium"),
    csrf: c.get("session").csrf,
    s: c.get("settings"),
    testMode: !tossEnabled(c.env),
    flashes: takeFlash(c),
    path: new URL(c.req.url).pathname,
    company: c.env.COMPANY_NAME || "모찌랩",
    email: c.env.SUPPORT_EMAIL || "help@labelpos.com",
  };
}

/** 사이트 주소. 설정(SITE_URL)이 있으면 그것, 없으면 지금 접속한 주소 */
export function siteUrl(c: C): string {
  return (c.env.SITE_URL || new URL(c.req.url).origin).replace(/\/$/, "");
}

export function flashRedirect(c: C, kind: "success" | "error" | "info", msg: string, to: string) {
  setFlash(c, kind, msg);
  return c.redirect(to);
}

export async function login(c: C, user: User) {
  const s: Session = { uid: user.id, csrf: c.get("session").csrf, exp: Date.now() + 30 * 86400_000 };
  c.set("session", s);
  await saveSession(c, s);
  await c.env.DB.prepare("UPDATE users SET last_login_at = ? WHERE id = ?").bind(new Date().toISOString(), user.id).run();
}

export async function form(c: C): Promise<Record<string, string>> {
  const body = await c.req.parseBody();
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(body)) if (typeof v === "string") out[k] = v;
  return out;
}

export function pageOf(c: C): number {
  return Math.max(1, Number(c.req.query("page") || 1) || 1);
}
export const PER_PAGE = 20;
