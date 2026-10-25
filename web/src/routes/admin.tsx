// 관리자 사이트 (/admin) - 대시보드, 회원, 구독, 결제, 기기(라이선스), 광고, 제품, 설정
import { Hono } from "hono";
import { randomToken } from "../auth";
import { refund, renewDue, tossEnabled } from "../billing";
import { addMonths, now, premiumUserIds, setSetting, validSubscription,
  type Ad, type Device, type Payment, type Product, type Subscription, type User } from "../db";
import { type AppEnv, type C, flashRedirect, form, pageCtx, pageOf, PER_PAGE } from "../ctx";
import * as A from "../views/admin";
import { ErrorPage } from "../views/pages";

const admin = new Hono<AppEnv>();
const MAX_IMG = 1024 * 1024;

admin.use("*", async (c, next) => {
  const user = c.get("user");
  if (!user) return c.redirect(`/login?next=${encodeURIComponent(new URL(c.req.url).pathname)}`);
  if (user.role !== "admin") return c.html(<ErrorPage c={pageCtx(c)} code={403} msg="관리자만 볼 수 있는 페이지입니다." />, 403);
  await next();
});

const count = async (c: C, sql: string, ...args: unknown[]) =>
  (await c.env.DB.prepare(sql).bind(...args).first<{ n: number }>())?.n || 0;

/** 한국 시간 기준 이번 달 1일 0시 (UTC ISO) */
function monthStartKst(offset = 0): string {
  const k = new Date(Date.now() + 9 * 3600_000);
  return new Date(Date.UTC(k.getUTCFullYear(), k.getUTCMonth() + offset, 1) - 9 * 3600_000).toISOString();
}

// ---------- 대시보드 ----------
admin.get("/", async (c) => {
  const ms = monthStartKst();
  const premiumIds = await premiumUserIds(c.env);
  const users = await count(c, "SELECT COUNT(*) n FROM users");
  const ad = await c.env.DB.prepare("SELECT COALESCE(SUM(views),0) v, COALESCE(SUM(clicks),0) k FROM ads").first<{ v: number; k: number }>();
  const stats: A.Stats = {
    users,
    new_users: await count(c, "SELECT COUNT(*) n FROM users WHERE created_at >= ?", ms),
    premium: premiumIds.size,
    revenue_month: await count(c, "SELECT COALESCE(SUM(amount),0) n FROM payments WHERE status='paid' AND paid_at >= ?", ms),
    devices: await count(c, "SELECT COUNT(*) n FROM devices WHERE revoked = 0"),
    ad_views: ad?.v || 0, ad_clicks: ad?.k || 0,
    failed: await count(c, "SELECT COUNT(*) n FROM subscriptions WHERE status = 'past_due'"),
    mrr: premiumIds.size * Number(c.get("settings").price),
    conversion: users ? Math.round((premiumIds.size * 1000) / users) / 10 : 0,
  };
  const months: A.Month[] = [];
  for (let i = 5; i >= 0; i--) {
    const start = monthStartKst(-i), end = monthStartKst(-i + 1);
    const label = `${new Date(new Date(start).getTime() + 9 * 3600_000).getUTCMonth() + 1}월`;
    months.push({
      label,
      revenue: await count(c, "SELECT COALESCE(SUM(amount),0) n FROM payments WHERE status='paid' AND paid_at >= ? AND paid_at < ?", start, end),
      signups: await count(c, "SELECT COUNT(*) n FROM users WHERE created_at >= ? AND created_at < ?", start, end),
    });
  }
  const recentUsers = (await c.env.DB.prepare("SELECT * FROM users ORDER BY id DESC LIMIT 6").all<User>()).results;
  const recentPayments = (await c.env.DB.prepare("SELECT p.*, u.email FROM payments p JOIN users u ON u.id = p.user_id ORDER BY p.id DESC LIMIT 6").all<Payment>()).results;
  return c.html(<A.Dashboard c={pageCtx(c)} stats={stats} months={months} recentUsers={recentUsers} premiumIds={premiumIds} recentPayments={recentPayments} />);
});

admin.post("/renew-now", async (c) => {
  const r = await renewDue(c.env);
  return flashRedirect(c, "success", `정기결제 실행 완료: 갱신 ${r.renewed}건 · 실패 ${r.failed}건 · 종료 ${r.expired}건`, "/admin");
});

