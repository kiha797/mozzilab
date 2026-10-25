// 사용자 사이트 화면
import { raw } from "hono/html";
import { displayName } from "../auth";
import { APP_NAMES, fmt, PAY_STATUS, SUB_METHOD, SUB_STATUS, won, type Device, type DeviceCode, type Payment, type Product, type Subscription, type User } from "../db";
import { Badge, BRAND, Csrf, Layout, PAY_BADGE, type PageCtx } from "./layout";

const ProductIcon = ({ p, size = 64 }: { p: Product; size?: number }) => (
  <div class="p-icon" style={`background:${p.color}22;width:${size}px;height:${size}px`}>
    <img src="/img/mochi.svg" alt="" style={`filter:drop-shadow(0 2px 0 ${p.color})`} />
  </div>
);

export const Home = ({ c, products }: { c: PageCtx; products: Product[] }) => (
  <Layout c={c}>
    <section class="hero">
      <div class="container">
        <div>
          <span class="badge">🍡 무료로 시작하는 PC 도구</span>
          <h1>말랑말랑,<br /><em>누구나 쉬운</em> PC 도구<br />{BRAND.name}</h1>
          <p>캡처부터 PDF까지, 꼭 필요한 기능만 귀엽고 가볍게.<br />지금 무료로 써보고, 광고가 싫다면 {c.s.plan_name}로!</p>
          <a class="btn btn-pink btn-lg" href="/download/capture">모찌캡처 무료 다운로드</a>
          <a class="btn btn-lg btn-ghost" href="/pricing">광고 없이 쓰기 →</a>
        </div>
        <div class="hero-mochi">
          <div class="hero-bubble">찰칵! 캡처는 나한테 맡겨 📸</div>
          <img src="/img/mochi.svg" alt="모찌 캐릭터" />
        </div>
      </div>
    </section>
    <section class="section" id="products">
      <div class="container">
        <h2>{BRAND.name} 제품</h2>
        <p class="lead">하나씩 늘어나는 말랑한 도구들. 모두 무료로 쓸 수 있어요.</p>
        <div class="cards">
          {products.map((p) => (
            <div class="card">
              <ProductIcon p={p} />
              <h3>{p.name} {p.status === "coming" ? <Badge kind="gray">출시 예정</Badge> : <Badge kind="mint">v{p.version}</Badge>}</h3>
              <p>{p.tagline}</p>
              {p.status === "released" ? (
                <><a class="btn btn-pink btn-sm" href={`/download/${p.slug}`}>무료 다운로드</a>
                  <a class="btn btn-sm btn-ghost" href={`/products/${p.slug}`}>자세히</a></>
              ) : <a class="btn btn-sm" href={`/products/${p.slug}`}>출시 알림 받기</a>}
            </div>
          ))}
        </div>
      </div>
    </section>
    <section class="section" style="background:var(--cream)">
      <div class="container">
        <h2>모찌캡처, 이런 게 좋아요</h2>
        <p class="lead">트레이 아이콘을 콕 누르면 바로 캡처!</p>
        <div class="features">
          <div class="feature"><div class="emoji">✂️</div><b>6가지 캡처</b><span>직접지정 · 창 · 단위영역 · 전체 · 스크롤 · 크기지정</span></div>
          <div class="feature"><div class="emoji">📐</div><b>크기지정 기억</b><span>정해둔 위치와 크기 그대로 다음에도 짠!</span></div>
          <div class="feature"><div class="emoji">🖍️</div><b>바로 편집</b><span>도형 · 화살표 · 펜 · 형광펜 · 모자이크 · 텍스트</span></div>
          <div class="feature"><div class="emoji">📋</div><b>자동 복사</b><span>캡처하면 바로 Ctrl+V. 카톡·메일에 쏙</span></div>
        </div>
      </div>
    </section>
    <section class="section">
      <div class="container">
        <div class="plus-banner">
          <div><h2>광고 없이 쾌적한 {c.s.plan_name}</h2><p>월 {won(Number(c.s.price))}으로 모든 {BRAND.name} PC 제품의 광고를 없애요. 언제든 해지할 수 있어요.</p></div>
          <a class="btn btn-lg" href="/pricing">지금 구독하기</a>
        </div>
      </div>
    </section>
  </Layout>
);

