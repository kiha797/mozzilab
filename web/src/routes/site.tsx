// 사용자 사이트 - 홈, 제품, 요금제, 로그인/회원가입, 마이페이지, 구독 결제, PC 로그인 승인
import { Hono } from "hono";
import { hashPassword, oauthProfile, PROVIDERS, providerEnabled, providerKeys, randomToken, safeNext, saveSession, sha256, verifyPassword } from "../auth";
import { issueBillingKey, startSubscription, tossEnabled } from "../billing";
import { activeDevices, getUserByEmail, now, validSubscription, fmt, type DeviceCode, type Payment, type Product, type Subscription, type User } from "../db";
import { type AppEnv, type C, flashRedirect, form, login, pageCtx, siteUrl } from "../ctx";
import * as V from "../views/pages";

const site = new Hono<AppEnv>();

function needLogin(c: C): Response | null {
  if (c.get("user")) return null;
  const u = new URL(c.req.url);
  return c.redirect(`/login?next=${encodeURIComponent(u.pathname + u.search)}`);
}

site.get("/", async (c) => {
  const products = (await c.env.DB.prepare("SELECT * FROM products ORDER BY sort").all<Product>()).results;
  return c.html(<V.Home c={pageCtx(c)} products={products} />);
});

site.get("/products/:slug", async (c) => {
  const p = await c.env.DB.prepare("SELECT * FROM products WHERE slug = ?").bind(c.req.param("slug")).first<Product>();
  if (!p) return c.notFound();
  return c.html(<V.ProductPage c={pageCtx(c)} p={p} />);
});

site.get("/download/:slug", async (c) => {
  const p = await c.env.DB.prepare("SELECT * FROM products WHERE slug = ?").bind(c.req.param("slug")).first<Product>();
  if (!p) return c.notFound();
  if (p.status !== "released" || !p.download_url)
    return flashRedirect(c, "info", `${p.name}은(는) 곧 출시됩니다. 조금만 기다려 주세요!`, `/products/${p.slug}`);
  await c.env.DB.prepare("UPDATE products SET downloads = downloads + 1 WHERE id = ?").bind(p.id).run();
  return c.redirect(p.download_url);
});

site.get("/pricing", (c) => c.html(<V.Pricing c={pageCtx(c)} />));
site.get("/terms", (c) => c.html(<V.Policy c={pageCtx(c)} kind="terms" />));
site.get("/privacy", (c) => c.html(<V.Policy c={pageCtx(c)} kind="privacy" />));

// ---------- 로그인 / 회원가입 ----------
const enabledMap = (c: C) => Object.fromEntries(Object.keys(PROVIDERS).map((p) => [p, providerEnabled(c.env, p)]));

site.get("/login", (c) => c.html(<V.Login c={pageCtx(c)} enabled={enabledMap(c)} next={safeNext(c.req.query("next"), "")} />));

site.post("/login", async (c) => {
  const f = await form(c);
  const next = safeNext(f.next, "/mypage");
  const user = await getUserByEmail(c.env, (f.email || "").trim());
  if (!user || !(await verifyPassword(f.password || "", user.password_hash)))
    return flashRedirect(c, "error", "이메일 또는 비밀번호가 맞지 않습니다.", `/login?next=${encodeURIComponent(next)}`);
  if (user.status !== "active") return flashRedirect(c, "error", "이용이 정지된 계정입니다. 고객센터로 문의해 주세요.", "/login");
  await login(c, user);
  return c.redirect(next);
});

site.get("/signup", (c) => c.html(<V.Signup c={pageCtx(c)} next={safeNext(c.req.query("next"), "")} form={{}} />));