// ---------- 회원 ----------
admin.get("/users", async (c) => {
  const kw = (c.req.query("q") || "").trim();
  const kind = c.req.query("kind") || "";
  const premiumIds = await premiumUserIds(c.env);
  const where: string[] = [];
  const args: unknown[] = [];
  if (kw) { where.push("(email LIKE ? OR name LIKE ?)"); args.push(`%${kw}%`, `%${kw}%`); }
  if (kind === "admin") where.push("role = 'admin'");
  if (kind === "suspended") where.push("status = 'suspended'");
  const ids = [...premiumIds].map(Number).filter(Number.isFinite);
  if (kind === "premium") where.push(ids.length ? `id IN (${ids.join(",")})` : "0");
  if (kind === "free" && ids.length) where.push(`id NOT IN (${ids.join(",")})`);
  const w = where.length ? `WHERE ${where.join(" AND ")}` : "";
  const total = await count(c, `SELECT COUNT(*) n FROM users ${w}`, ...args);
  const page = pageOf(c);
  const items = (await c.env.DB.prepare(`SELECT * FROM users ${w} ORDER BY id DESC LIMIT ? OFFSET ?`).bind(...args, PER_PAGE, (page - 1) * PER_PAGE).all<User>()).results;
  const dc = (await c.env.DB.prepare("SELECT user_id, COUNT(*) n FROM devices WHERE revoked = 0 GROUP BY user_id").all<{ user_id: number; n: number }>()).results;
  return c.html(<A.Users c={pageCtx(c)} items={items} premiumIds={premiumIds} deviceCounts={new Map(dc.map((x) => [x.user_id, x.n]))}
    kw={kw} kind={kind} page={page} pages={Math.ceil(total / PER_PAGE)} />);
});

admin.get("/users/:id", async (c) => {
  const id = Number(c.req.param("id"));
  const db = c.env.DB;
  const u = await db.prepare("SELECT * FROM users WHERE id = ?").bind(id).first<User>();
  if (!u) return c.notFound();
  const [sub, subs, devices, payments] = await Promise.all([
    validSubscription(c.env, id),
    db.prepare("SELECT * FROM subscriptions WHERE user_id = ? ORDER BY id DESC").bind(id).all<Subscription>(),
    db.prepare("SELECT * FROM devices WHERE user_id = ? ORDER BY id DESC").bind(id).all<Device>(),
    db.prepare("SELECT * FROM payments WHERE user_id = ? ORDER BY id DESC").bind(id).all<Payment>(),
  ]);
  return c.html(<A.UserDetail c={pageCtx(c)} u={u} sub={sub} subs={subs.results} devices={devices.results} payments={payments.results} />);
});

admin.post("/users/:id/update", async (c) => {
  const id = Number(c.req.param("id"));
  const f = await form(c);
  await c.env.DB.prepare("UPDATE users SET name = ?, role = ?, status = ?, memo = ? WHERE id = ?")
    .bind(f.name || "", f.role === "admin" ? "admin" : "user", f.status === "suspended" ? "suspended" : "active", f.memo || "", id).run();
  return flashRedirect(c, "success", "회원 정보를 저장했습니다.", `/admin/users/${id}`);
});

admin.post("/users/:id/grant", async (c) => {
  const id = Number(c.req.param("id"));
  const f = await form(c);
  const months = Math.max(1, Math.min(120, Number(f.months) || 1));
  const sub = await validSubscription(c.env, id);
  let msg: string;
  if (sub) {
    await c.env.DB.prepare("UPDATE subscriptions SET current_period_end = ? WHERE id = ?").bind(addMonths(sub.current_period_end!, months), sub.id).run();
    msg = `이용 기간을 ${months}개월 연장했습니다.`;
  } else {
    const t = now();
    await c.env.DB.prepare(`INSERT INTO subscriptions (user_id, method, status, price, started_at, current_period_end, note, created_at)
      VALUES (?, 'manual', 'canceled', 0, ?, ?, ?, ?)`).bind(id, t, addMonths(t, months), f.note || "관리자 부여", t).run();
    msg = `${months}개월 이용권을 부여했습니다. (자동결제 없음)`;
  }
  return flashRedirect(c, "success", msg, `/admin/users/${id}`);
});

admin.post("/users/:id/end-sub", async (c) => {
  const id = Number(c.req.param("id"));
  const sub = await validSubscription(c.env, id);
  if (sub) {
    const t = now();
    await c.env.DB.prepare("UPDATE subscriptions SET status = 'expired', current_period_end = ?, canceled_at = ? WHERE id = ?").bind(t, t, sub.id).run();
  }
  return flashRedirect(c, "success", "구독을 즉시 종료했습니다. (환불은 결제 내역에서 따로 처리하세요)", `/admin/users/${id}`);
});

admin.post("/users/:id/revoke-devices", async (c) => {
  const id = Number(c.req.param("id"));
  await c.env.DB.prepare("UPDATE devices SET revoked = 1 WHERE user_id = ?").bind(id).run();
  return flashRedirect(c, "success", "모든 PC 로그인을 해제했습니다.", `/admin/users/${id}`);
});