export const ProductPage = ({ c, p }: { c: PageCtx; p: Product }) => (
  <Layout c={c} title={p.name}>
    <section class="hero" style="padding:60px 0">
      <div class="container">
        <div>
          <ProductIcon p={p} size={80} />
          <h1>{p.name}</h1>
          <p>{p.tagline}<br /><span class="small">{p.description}</span></p>
          {p.status === "released" ? (
            <><a class="btn btn-pink btn-lg" href={`/download/${p.slug}`}>무료 다운로드 (v{p.version})</a>
              <p class="small muted" style="margin-top:12px">Windows 10 / 11 · 무료 버전은 결과창에 광고가 표시됩니다</p></>
          ) : <span class="badge badge-gray" style="font-size:15px;padding:8px 16px">🛠 열심히 만드는 중이에요</span>}
        </div>
        <div class="hero-mochi"><img src="/img/mochi.svg" alt="" /></div>
      </div>
    </section>
  </Layout>
);

export const Pricing = ({ c }: { c: PageCtx }) => (
  <Layout c={c} title={c.s.plan_name}>
    <section class="price-hero">
      <div class="container">
        <span class="badge">🍡 {BRAND.name} 구독</span>
        <h1>광고 없이 쾌적한<br />{BRAND.name} <em>{c.s.plan_name.replace("모찌 ", "")}</em></h1>
        <p>모찌캡처는 물론, 앞으로 나올 모든 {BRAND.name} PC 제품에서 광고가 사라져요.</p>
      </div>
    </section>
    <div class="container">
      <div class="plans">
        <div class="plan">
          <h3>무료</h3>
          <div class="price">0원 <small>/ 평생</small></div>
          <ul><li>모든 캡처·편집 기능</li><li>최근 캡처 목록 100장</li><li class="no">결과창 광고 표시</li><li class="no">캡처 후 팝업 광고</li></ul>
          <a class="btn btn-block" href="/download/capture">무료 다운로드</a>
        </div>
        <div class="plan best">
          <h3>{c.s.plan_name}</h3>
          <div class="price">{Number(c.s.price).toLocaleString("ko-KR")}원 <small>/ 월</small></div>
          <ul>
            <li>{BRAND.name} PC 제품 내 <b>광고 완전 제거</b></li>
            <li>앞으로 나올 모찌PDF·모찌압축에도 적용</li>
            <li>PC 여러 대에서 같은 계정으로 사용</li>
            <li>언제든 해지 · 남은 기간까지 이용</li>
          </ul>
          {c.premium ? <a class="btn btn-block" href="/mypage">이미 구독 중이에요 ⭐</a>
            : <a class="btn btn-pink btn-block btn-lg" href="/subscribe">지금 구독하기</a>}
        </div>
      </div>
    </div>
    <section class="section" id="faq">
      <div class="container faq">
        <h2>자주 묻는 질문</h2>
        <details open><summary>PC 프로그램에는 어떻게 적용되나요?</summary><p>모찌캡처 결과창 오른쪽 위의 [로그인] 버튼을 누르면 웹사이트가 열립니다. 같은 계정으로 로그인하고 [연결 승인]을 누르면 바로 광고가 사라져요.</p></details>
        <details><summary>해지는 어떻게 하나요?</summary><p>마이페이지 → [구독 해지]를 누르세요. 이미 결제한 기간이 끝날 때까지는 계속 광고 없이 쓸 수 있고, 그 다음 달부터 결제되지 않습니다.</p></details>
        <details><summary>PC는 몇 대까지 쓸 수 있나요?</summary><p>한 계정으로 PC {c.s.device_limit}대까지 로그인할 수 있어요. 쓰지 않는 PC는 마이페이지에서 언제든 해제할 수 있어요.</p></details>
        <details><summary>결제는 어떤 방법이 있나요?</summary><p>신용·체크카드 자동결제로 매달 같은 날 결제됩니다. 결제 내역은 마이페이지에서 확인할 수 있어요.</p></details>
      </div>
    </section>
  </Layout>
);

