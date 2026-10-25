// 모찌랩 웹사이트 (Cloudflare Workers) - 사용자 사이트 + 관리자 사이트 + PC 프로그램용 API
import { Hono } from "hono";
import { loadSession, saveSession } from "./auth";
import { renewDue } from "./billing";
import { ensureSchema, getSettings, getUser, validSubscription, type Env } from "./db";
import { type AppEnv, form, pageCtx } from "./ctx";
import adminRoutes from "./routes/admin";
import apiRoutes from "./routes/api";
import siteRoutes from "./routes/site";
import { ErrorPage } from "./views/pages";

const app = new Hono<AppEnv>();

// 모든 요청: DB 준비 → 설정 → 로그인 세션 → 폼 보안(CSRF) 확인
app.use("*", async (c, next) => {
  await ensureSchema(c.env);
  c.set("settings", await getSettings(c.env));
  const isApi = c.req.path.startsWith("/api/") || c.req.path.startsWith("/r/") || c.req.path.startsWith("/files/");
  if (isApi) {
    c.set("user", null);
    c.set("premium", false);
    c.set("session", { csrf: "", exp: 0 });
    return next();
  }
  const session = await loadSession(c);
  c.set("session", session);
  let user = session.uid ? await getUser(c.env, session.uid) : null;
  if (user && user.status !== "active") user = null;
  c.set("user", user);
  c.set("premium", user ? !!(await validSubscription(c.env, user.id)) : false);
  if (!c.req.header("Cookie")?.includes("ml_sess=")) await saveSession(c, session);
  if (c.req.method === "POST") {
    const f = await form(c);
    if (f._csrf !== session.csrf)
      return c.html(<ErrorPage c={pageCtx(c)} code={400} msg="보안 토큰이 만료되었습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요." />, 400);
  }
  await next();
});

app.route("/", apiRoutes);
app.route("/admin", adminRoutes);
app.route("/", siteRoutes);

app.notFound((c) => {
  if (c.req.path.startsWith("/api/")) return c.json({ error: "not found" }, 404);
  return c.html(<ErrorPage c={pageCtx(c)} code={404} msg="페이지를 찾을 수 없어요." />, 404);
});

app.onError((err, c) => {
  console.error(err);
  if (c.req.path.startsWith("/api/")) return c.json({ error: "server error" }, 500);
  return c.html(<ErrorPage c={pageCtx(c)} code={500} msg="잠시 문제가 생겼어요. 잠시 후 다시 시도해 주세요." />, 500);
});

export default {
  fetch: app.fetch,
  // 매일 오전 9시(한국 시간): 정기결제 + 오래된 로그인 코드 정리
  async scheduled(_event: ScheduledController, env: Env, ctx: ExecutionContext) {
    ctx.waitUntil((async () => {
      await ensureSchema(env);
      console.log("renew", JSON.stringify(await renewDue(env)));
      await env.DB.prepare("DELETE FROM device_codes WHERE created_at < ?").bind(new Date(Date.now() - 86400_000).toISOString()).run();
    })());
  },
};