// ---------- 구독 / 결제 / 기기 ----------
admin.get("/subscriptions", async (c) => {
  const st = c.req.query("status") || "";
  const w = st ? "WHERE s.status = ?" : "";
  const args = st ? [st] : [];
  const page = pageOf(c);
  const total = await count(c, `SELECT COUNT(*) n FROM subscriptions s ${w}`, ...args);
  const items = (await c.env.DB.prepare(`SELECT s.*, u.email FROM subscriptions s JOIN users u ON u.id = s.user_id ${w} ORDER BY s.id DESC LIMIT ? OFFSET ?`)
    .bind(...args, PER_PAGE, (page - 1) * PER_PAGE).all<Subscription>()).results;
  return c.html(<A.Subscriptions c={pageCtx(c)} items={items} status={st} page={page} pages={Math.ceil(total / PER_PAGE)} />);
});

admin.get("/payments", async (c) => {
  const st = c.req.query("status") || "";
  const w = st ? "WHERE p.status = ?" : "";
  const args = st ? [st] : [];
  const page = pageOf(c);
  const total = await count(c, `SELECT COUNT(*) n FROM payments p ${w}`, ...args);
  const sum = await count(c, "SELECT COALESCE(SUM(amount),0) n FROM payments WHERE status = 'paid'");
  const items = (await c.env.DB.prepare(`SELECT p.*, u.email FROM payments p JOIN users u ON u.id = p.user_id ${w} ORDER BY p.id DESC LIMIT ? OFFSET ?`)
    .bind(...args, PER_PAGE, (page - 1) * PER_PAGE).all<Payment>()).results;
  return c.html(<A.Payments c={pageCtx(c)} items={items} status={st} total={sum} page={page} pages={Math.ceil(total / PER_PAGE)} />);
});

admin.post("/payments/:id/refund", async (c) => {
  const pay = await c.env.DB.prepare("SELECT * FROM payments WHERE id = ?").bind(Number(c.req.param("id"))).first<Payment>();
  if (!pay || pay.status !== "paid") return flashRedirect(c, "error", "결제 완료 상태만 환불할 수 있습니다.", "/admin/payments");
  const r = await refund(c.env, pay);
  return r.ok ? flashRedirect(c, "success", "환불 처리했습니다.", "/admin/payments") : flashRedirect(c, "error", `환불 실패: ${r.reason}`, "/admin/payments");
});

admin.get("/devices", async (c) => {
  const show = c.req.query("show") || "";
  const w = show === "all" ? "" : "WHERE d.revoked = 0";
  const page = pageOf(c);
  const total = await count(c, `SELECT COUNT(*) n FROM devices d ${w}`);
  const items = (await c.env.DB.prepare(`SELECT d.*, u.email FROM devices d JOIN users u ON u.id = d.user_id ${w} ORDER BY d.last_seen_at DESC LIMIT ? OFFSET ?`)
    .bind(PER_PAGE, (page - 1) * PER_PAGE).all<Device>()).results;
  return c.html(<A.Devices c={pageCtx(c)} items={items} premiumIds={await premiumUserIds(c.env)} show={show} page={page} pages={Math.ceil(total / PER_PAGE)} />);
});

admin.post("/devices/:id/revoke", async (c) => {
  await c.env.DB.prepare("UPDATE devices SET revoked = 1 WHERE id = ?").bind(Number(c.req.param("id"))).run();
  return flashRedirect(c, "success", "기기 로그인을 해제했습니다.", c.req.header("Referer") || "/admin/devices");
});

// ---------- 광고 ----------
admin.get("/ads", async (c) => {
  const items = (await c.env.DB.prepare("SELECT * FROM ads ORDER BY active DESC, id DESC").all<Ad>()).results;
  return c.html(<A.Ads c={pageCtx(c)} items={items} />);
});

const NEW_AD: Partial<Ad> = { active: 1, weight: 1, placement: "banner", apps: "all", bg_color: "#ff6f91", button_text: "자세히 알아보기" };

admin.get("/ads/new", (c) => c.html(<A.AdEdit c={pageCtx(c)} ad={NEW_AD} />));
admin.get("/ads/:id", async (c) => {
  const ad = await c.env.DB.prepare("SELECT * FROM ads WHERE id = ?").bind(Number(c.req.param("id"))).first<Ad>();
  return ad ? c.html(<A.AdEdit c={pageCtx(c)} ad={ad} />) : c.notFound();
});

