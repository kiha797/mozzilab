// 정기결제(구독) - 토스페이먼츠 자동결제(빌링) API
// TOSS_CLIENT_KEY / TOSS_SECRET_KEY 가 없으면 '테스트 모드'(가상 결제)
import { addMonths, getSettings, now, type Env, type Payment, type Subscription, type User } from "./db";
import { displayName, randomToken } from "./auth";

const TOSS_API = "https://api.tosspayments.com/v1";

export const tossEnabled = (env: Env) => !!(env.TOSS_CLIENT_KEY && env.TOSS_SECRET_KEY);

function authHeader(env: Env) {
  return { Authorization: "Basic " + btoa((env.TOSS_SECRET_KEY || "") + ":"), "Content-Type": "application/json" };
}

export async function issueBillingKey(env: Env, authKey: string, customerKey: string): Promise<{ billingKey: string; card: string }> {
  const r = await fetch(`${TOSS_API}/billing/authorizations/issue`, {
    method: "POST", headers: authHeader(env), body: JSON.stringify({ authKey, customerKey }),
  });
  const data = (await r.json()) as any;
  if (!r.ok) throw new Error(data.message || "빌링키 발급 실패");
  return { billingKey: data.billingKey, card: `${data.cardCompany || ""} ${data.card?.number || ""}`.trim() };
}

async function chargeToss(env: Env, sub: Subscription, user: User, amount: number, orderId: string, orderName: string) {
  const r = await fetch(`${TOSS_API}/billing/${sub.billing_key}`, {
    method: "POST", headers: authHeader(env),
    body: JSON.stringify({ customerKey: sub.customer_key, amount, orderId, orderName, customerEmail: user.email, customerName: displayName(user) }),
  });
  const data = (await r.json()) as any;
  if (r.ok && data.status === "DONE") return { ok: true, paymentKey: data.paymentKey as string, reason: "" };
  return { ok: false, paymentKey: null, reason: (data.message as string) || "결제 실패" };
}

/** 구독 1개월치 결제. 성공하면 이용 기간이 1개월 늘어난다. */
export async function charge(env: Env, sub: Subscription): Promise<{ ok: boolean; reason: string }> {
  const user = await env.DB.prepare("SELECT * FROM users WHERE id = ?").bind(sub.user_id).first<User>();
  if (!user) return { ok: false, reason: "회원 없음" };
  const s = await getSettings(env);
  const amount = Number(s.price);
  const orderId = `mozzi-${sub.id}-${randomToken(9)}`;
  const orderName = `${s.plan_name} 1개월`;
  const res = sub.method === "toss"
    ? await chargeToss(env, sub, user, amount, orderId, orderName)
    : { ok: true, paymentKey: "TEST-" + randomToken(12), reason: "" };
  const t = now();
  const stmts = [env.DB.prepare(`INSERT INTO payments (user_id, subscription_id, amount, status, order_id, order_name, payment_key,
      method, card, fail_reason, paid_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)`)
    .bind(user.id, sub.id, amount, res.ok ? "paid" : "failed", orderId, orderName, res.paymentKey, sub.method, sub.card_info, res.reason, t)];
  if (res.ok) {
    const base = sub.current_period_end && sub.current_period_end > t ? sub.current_period_end : t;
    stmts.push(env.DB.prepare("UPDATE subscriptions SET current_period_end = ?, price = ?, status = 'active' WHERE id = ?")
      .bind(addMonths(base, 1), amount, sub.id));
  } else {
    stmts.push(env.DB.prepare("UPDATE subscriptions SET status = 'past_due' WHERE id = ?").bind(sub.id));
  }
  await env.DB.batch(stmts);
  return { ok: res.ok, reason: res.reason };
}

export async function startSubscription(env: Env, user: User, method: string, billingKey: string | null = null,
  customerKey: string | null = null, card = ""): Promise<{ ok: boolean; reason: string }> {
  const s = await getSettings(env);
  const t = now();
  const r = await env.DB.prepare(`INSERT INTO subscriptions (user_id, method, billing_key, customer_key, card_info, price, status,
      started_at, current_period_end, created_at) VALUES (?,?,?,?,?,?,'active',?,?,?)`)
    .bind(user.id, method, billingKey, customerKey, card, Number(s.price), t, t, t).run();
  const sub = await env.DB.prepare("SELECT * FROM subscriptions WHERE id = ?").bind(r.meta.last_row_id).first<Subscription>();
  const res = await charge(env, sub!);
  if (!res.ok) await env.DB.prepare("UPDATE subscriptions SET status = 'expired' WHERE id = ?").bind(sub!.id).run();
  return res;
}

export async function refund(env: Env, pay: Payment): Promise<{ ok: boolean; reason: string }> {
  if (pay.method === "toss" && pay.payment_key && tossEnabled(env)) {
    const r = await fetch(`${TOSS_API}/payments/${pay.payment_key}/cancel`, {
      method: "POST", headers: authHeader(env), body: JSON.stringify({ cancelReason: "관리자 환불" }),
    });
    if (!r.ok) return { ok: false, reason: ((await r.json()) as any).message || "환불 실패" };
  }
  await env.DB.prepare("UPDATE payments SET status = 'refunded', refunded_at = ? WHERE id = ?").bind(now(), pay.id).run();
  return { ok: true, reason: "" };
}

/** 기간이 끝난 구독 정리 + 자동결제. 매일 Cron(오전 9시)과 관리자 버튼에서 실행 */
export async function renewDue(env: Env) {
  const result = { renewed: 0, failed: 0, expired: 0 };
  const t = now();
  const subs = (await env.DB.prepare("SELECT * FROM subscriptions WHERE status IN ('active','canceled','past_due')").all<Subscription>()).results;
  for (const sub of subs) {
    if (sub.current_period_end && sub.current_period_end > t && sub.status !== "past_due") continue;
    const expire = () => env.DB.prepare("UPDATE subscriptions SET status = 'expired' WHERE id = ?").bind(sub.id).run();
    if (sub.status === "canceled" || sub.method === "manual") { await expire(); result.expired++; continue; }
    if (sub.status === "past_due" && sub.current_period_end &&
        Date.now() - new Date(sub.current_period_end).getTime() >= 3 * 86400_000) { await expire(); result.expired++; continue; }
    const r = await charge(env, sub);
    r.ok ? result.renewed++ : result.failed++;
  }
  return result;
}