site.post("/signup", async (c) => {
  const f = await form(c);
  const email = (f.email || "").trim().toLowerCase();
  const pw = f.password || "";
  let err = "";
  if (!email.includes("@") || !email.includes(".")) err = "올바른 이메일 주소를 입력해 주세요.";
  else if (pw.length < 8) err = "비밀번호는 8자 이상으로 만들어 주세요.";
  else if (pw !== f.password2) err = "비밀번호 확인이 일치하지 않습니다.";
  else if (!f.agree) err = "이용약관과 개인정보처리방침에 동의해 주세요.";
  else if (await getUserByEmail(c.env, email)) err = "이미 가입된 이메일입니다. 로그인해 주세요.";
  if (err) {
    const ctx = pageCtx(c);
    ctx.flashes.push(["error", err]);
    return c.html(<V.Signup c={ctx} next={safeNext(f.next, "")} form={f} />);
  }
  const r = await c.env.DB.prepare("INSERT INTO users (email, name, password_hash, marketing, created_at) VALUES (?,?,?,?,?)")
    .bind(email, (f.name || "").trim().slice(0, 100), await hashPassword(pw), f.marketing ? 1 : 0, now()).run();
  const user = await c.env.DB.prepare("SELECT * FROM users WHERE id = ?").bind(r.meta.last_row_id).first<User>();
  await login(c, user!);
  return flashRedirect(c, "success", "모찌랩 회원이 되신 것을 환영합니다! 🍡", safeNext(f.next, "/mypage"));
});

site.get("/login/:provider", async (c) => {
  const p = c.req.param("provider");
  if (p === "apple") return flashRedirect(c, "info", "Apple 로그인은 준비 중입니다. 이메일로 로그인해 주세요.", "/login");
  if (!PROVIDERS[p]) return c.notFound();
  if (!providerEnabled(c.env, p))
    return flashRedirect(c, "info", `${PROVIDERS[p].name} 로그인은 준비 중입니다. 이메일로 로그인해 주세요.`, "/login");
  const s = c.get("session");
  s.oauth_state = randomToken(16);
  s.next = safeNext(c.req.query("next"), "/mypage");
  await saveSession(c, s);
  const params = new URLSearchParams({ response_type: "code", client_id: providerKeys(c.env, p)[0],
    redirect_uri: `${siteUrl(c)}/oauth/${p}/callback`, state: s.oauth_state });
  if (PROVIDERS[p].scope) params.set("scope", PROVIDERS[p].scope);
  return c.redirect(`${PROVIDERS[p].auth}?${params}`);
});

site.get("/oauth/:provider/callback", async (c) => {
  const p = c.req.param("provider");
  if (!PROVIDERS[p]) return c.notFound();
  const s = c.get("session");
  const state = c.req.query("state") || "";
  const code = c.req.query("code");
  if (!code || !s.oauth_state || state !== s.oauth_state)
    return flashRedirect(c, "error", "로그인이 취소되었거나 시간이 지났습니다. 다시 시도해 주세요.", "/login");
  const prof = await oauthProfile(c.env, p, code, state, `${siteUrl(c)}/oauth/${p}/callback`);
  if (!prof) return flashRedirect(c, "error", `${PROVIDERS[p].name} 로그인에 실패했습니다.`, "/login");
  const db = c.env.DB;
  let user = await db.prepare("SELECT * FROM users WHERE provider = ? AND provider_id = ?").bind(p, prof.pid).first<User>();
  if (!user && prof.email) {
    user = await getUserByEmail(c.env, prof.email);       // 같은 이메일이면 기존 계정에 연결
    if (user && !user.provider_id) await db.prepare("UPDATE users SET provider = ?, provider_id = ? WHERE id = ?").bind(p, prof.pid, user.id).run();
  }
  if (!user) {
    const email = (prof.email || `${p}_${prof.pid}@users.mozzilab`).toLowerCase();
    const r = await db.prepare("INSERT INTO users (email, name, provider, provider_id, created_at) VALUES (?,?,?,?,?)")
      .bind(email, prof.name || "", p, prof.pid, now()).run();
    user = await db.prepare("SELECT * FROM users WHERE id = ?").bind(r.meta.last_row_id).first<User>();
  }
  if (user!.status !== "active") return flashRedirect(c, "error", "이용이 정지된 계정입니다.", "/login");
  const next = s.next || "/mypage";
  await login(c, user!);
  return c.redirect(next);
});

site.post("/logout", async (c) => {
  const s = { csrf: c.get("session").csrf, exp: Date.now() + 30 * 86400_000 };
  await saveSession(c, s);
  return c.redirect("/");
});