/** 날짜 입력(YYYY-MM-DD, 한국 날짜)을 UTC ISO 로. 종료일은 그날 23:59 까지 */
function kstDate(v: string | undefined, endOfDay = false): string | null {
  if (!v || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return null;
  const t = Date.parse(`${v}T00:00:00+09:00`) + (endOfDay ? 86400_000 - 60_000 : 0);
  return new Date(t).toISOString();
}

async function saveAd(c: C, id: number | null) {
  const body = await c.req.parseBody();
  const f: Record<string, string> = {};
  for (const [k, v] of Object.entries(body)) if (typeof v === "string") f[k] = v;
  const old = id ? await c.env.DB.prepare("SELECT * FROM ads WHERE id = ?").bind(id).first<Ad>() : null;
  let image = old?.image || "";
  if ((f.image_url || "").trim()) image = f.image_url.trim();
  const file = body.image_file;
  if (file instanceof File && file.size > 0) {
    if (!/^image\/(png|jpe?g|gif|webp)$/.test(file.type)) return flashRedirect(c, "error", "이미지는 png, jpg, gif, webp 파일만 올릴 수 있습니다.", c.req.path);
    if (file.size > MAX_IMG) return flashRedirect(c, "error", "이미지는 1MB 이하로 올려 주세요.", c.req.path);
    image = randomToken(12);
    await c.env.DB.prepare("INSERT INTO files (id, content_type, data, created_at) VALUES (?,?,?,?)")
      .bind(image, file.type, await file.arrayBuffer(), now()).run();
  }
  if (f.remove_image) image = "";
  const vals = [(f.title || "").trim() || "광고", (f.subtitle || "").trim(), image, (f.link_url || "").trim(),
    (f.button_text || "").trim() || "자세히 알아보기", f.placement === "popup" ? "popup" : "banner", f.apps || "all",
    f.bg_color || "#ff6f91", Math.max(1, Number(f.weight) || 1), f.active ? 1 : 0, kstDate(f.start_at), kstDate(f.end_at, true)];
  if (old) {
    await c.env.DB.prepare(`UPDATE ads SET title=?, subtitle=?, image=?, link_url=?, button_text=?, placement=?, apps=?, bg_color=?,
      weight=?, active=?, start_at=?, end_at=? WHERE id = ?`).bind(...vals, old.id).run();
  } else {
    await c.env.DB.prepare(`INSERT INTO ads (title, subtitle, image, link_url, button_text, placement, apps, bg_color, weight, active,
      start_at, end_at, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(...vals, now()).run();
  }
  return flashRedirect(c, "success", "광고를 저장했습니다.", "/admin/ads");
}

admin.post("/ads/new", (c) => saveAd(c, null));
admin.post("/ads/:id", (c) => saveAd(c, Number(c.req.param("id"))));

admin.post("/ads/:id/toggle", async (c) => {
  await c.env.DB.prepare("UPDATE ads SET active = 1 - active WHERE id = ?").bind(Number(c.req.param("id"))).run();
  return c.redirect("/admin/ads");
});

admin.post("/ads/:id/delete", async (c) => {
  await c.env.DB.prepare("DELETE FROM ads WHERE id = ?").bind(Number(c.req.param("id"))).run();
  return flashRedirect(c, "success", "광고를 삭제했습니다.", "/admin/ads");
});

// ---------- 제품 ----------
admin.get("/products", async (c) => {
  const items = (await c.env.DB.prepare("SELECT * FROM products ORDER BY sort").all<Product>()).results;
  return c.html(<A.Products c={pageCtx(c)} items={items} />);
});

admin.post("/products", async (c) => {
  const f = await form(c);
  const vals = [f.slug || "", f.name || "", f.tagline || "", f.description || "", f.version || "1.0.0", f.download_url || "",
    f.status === "released" ? "released" : "coming", f.color || "#ff6f91", Number(f.sort) || 0].map((v) => (typeof v === "string" ? v.trim() : v));
  if (f.id) {
    await c.env.DB.prepare(`UPDATE products SET slug=?, name=?, tagline=?, description=?, version=?, download_url=?, status=?, color=?, sort=?
      WHERE id = ?`).bind(...vals, Number(f.id)).run();
  } else {
    await c.env.DB.prepare(`INSERT INTO products (slug, name, tagline, description, version, download_url, status, color, sort)
      VALUES (?,?,?,?,?,?,?,?,?)`).bind(...vals).run();
  }
  return flashRedirect(c, "success", `'${f.name}' 제품 정보를 저장했습니다.`, "/admin/products");
});

// ---------- 설정 ----------
admin.get("/settings", (c) => c.html(<A.Settings c={pageCtx(c)} toss={tossEnabled(c.env)} />));

admin.post("/settings", async (c) => {
  const f = await form(c);
  for (const k of ["plan_name", "price", "device_limit", "popup_every"]) await setSetting(c.env, k, (f[k] || "").trim());
  return flashRedirect(c, "success", "설정을 저장했습니다.", "/admin/settings");
});

export default admin;
