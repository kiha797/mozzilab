// 모든 화면이 함께 쓰는 틀 (상단 메뉴, 바닥글, 관리자 메뉴)
import type { Child } from "hono/jsx";
import type { Flash } from "../auth";
import { displayName } from "../auth";
import type { User } from "../db";

export const BRAND = {
  name: "모찌LAB.",
  en: "MozziLab",
  slogan: "말랑말랑, 누구나 쉬운 PC 도구",
};

export interface PageCtx {
  me: User | null;
  premium: boolean;
  csrf: string;
  s: Record<string, string>;
  testMode: boolean;
  flashes: Flash[];
  path: string;
  company: string;
  email: string;
}

export const Csrf = ({ c }: { c: PageCtx }) => <input type="hidden" name="_csrf" value={c.csrf} />;

const Flashes = ({ items, wrap = true }: { items: Flash[]; wrap?: boolean }) => {
  if (!items.length) return null;
  const list = items.map(([k, m]) => <div class={`flash flash-${k}`}>{m}</div>);
  return wrap ? <div class="container flashes">{list}</div> : <>{list}</>;
};

const Head = ({ title }: { title: string }) => (
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <link rel="icon" href="/img/favicon.svg" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" />
    <link rel="stylesheet" href="/css/style.css" />
  </head>
);

export const Layout = ({ c, title, children, head }: { c: PageCtx; title?: string; children: Child; head?: Child }) => (
  <html lang="ko">
    <Head title={title ? `${title} - ${BRAND.name}` : `${BRAND.name} - ${BRAND.slogan}`} />
    {head}
    <body>
      {c.testMode && <div class="testbar">🧪 테스트 모드 — 실제 결제가 되지 않습니다 (Cloudflare 설정에 토스페이먼츠 키를 넣으면 실제 결제)</div>}
      <header class="header">
        <div class="container">
          <a class="logo" href="/"><img src="/img/mochi.svg" alt="" />{BRAND.name}<small>{BRAND.en}</small></a>
          <nav class="nav">
            <a href="/#products">제품</a>
            <a href="/products/capture">모찌캡처</a>
            <a href="/pricing">{c.s.plan_name}</a>
            <a href="/pricing#faq">고객지원</a>
          </nav>
          {c.me ? (
            <details class="dropdown">
              <summary class="btn btn-dark btn-sm">{displayName(c.me)} 님 {c.premium ? "⭐" : ""} ▾</summary>
              <div class="dropdown-menu">
                <a href="/mypage">마이페이지</a>
                {!c.premium && <a href="/pricing">광고 없이 쓰기</a>}
                {c.me.role === "admin" && <a href="/admin">관리자 사이트</a>}
                <form method="post" action="/logout"><Csrf c={c} /><button>로그아웃</button></form>
              </div>
            </details>
          ) : (
            <>
              <a class="btn btn-sm" href="/login">로그인</a>
              <a class="btn btn-pink btn-sm" href="/signup">회원가입</a>
            </>
          )}
        </div>
      </header>
      <Flashes items={c.flashes} />
      <main>{children}</main>
      <footer class="footer">
        <div class="container">
          <div>
            <div class="logo" style="font-size:17px"><img src="/img/mochi.svg" alt="" style="width:30px" />{BRAND.name}</div>
            <div>{BRAND.slogan}</div>
            <div class="small muted">© {c.company} · 문의 {c.email}</div>
          </div>
          <div><a href="/terms">이용약관</a><a href="/privacy"><b>개인정보처리방침</b></a><a href="/pricing">요금제</a></div>
        </div>
      </footer>
    </body>
  </html>
);

const ADMIN_MENU: [string, string, string[]][] = [
  ["/admin", "📊 대시보드", ["/admin"]],
  ["/admin/users", "👥 회원 관리", ["/admin/users"]],
  ["/admin/subscriptions", "⭐ 구독 관리", ["/admin/subscriptions"]],
  ["/admin/payments", "💳 결제 내역", ["/admin/payments"]],
  ["/admin/devices", "💻 라이선스(PC)", ["/admin/devices"]],
  ["", "", []],
  ["/admin/ads", "📢 광고 관리", ["/admin/ads"]],
  ["/admin/products", "📦 제품 관리", ["/admin/products"]],
  ["/admin/settings", "⚙️ 설정", ["/admin/settings"]],
];

export const AdminLayout = ({ c, children }: { c: PageCtx; children: Child }) => (
  <html lang="ko">
    <Head title={`관리자 - ${BRAND.name}`} />
    <body>
      <div class="admin">
        <aside class="admin-side">
          <a class="logo" href="/admin" style="padding:0;background:none"><img src="/img/mochi.svg" alt="" />관리자</a>
          {ADMIN_MENU.map(([href, label, prefixes]) => {
            if (!href) return <div class="sep"></div>;
            const on = href === "/admin" ? c.path === "/admin" || c.path === "/admin/" : prefixes.some((p) => c.path.startsWith(p));
            return <a href={href} class={on ? "on" : ""}>{label}</a>;
          })}
          <div class="sep"></div>
          <a href="/">🏠 사용자 사이트</a>
          <form method="post" action="/logout"><Csrf c={c} /><button class="btn btn-sm btn-ghost" style="color:#e9dede;margin-left:6px">로그아웃</button></form>
        </aside>
        <section class="admin-main">
          {c.testMode && <div class="flash flash-info">🧪 테스트 모드 — 토스페이먼츠 키가 없어 가상 결제로 동작합니다.</div>}
          <Flashes items={c.flashes} wrap={false} />
          {children}
        </section>
      </div>
    </body>
  </html>
);

export const Badge = ({ kind, children }: { kind?: string; children: Child }) => (
  <span class={`badge ${kind ? "badge-" + kind : ""}`}>{children}</span>
);

export const PAY_BADGE: Record<string, string> = { paid: "mint", failed: "red", refunded: "gray" };
export const SUB_BADGE: Record<string, string> = { active: "mint", canceled: "peach", past_due: "red", expired: "gray" };

export const Pager = ({ page, pages, base }: { page: number; pages: number; base: string }) => {
  if (pages <= 1) return null;
  const sep = base.includes("?") ? "&" : "?";
  const nums = Array.from({ length: pages }, (_, i) => i + 1).filter((n) => n <= 2 || n > pages - 2 || Math.abs(n - page) <= 2);
  const out: Child[] = [];
  let last = 0;
  for (const n of nums) {
    if (n - last > 1) out.push(<span>…</span>);
    out.push(n === page ? <span class="on">{n}</span> : <a href={`${base}${sep}page=${n}`}>{n}</a>);
    last = n;
  }
  return <div class="pager">{out}</div>;
};