// ---------- 마이페이지 ----------
site.get("/mypage", async (c) => {
  const r = needLogin(c); if (r) return r;
  const user = c.get("user")!;
  const db = c.env.DB;
  const [sub, last, devices, payments] = await Promise.all([
    validSubscription(c.env, user.id),
    db.prepare("SELECT * FROM subscriptions WHERE user_id = ? ORDER BY id DESC LIMIT 1").bind(user.id).first<Subscription>(),
    activeDevices(c.env, user.id),
    db.prepare("SELECT * FROM payments WHERE user_id = ? ORDER BY id DESC LIMIT 50").bind(user.id).all<Payment>(),
  ]);
  return c.html(<V.MyPage c={pageCtx(c)} user={user} sub={sub} lastSub={last} devices={devices} payments={payments.results} />);
});

site.post("/mypage/profile", async (c) => {
  const r = needLogin(c); if (r) return r;
  const user = c.get("user")!;
  const f = await form(c);
  if (f.new_password) {
    if (f.new_password.length < 8) return flashRedirect(c, "error", "새 비밀번호는 8자 이상이어야 합니다.", "/mypage");
    await c.env.DB.prepare("UPDATE users SET password_hash = ? WHERE id = ?").bind(await hashPassword(f.new_password), user.id).run();
  }
  await c.env.DB.prepare("UPDATE users SET name = ?, marketing = ? WHERE id = ?")
    .bind((f.name || "").trim().slice(0, 100), f.marketing ? 1 : 0, user.id).run();
  return flashRedirect(c, "success", "내 정보를 저장했습니다.", "/mypage");
});

site.post("/mypage/devices/:id/revoke", async (c) => {
  const r = needLogin(c); if (r) return r;
  const dev = await c.env.DB.prepare("SELECT * FROM devices WHERE id = ? AND user_id = ?").bind(Number(c.req.param("id")), c.get("user")!.id)
    .first<{ id: number; device_name: string }>();
  if (!dev) return c.notFound();
  await c.env.DB.prepare("UPDATE devices SET revoked = 1 WHERE id = ?").bind(dev.id).run();
  return flashRedirect(c, "success", `'${dev.device_name}' 기기의 로그인을 해제했습니다.`, "/mypage");
});

// ---------- 구독 결제 ----------
site.get("/subscribe", async (c) => {
  const r = needLogin(c); if (r) return r;
  if (c.get("premium")) return flashRedirect(c, "info", "이미 구독 중입니다. 광고 없이 이용하세요!", "/mypage");
  const customerKey = `mozzi-user-${c.get("user")!.id}-${randomToken(6)}`;
  return c.html(<V.Checkout c={pageCtx(c)} toss={tossEnabled(c.env)} clientKey={c.env.TOSS_CLIENT_KEY || ""} customerKey={customerKey} siteUrl={siteUrl(c)} />);
});

site.post("/subscribe/test", async (c) => {
  const r = needLogin(c); if (r) return r;
  if (tossEnabled(c.env)) return c.notFound();
  const res = await startSubscription(c.env, c.get("user")!, "test", null, null, "테스트 카드");
  return res.ok ? flashRedirect(c, "success", "테스트 결제가 완료되었습니다. 이제 광고 없이 이용할 수 있어요!", "/mypage")
    : flashRedirect(c, "error", res.reason, "/mypage");
});

site.get("/billing/success", async (c) => {
  const r = needLogin(c); if (r) return r;
  const user = c.get("user")!;
  const authKey = c.req.query("authKey");
  const customerKey = c.req.query("customerKey") || "";
  if (!authKey || !customerKey.startsWith(`mozzi-user-${user.id}-`)) return c.text("잘못된 요청", 400);
  let billingKey: string, card: string;
  try {
    ({ billingKey, card } = await issueBillingKey(c.env, authKey, customerKey));
  } catch (e) {
    return flashRedirect(c, "error", `카드 등록에 실패했습니다: ${(e as Error).message}`, "/pricing");
  }
  const res = await startSubscription(c.env, user, "toss", billingKey, customerKey, card);
  return res.ok ? flashRedirect(c, "success", "구독이 시작되었습니다. 이제 모든 모찌랩 제품을 광고 없이 쓸 수 있어요! 🎉", "/mypage")
    : flashRedirect(c, "error", `결제에 실패했습니다: ${res.reason}`, "/mypage");
});