const SocialIcons = {
  naver: raw(`<svg viewBox="0 0 24 24"><path fill="#fff" d="M4 4h5.3l5.4 7.9V4H20v16h-5.3L9.3 12.1V20H4z"/></svg>`),
  kakao: raw(`<svg viewBox="0 0 24 24"><path fill="#191919" d="M12 3C6.5 3 2 6.6 2 11c0 2.8 1.8 5.3 4.6 6.7L5.5 21.5l4.3-2.9c.7.1 1.4.2 2.2.2 5.5 0 10-3.6 10-8S17.5 3 12 3z"/></svg>`),
  google: raw(`<svg viewBox="0 0 24 24"><path fill="#4285F4" d="M22 12.2c0-.7-.1-1.4-.2-2H12v3.9h5.6a4.8 4.8 0 0 1-2.1 3.1v2.6h3.4c2-1.8 3.1-4.5 3.1-7.6z"/><path fill="#34A853" d="M12 22c2.8 0 5.2-.9 6.9-2.5l-3.4-2.6c-.9.6-2.1 1-3.5 1-2.7 0-5-1.8-5.8-4.3H2.7v2.7A10 10 0 0 0 12 22z"/><path fill="#FBBC05" d="M6.2 13.6a6 6 0 0 1 0-3.8V7.1H2.7a10 10 0 0 0 0 9.2z"/><path fill="#EA4335" d="M12 6c1.5 0 2.9.5 4 1.5l3-3A10 10 0 0 0 2.7 7.1l3.5 2.7C7 7.8 9.3 6 12 6z"/></svg>`),
  apple: raw(`<svg viewBox="0 0 24 24"><path fill="#fff" d="M16.4 12.6c0-2.6 2.1-3.8 2.2-3.9-1.2-1.8-3.1-2-3.7-2-1.6-.2-3.1.9-3.9.9-.8 0-2-.9-3.4-.9-1.7 0-3.3 1-4.2 2.6-1.8 3.1-.5 7.7 1.3 10.2.9 1.2 1.9 2.6 3.2 2.6 1.3-.1 1.8-.8 3.3-.8 1.6 0 2 .8 3.4.8 1.4 0 2.3-1.3 3.1-2.5 1-1.4 1.4-2.8 1.4-2.9-.1 0-2.7-1-2.7-4.1zM13.9 5c.7-.9 1.2-2 1-3.2-1 0-2.3.7-3 1.6-.7.8-1.2 2-1.1 3.1 1.2.1 2.3-.6 3.1-1.5z"/></svg>`),
};

