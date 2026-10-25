// PC 프로그램(모찌캡처 등)이 쓰는 API - 로그인 연결, 라이선스 확인, 광고 목록
// (예전 파이썬 서버와 주소·응답 형식이 같아서 PC 프로그램은 그대로 동작)
import { Hono } from "hono";
import { randomToken, sha256 } from "../auth";
import { adRunning, addMinutes, now, validSubscription, type Ad, type Device, type DeviceCode, type Product, type User } from "../db";
import { type AppEnv, type C, siteUrl } from "../ctx";

const api = new Hono<AppEnv>();
const CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";   // 헷갈리는 0/O, 1/I 제외

function userCode(): string {
  const r = crypto.getRandomValues(new Uint8Array(8));
  const s = [...r].map((b) => CODE_CHARS[b % CODE_CHARS.length]).join("");
  return `${s.slice(0, 4)}-${s.slice(4)}`;
}

async function bearer(c: C): Promise<{ dev: Device; user: User } | null> {
  const auth = c.req.header("Authorization") || "";
  if (!auth.startsWith("Bearer ")) return null;
  const dev = await c.env.DB.prepare("SELECT * FROM devices WHERE token_hash = ? AND revoked = 0").bind(await sha256(auth.slice(7).trim())).first<Device>();
  if (!dev) return null;
  const user = await c.env.DB.prepare("SELECT * FROM users WHERE id = ?").bind(dev.user_id).first<User>();
  if (!user || user.status !== "active") return null;
  c.executionCtx.waitUntil(c.env.DB.prepare("UPDATE devices SET last_seen_at = ? WHERE id = ?").bind(now(), dev.id).run());
  return { dev, user };
}

async function body(c: C): Promise<Record<string, any>> {
  try { return await c.req.json(); } catch { return {}; }
}

api.post("/api/device/start", async (c) => {
  const d = await body(c);
  const deviceCode = randomToken(32);
  const code = userCode();
  const t = now();
  await c.env.DB.prepare(`INSERT INTO device_codes (device_code, user_code, device_id, device_name, app, app_version, created_at, expires_at)
    VALUES (?,?,?,?,?,?,?,?)`).bind(deviceCode, code, String(d.device_id || "").slice(0, 100), String(d.device_name || "").slice(0, 100),
    String(d.app || "capture").slice(0, 30), String(d.version || "").slice(0, 30), t, addMinutes(t, 10)).run();
  return c.json({ device_code: deviceCode, user_code: code, interval: 3, expires_in: 600,
    verify_url: `${siteUrl(c)}/device?code=${code}` });
});

api.post("/api/device/poll", async (c) => {
  const d = await body(c);
  const dc = await c.env.DB.prepare("SELECT * FROM device_codes WHERE device_code = ?").bind(String(d.device_code || "")).first<DeviceCode>();
  if (!dc) return c.json({ status: "invalid" }, 404);
  if (dc.status === "pending" && dc.expires_at < now()) return c.json({ status: "expired" });
  if (dc.status === "approved" && dc.token) {
    await c.env.DB.prepare("UPDATE device_codes SET token = NULL, status = 'used' WHERE id = ?").bind(dc.id).run();
    return c.json({ status: "approved", token: dc.token });
  }
  return c.json({ status: dc.status });
});

api.get("/api/me", async (c) => {
  const b = await bearer(c);
  if (!b) return c.json({ error: "unauthorized" }, 401);
  const sub = await validSubscription(c.env, b.user.id);
  const base = siteUrl(c);
  return c.json({
    email: b.user.email, name: b.user.name || b.user.email.split("@")[0], premium: !!sub,
    plan_name: c.get("settings").plan_name,
    // PC 프로그램은 한국 시간 기준으로 비교하므로 한국 시간(UTC+9)으로 보냄
    expires_at: sub?.current_period_end ? new Date(new Date(sub.current_period_end).getTime() + 9 * 3600_000).toISOString().slice(0, 19) : null,
    mypage_url: `${base}/mypage`, pricing_url: `${base}/pricing`,
  });
});

api.post("/api/logout", async (c) => {
  const b = await bearer(c);
  if (b) await c.env.DB.prepare("UPDATE devices SET revoked = 1 WHERE id = ?").bind(b.dev.id).run();
  return c.json({ ok: true });
});

// ---------- 광고 ----------
function adJson(c: C, ad: Ad) {
  const base = siteUrl(c);
  const img = ad.image ? (ad.image.startsWith("http") ? ad.image : `${base}/files/${ad.image}`) : "";
  return { id: ad.id, title: ad.title, subtitle: ad.subtitle, image_url: img, button_text: ad.button_text,
    bg_color: ad.bg_color, weight: Math.max(1, ad.weight || 1), click_url: `${base}/r/ad/${ad.id}` };
}

api.get("/api/ads", async (c) => {
  const app = c.req.query("app") || "capture";
  const s = c.get("settings");
  const pricing = `${siteUrl(c)}/pricing`;
  const b = await bearer(c);
  if (b && (await validSubscription(c.env, b.user.id))) return c.json({ show_ads: false, pricing_url: pricing });
  const items = (await c.env.DB.prepare("SELECT * FROM ads WHERE active = 1").all<Ad>()).results
    .filter((a) => adRunning(a) && (a.apps === "all" || a.apps === app));
  return c.json({
    show_ads: true, pricing_url: pricing, popup_every: Number(s.popup_every || 1), plan_name: s.plan_name, price: Number(s.price),
    banner: items.filter((a) => a.placement === "banner").map((a) => adJson(c, a)),
    popup: items.filter((a) => a.placement === "popup").map((a) => adJson(c, a)),
  });
});

api.post("/api/ads/:id/view", async (c) => {
  await c.env.DB.prepare("UPDATE ads SET views = views + 1 WHERE id = ?").bind(Number(c.req.param("id"))).run();
  return c.json({ ok: true });
});

api.get("/r/ad/:id", async (c) => {
  const ad = await c.env.DB.prepare("SELECT * FROM ads WHERE id = ?").bind(Number(c.req.param("id"))).first<Ad>();
  if (!ad) return c.redirect("/");
  await c.env.DB.prepare("UPDATE ads SET clicks = clicks + 1 WHERE id = ?").bind(ad.id).run();
  return c.redirect(ad.link_url || "/pricing");
});

api.get("/api/products", async (c) => {
  const base = siteUrl(c);
  const rows = (await c.env.DB.prepare("SELECT * FROM products ORDER BY sort").all<Product>()).results;
  return c.json(rows.map((p) => ({ slug: p.slug, name: p.name, version: p.version, status: p.status, download_url: `${base}/download/${p.slug}` })));
});

// 광고 이미지 (관리자가 올린 파일)
api.get("/files/:id", async (c) => {
  const f = await c.env.DB.prepare("SELECT content_type, data FROM files WHERE id = ?").bind(c.req.param("id")).first<{ content_type: string; data: ArrayBuffer | number[] }>();
  if (!f) return c.notFound();
  return new Response(new Uint8Array(f.data as ArrayBuffer), {
    headers: { "Content-Type": f.content_type, "Cache-Control": "public, max-age=31536000, immutable" },
  });
});

export default api;