site.get("/billing/fail", (c) => flashRedirect(c, "error", `결제가 진행되지 않았습니다. (${c.req.query("message") || "취소됨"})`, "/pricing"));

site.post("/subscription/cancel", async (c) => {
  const r = needLogin(c); if (r) return r;
  const sub = await validSubscription(c.env, c.get("user")!.id);
  if (sub && sub.status === "active") {
    await c.env.DB.prepare("UPDATE subscriptions SET status = 'canceled', canceled_at = ? WHERE id = ?").bind(now(), sub.id).run();
    return flashRedirect(c, "success", `해지 예약되었습니다. ${fmt(sub.current_period_end, "korean")}까지는 광고 없이 이용할 수 있어요.`, "/mypage");
  }
  return c.redirect("/mypage");
});

site.post("/subscription/resume", async (c) => {
  const r = needLogin(c); if (r) return r;
  const sub = await validSubscription(c.env, c.get("user")!.id);
  if (sub && sub.status === "canceled" && sub.method !== "manual") {
    await c.env.DB.prepare("UPDATE subscriptions SET status = 'active', canceled_at = NULL WHERE id = ?").bind(sub.id).run();
    return flashRedirect(c, "success", "해지 예약을 취소했습니다. 구독이 계속됩니다.", "/mypage");
  }
  return c.redirect("/mypage");
});

// ---------- PC 프로그램 로그인 승인 ----------
site.get("/device", async (c) => {
  const r = needLogin(c); if (r) return r;
  const code = (c.req.query("code") || "").trim().toUpperCase();
  const dc = code ? await c.env.DB.prepare("SELECT * FROM device_codes WHERE user_code = ?").bind(code).first<DeviceCode>() : null;
  return c.html(<V.DevicePage c={pageCtx(c)} code={code} dc={dc} expired={!!dc && dc.expires_at < now()} />);
});

site.post("/device", async (c) => {
  const r = needLogin(c); if (r) return r;
  const user = c.get("user")!;
  const f = await form(c);
  const db = c.env.DB;
  const dc = await db.prepare("SELECT * FROM device_codes WHERE user_code = ?").bind((f.code || "").trim().toUpperCase()).first<DeviceCode>();
  if (!dc || dc.status !== "pending" || dc.expires_at < now())
    return flashRedirect(c, "error", "코드가 맞지 않거나 시간이 지났습니다. PC 프로그램에서 로그인을 다시 눌러 주세요.", "/device");
  if (f.action === "deny") {
    await db.prepare("UPDATE device_codes SET status = 'denied' WHERE id = ?").bind(dc.id).run();
    return flashRedirect(c, "info", "연결을 거절했습니다.", "/mypage");
  }
  const limit = Number(c.get("settings").device_limit);
  const devices = await activeDevices(c.env, user.id);
  const same = devices.filter((d) => d.device_id === dc.device_id && d.app === dc.app);
  // 같은 PC 에서 모찌캡처·모찌PDF·모찌압축을 함께 써도 PC 1대로 계산
  const pcs = new Set(devices.map((d) => d.device_id));
  if (!pcs.has(dc.device_id) && pcs.size >= limit)
    return flashRedirect(c, "error", `PC는 최대 ${limit}대까지 연결할 수 있습니다. 아래 '내 PC 기기'에서 쓰지 않는 PC를 해제해 주세요.`, "/mypage");
  const token = randomToken(32);
  const t = now();
  await db.batch([
    ...same.map((d) => db.prepare("UPDATE devices SET revoked = 1 WHERE id = ?").bind(d.id)),
    db.prepare(`INSERT INTO devices (user_id, device_id, device_name, app, app_version, token_hash, created_at, last_seen_at)
      VALUES (?,?,?,?,?,?,?,?)`).bind(user.id, dc.device_id, dc.device_name || "내 PC", dc.app, dc.app_version, await sha256(token), t, t),
    db.prepare("UPDATE device_codes SET status = 'approved', user_id = ?, token = ? WHERE id = ?").bind(user.id, token, dc.id),
  ]);
  return c.html(<V.DeviceDone c={pageCtx(c)} dc={dc} premium={c.get("premium")} />);
});

export default site;