export const Login = ({ c, enabled, next }: { c: PageCtx; enabled: Record<string, boolean>; next: string }) => {
  const q = next ? `?next=${encodeURIComponent(next)}` : "";
  return (
    <Layout c={c} title="로그인">
      <div class="auth container">
        <img src="/img/mochi.svg" alt="" style="width:110px" />
        <h1>로그인하고 더 말랑한 혜택을<br />누리세요!</h1>
        <p class="sub">하나의 계정으로 모든 {BRAND.name} 제품을 이용할 수 있어요.</p>
        <a class={`social naver ${enabled.naver ? "" : "off"}`} href={`/login/naver${q}`}>{SocialIcons.naver}네이버 로그인</a>
        <a class={`social kakao ${enabled.kakao ? "" : "off"}`} href={`/login/kakao${q}`}>{SocialIcons.kakao}카카오 로그인</a>
        <a class={`social google ${enabled.google ? "" : "off"}`} href={`/login/google${q}`}>{SocialIcons.google}구글 로그인</a>
        <a class="social apple off" href="/login/apple">{SocialIcons.apple}Apple로 로그인</a>
        <div class="divider">또는 이메일로 로그인</div>
        <form method="post" class="form" action="/login">
          <Csrf c={c} /><input type="hidden" name="next" value={next} />
          <div class="field"><input class="input" type="email" name="email" placeholder="이메일" required autofocus /></div>
          <div class="field"><input class="input" type="password" name="password" placeholder="비밀번호" required /></div>
          <button class="btn btn-pink btn-block btn-lg">로그인</button>
        </form>
        <div class="auth-links"><a href={`mailto:${c.email}?subject=비밀번호 찾기`}>비밀번호 찾기</a><a class="pink" href={`/signup${q}`}>이메일로 회원가입 ›</a></div>
        <div class="member-box">
          <h3>{BRAND.name} 회원이 되면?</h3>
          <p class="muted">모찌캡처, 모찌PDF 등 모든 제품을 하나의 계정으로!<br />{c.s.plan_name} 구독으로 광고 없이 쓸 수 있어요.</p>
          <div class="member-icons">
            <span style="background:#ffe3eb">📸</span><span style="background:#e3f5ec">📄</span><span style="background:#fff1e0">🗜️</span><span style="background:#ece8ff">✨</span>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export const Signup = ({ c, next, form }: { c: PageCtx; next: string; form: Record<string, string> }) => (
  <Layout c={c} title="회원가입">
    <div class="auth container">
      <img src="/img/mochi.svg" alt="" style="width:90px" />
      <h1>{BRAND.name} 회원가입</h1>
      <p class="sub">30초면 끝나요! 🍡</p>
      <form method="post" class="form" action="/signup">
        <Csrf c={c} /><input type="hidden" name="next" value={next} />
        <div class="field"><label>이메일</label><input class="input" type="email" name="email" required value={form.email || ""} /></div>
        <div class="field"><label>이름 (닉네임)</label><input class="input" name="name" value={form.name || ""} /></div>
        <div class="field"><label>비밀번호 (8자 이상)</label><input class="input" type="password" name="password" required minlength={8} /></div>
        <div class="field"><label>비밀번호 확인</label><input class="input" type="password" name="password2" required /></div>
        <label class="check"><input type="checkbox" name="agree" required /> <span><a href="/terms" target="_blank"><u>이용약관</u></a>과 <a href="/privacy" target="_blank"><u>개인정보처리방침</u></a>에 동의합니다 (필수)</span></label>
        <label class="check"><input type="checkbox" name="marketing" /> 새 제품·이벤트 소식 받기 (선택)</label>
        <button class="btn btn-pink btn-block btn-lg" style="margin-top:12px">가입하기</button>
      </form>
      <div class="auth-links"><span class="muted">이미 회원이신가요?</span><a class="pink" href={`/login${next ? "?next=" + encodeURIComponent(next) : ""}`}>로그인 ›</a></div>
    </div>
  </Layout>
);

const PROVIDER_NAMES: Record<string, string> = { email: "이메일 가입", naver: "네이버", kakao: "카카오", google: "구글" };

export const MyPage = ({ c, user, sub, lastSub, devices, payments }: {
  c: PageCtx; user: User; sub: Subscription | null; lastSub: Subscription | null; devices: Device[]; payments: Payment[];
}) => (
  <Layout c={c} title="마이페이지">
    <div class="page container">
      <h1>{displayName(user)} 님, 반가워요! 🍡</h1>
      <div class="grid-2">
        <div class={`panel status-card ${sub ? "" : "free"}`}>
          {sub ? (
            <>
              <div>⭐ {c.s.plan_name} {SUB_STATUS[sub.status]}</div>
              <div class="big">광고 없이 이용 중</div>
              <div>{sub.status === "active" && sub.method !== "manual"
                ? `다음 결제일 ${fmt(sub.current_period_end, "korean")} · ${won(sub.price)}`
                : `${fmt(sub.current_period_end, "korean")}까지 이용 가능`}</div>
              <div style="margin-top:16px">
                {sub.status === "active" && sub.method !== "manual" && (
                  <form method="post" action="/subscription/cancel" class="inline" onsubmit="return confirm('구독을 해지할까요? 남은 기간까지는 계속 이용할 수 있어요.')">
                    <Csrf c={c} /><button class="btn btn-sm">구독 해지</button></form>)}
                {sub.status === "canceled" && sub.method !== "manual" && (
                  <form method="post" action="/subscription/resume" class="inline"><Csrf c={c} /><button class="btn btn-sm">해지 취소 (구독 계속)</button></form>)}
              </div>
            </>
          ) : (
            <>
              <div>무료 회원</div>
              <div class="big">광고와 함께 무료 이용 중</div>
              <div class="muted">{c.s.plan_name} 월 {won(Number(c.s.price))}으로 광고를 없애 보세요.</div>
              <a class="btn btn-pink" style="margin-top:16px" href="/subscribe">광고 없이 쓰기</a>
              {lastSub && lastSub.status === "expired" && <p class="small muted">이전 구독은 {fmt(lastSub.current_period_end, "date")}에 종료되었습니다.</p>}
            </>
          )}
        </div>
        <div class="panel">
          <h2>👤 내 정보</h2>
          <form method="post" action="/mypage/profile" class="form"><Csrf c={c} />
            <div class="field"><label>이메일</label><input class="input" value={user.email} disabled /> <span class="small muted">{PROVIDER_NAMES[user.provider] || user.provider} 계정</span></div>
            <div class="field"><label>이름</label><input class="input" name="name" value={user.name} /></div>
            {user.provider === "email" && <div class="field"><label>새 비밀번호 (바꿀 때만)</label><input class="input" type="password" name="new_password" minlength={8} /></div>}
            <label class="check"><input type="checkbox" name="marketing" checked={!!user.marketing} /> 새 제품·이벤트 소식 받기</label>
            <button class="btn btn-sm btn-dark">저장</button>
          </form>
        </div>
      </div>
      <div class="panel">
        <h2>💻 내 PC 기기 <Badge>{new Set(devices.map((d) => d.device_id)).size} / {c.s.device_limit}대</Badge></h2>
        <p class="small muted">모찌캡처에서 [로그인]한 PC 목록입니다. 쓰지 않는 PC는 해제하세요.</p>
        <table class="table">
          <tr><th>PC 이름</th><th>프로그램</th><th>연결일</th><th>마지막 사용</th><th></th></tr>
          {devices.length ? devices.map((d) => (
            <tr><td><b>{d.device_name}</b></td><td>{APP_NAMES[d.app] || d.app} {d.app_version}</td><td>{fmt(d.created_at, "date")}</td><td>{fmt(d.last_seen_at)}</td>
              <td><form method="post" action={`/mypage/devices/${d.id}/revoke`} onsubmit="return confirm('이 PC의 로그인을 해제할까요?')"><Csrf c={c} /><button class="btn btn-sm btn-danger">해제</button></form></td></tr>
          )) : <tr><td colspan={5} class="empty">아직 연결된 PC가 없어요. 모찌캡처 결과창의 [로그인]을 눌러 연결하세요.</td></tr>}
        </table>
      </div>
      <div class="panel">
        <h2>🧾 결제 내역</h2>
        <table class="table">
          <tr><th>결제일</th><th>상품</th><th>금액</th><th>결제수단</th><th>상태</th></tr>
          {payments.length ? payments.map((p) => (
            <tr><td>{fmt(p.paid_at)}</td><td>{p.order_name}</td><td>{won(p.amount)}</td><td>{p.card || SUB_METHOD[p.method] || p.method}</td>
              <td><Badge kind={PAY_BADGE[p.status]}>{PAY_STATUS[p.status]}</Badge></td></tr>
          )) : <tr><td colspan={5} class="empty">결제 내역이 없어요.</td></tr>}
        </table>
      </div>
    </div>
  </Layout>
);

export const Checkout = ({ c, toss, clientKey, customerKey, siteUrl }: { c: PageCtx; toss: boolean; clientKey: string; customerKey: string; siteUrl: string }) => (
  <Layout c={c} title="구독하기" head={toss ? <script src="https://js.tosspayments.com/v2/standard"></script> : undefined}>
    <div class="auth container">
      <img src="/img/mochi.svg" alt="" style="width:100px" />
      <h1>{c.s.plan_name} 구독하기</h1>
      <p class="sub">광고 없이 쾌적하게! 언제든 해지할 수 있어요.</p>
      <div class="panel" style="text-align:left">
        <dl class="dl">
          <dt>상품</dt><dd><b>{c.s.plan_name}</b> (1개월 자동결제)</dd>
          <dt>금액</dt><dd><b style="color:var(--pink);font-size:20px">{won(Number(c.s.price))}</b> / 월 (부가세 포함)</dd>
          <dt>결제일</dt><dd>오늘 첫 결제 후, 매달 같은 날 자동 결제</dd>
          <dt>계정</dt><dd>{c.me?.email}</dd>
        </dl>
      </div>
      {toss ? (
        <>
          <button id="pay" class="btn btn-pink btn-block btn-lg">카드 등록하고 구독 시작</button>
          <p class="small muted">결제는 토스페이먼츠를 통해 안전하게 처리됩니다.</p>
          {raw(`<script>
            const payment = TossPayments(${JSON.stringify(clientKey)}).payment({ customerKey: ${JSON.stringify(customerKey)} });
            document.getElementById("pay").onclick = () => payment.requestBillingAuth({
              method: "CARD",
              successUrl: ${JSON.stringify(siteUrl + "/billing/success")},
              failUrl: ${JSON.stringify(siteUrl + "/billing/fail")},
              customerEmail: ${JSON.stringify(c.me?.email || "")},
              customerName: ${JSON.stringify(c.me ? displayName(c.me) : "")},
            });
          </script>`)}
        </>
      ) : (
        <>
          <form method="post" action="/subscribe/test"><Csrf c={c} /><button class="btn btn-pink btn-block btn-lg">🧪 테스트 결제로 구독 시작</button></form>
          <p class="small muted">지금은 테스트 모드라 실제 돈이 나가지 않습니다.<br />운영할 때는 Cloudflare 설정에 토스페이먼츠 키를 넣으세요.</p>
        </>
      )}
      <p class="small muted">구독하면 <a href="/terms"><u>이용약관</u></a>(정기결제 조항 포함)에 동의하는 것으로 봅니다.</p>
    </div>
  </Layout>
);

export const DevicePage = ({ c, code, dc, expired }: { c: PageCtx; code: string; dc: DeviceCode | null; expired: boolean }) => (
  <Layout c={c} title="PC 프로그램 연결">
    <div class="device-box container">
      <img src="/img/mochi.svg" alt="" style="width:110px" />
      {dc && dc.status === "pending" && !expired ? (
        <>
          <h1>PC 프로그램과 연결할까요?</h1>
          <p class="muted"><b>{dc.device_name}</b> PC의 <b>{APP_NAMES[dc.app] || dc.app}</b>에서 로그인을 요청했어요.<br />PC 화면에 보이는 코드와 같은지 확인하세요.</p>
          <div class="device-code">{dc.user_code}</div>
          <form method="post" action="/device"><Csrf c={c} /><input type="hidden" name="code" value={dc.user_code} />
            <button class="btn btn-pink btn-lg" name="action" value="approve">연결 승인</button>{" "}
            <button class="btn btn-lg" name="action" value="deny">거절</button>
          </form>
          <p class="small muted" style="margin-top:20px">로그인 계정: {c.me?.email}</p>
        </>
      ) : (
        <>
          <h1>PC 연결 코드 입력</h1>
          <p class="muted">{code ? "코드가 맞지 않거나 시간이 지났어요. " : ""}PC 프로그램 화면에 보이는 8자리 코드를 입력하세요.</p>
          <form method="get" action="/device" class="form" style="max-width:320px;margin:20px auto">
            <input class="input center" name="code" placeholder="ABCD-1234" style="font-size:22px;letter-spacing:3px" required />
            <button class="btn btn-pink btn-block" style="margin-top:10px">확인</button>
          </form>
        </>
      )}
    </div>
  </Layout>
);

export const DeviceDone = ({ c, dc, premium }: { c: PageCtx; dc: DeviceCode; premium: boolean }) => (
  <Layout c={c} title="연결 완료">
    <div class="device-box container">
      <img src="/img/mochi.svg" alt="" style="width:120px" />
      <h1>연결 완료! 🎉</h1>
      <p class="muted"><b>{dc.device_name}</b> PC에 로그인되었어요. 이 창은 닫고 PC 프로그램으로 돌아가세요.</p>
      {premium ? <p><span class="badge" style="font-size:15px;padding:8px 16px">⭐ {c.s.plan_name} — 광고 없이 이용할 수 있어요</span></p>
        : <><p>지금은 무료 회원이라 광고가 보여요.</p><a class="btn btn-pink btn-lg" href="/subscribe">{c.s.plan_name}로 광고 없애기</a></>}
    </div>
  </Layout>
);

export const Policy = ({ c, kind }: { c: PageCtx; kind: "terms" | "privacy" }) => (
  <Layout c={c} title={kind === "terms" ? "이용약관" : "개인정보처리방침"}>
    <div class="page container" style="max-width:820px">
      {kind === "terms" ? (
        <>
          <h1>이용약관</h1>
          <p class="muted">※ 아래는 기본 예시입니다. 실제 서비스 전에 꼭 법률 검토를 받아 수정하세요.</p>
          <h3>제1조 (목적)</h3><p>이 약관은 {c.company}(이하 "회사")가 제공하는 {BRAND.name} 서비스의 이용 조건과 절차를 정합니다.</p>
          <h3>제2조 (무료 서비스와 광고)</h3><p>회사는 PC 프로그램을 무료로 제공하며, 무료 이용 시 프로그램 화면에 광고가 표시될 수 있습니다.</p>
          <h3>제3조 (유료 구독 · 정기결제)</h3><p>{c.s.plan_name}은 월 {won(Number(c.s.price))}이며 최초 결제일 기준 매월 자동 결제됩니다. 회원은 언제든 마이페이지에서 해지할 수 있으며, 해지 시 이미 결제한 이용기간 종료일까지 서비스를 이용할 수 있습니다.</p>
          <h3>제4조 (청약철회 및 환불)</h3><p>결제 후 7일 이내이고 유료 혜택을 사용하지 않은 경우 전액 환불됩니다. 그 밖의 환불은 관련 법령과 회사 정책에 따릅니다.</p>
          <h3>제5조 (기기 이용)</h3><p>하나의 계정은 회사가 정한 대수의 PC에서 이용할 수 있습니다.</p>
        </>
      ) : (
        <>
          <h1>개인정보처리방침</h1>
          <p class="muted">※ 아래는 기본 예시입니다. 실제 서비스 전에 꼭 법률 검토를 받아 수정하세요.</p>
          <h3>1. 수집하는 항목</h3><p>이메일, 이름(닉네임), 소셜 로그인 식별값, 결제 기록(카드사·카드번호 일부), PC 이름, 접속 기록</p>
          <h3>2. 이용 목적</h3><p>회원 관리, 구독 결제와 라이선스 확인, 고객 문의 응대, (동의한 경우) 새 소식 안내</p>
          <h3>3. 보관 기간</h3><p>회원 탈퇴 시 즉시 삭제합니다. 단, 전자상거래법에 따라 결제 기록은 5년간 보관합니다.</p>
          <h3>4. 위탁</h3><p>결제 처리: 토스페이먼츠(주) · 서버 운영: Cloudflare, Inc.</p>
          <h3>5. 문의</h3><p>{c.email}</p>
        </>
      )}
    </div>
  </Layout>
);

export const ErrorPage = ({ c, code, msg }: { c: PageCtx; code: number; msg: string }) => (
  <Layout c={c} title={`오류 ${code}`}>
    <div class="device-box container">
      <img src="/img/mochi.svg" alt="" style="width:120px;transform:rotate(-8deg)" />
      <h1>앗, {code}</h1>
      <p class="muted">{msg}</p>
      <a class="btn btn-pink" href="/">홈으로</a>
    </div>
  </Layout>
);
