// 관리자 사이트 화면
import { APP_NAMES, adRunning, fmt, PAY_STATUS, SUB_METHOD, SUB_STATUS, won,
  type Ad, type Device, type Payment, type Product, type Subscription, type User } from "../db";
import { AdminLayout, Badge, Csrf, PAY_BADGE, Pager, SUB_BADGE, type PageCtx } from "./layout";

const num = (n: number) => Number(n || 0).toLocaleString("ko-KR");
export const adImageUrl = (img: string) => (img.startsWith("http") ? img : `/files/${img}`);

export interface Stats {
  users: number; new_users: number; premium: number; revenue_month: number; devices: number;
  ad_views: number; ad_clicks: number; failed: number; mrr: number; conversion: number;
}
export interface Month { label: string; revenue: number; signups: number }

export const Dashboard = ({ c, stats, months, recentUsers, premiumIds, recentPayments }: {
  c: PageCtx; stats: Stats; months: Month[]; recentUsers: User[]; premiumIds: Set<number>; recentPayments: Payment[];
}) => {
  const maxRev = Math.max(1, ...months.map((m) => m.revenue));
  const maxSign = Math.max(1, ...months.map((m) => m.signups));
  const ctr = stats.ad_views ? ((stats.ad_clicks * 100) / stats.ad_views).toFixed(2) : "0";
  return (
    <AdminLayout c={c}>
      <div class="admin-top">
        <h1>대시보드</h1>
        <form method="post" action="/admin/renew-now" onsubmit="return confirm('기간이 끝난 구독의 정기결제를 지금 실행할까요?')"><Csrf c={c} /><button class="btn btn-sm btn-dark">🔁 정기결제 지금 실행</button></form>
      </div>
      <div class="kpis">
        <div class="kpi"><span>전체 회원</span><b>{num(stats.users)}명</b><em>이번 달 +{stats.new_users}</em></div>
        <div class="kpi"><span>유료 구독자</span><b>{num(stats.premium)}명</b><em>전환율 {stats.conversion}%</em></div>
        <div class="kpi"><span>월 반복 매출(MRR)</span><b>{won(stats.mrr)}</b><em>구독자 × 월 요금</em></div>
        <div class="kpi"><span>이번 달 결제액</span><b>{won(stats.revenue_month)}</b>{stats.failed > 0 && <em style="color:#c53030">결제 실패 {stats.failed}건</em>}</div>
        <div class="kpi"><span>로그인된 PC</span><b>{num(stats.devices)}대</b></div>
        <div class="kpi"><span>광고 노출</span><b>{num(stats.ad_views)}회</b></div>
        <div class="kpi"><span>광고 클릭</span><b>{num(stats.ad_clicks)}회</b><em>CTR {ctr}%</em></div>
        <div class="kpi"><span>구독 요금</span><b>{won(Number(c.s.price))}</b><em>{c.s.plan_name}</em></div>
      </div>
      <div class="grid-2">
        <div class="panel"><h2>월별 결제액</h2>
          <div class="bars">{months.map((m) => <div class="bar"><b>{num(m.revenue)}</b><i style={`height:${Math.round((m.revenue / maxRev) * 140)}px`}></i>{m.label}</div>)}</div></div>
        <div class="panel"><h2>월별 신규 가입</h2>
          <div class="bars">{months.map((m) => <div class="bar mint"><b>{m.signups}</b><i style={`height:${Math.round((m.signups / maxSign) * 140)}px`}></i>{m.label}</div>)}</div></div>
      </div>
      <div class="grid-2">
        <div class="panel"><h2>최근 가입 회원</h2>
          <table class="table"><tr><th>이메일</th><th>가입일</th><th>등급</th></tr>
            {recentUsers.map((u) => <tr><td><a href={`/admin/users/${u.id}`}><b>{u.email}</b></a></td><td>{fmt(u.created_at, "short")}</td>
              <td>{premiumIds.has(u.id) ? <Badge>유료</Badge> : <Badge kind="gray">무료</Badge>}</td></tr>)}
          </table></div>
        <div class="panel"><h2>최근 결제</h2>
          <table class="table"><tr><th>회원</th><th>금액</th><th>상태</th><th>일시</th></tr>
            {recentPayments.length ? recentPayments.map((p) => <tr><td>{p.email}</td><td>{won(p.amount)}</td>
              <td><Badge kind={PAY_BADGE[p.status]}>{PAY_STATUS[p.status]}</Badge></td><td>{fmt(p.paid_at, "short")}</td></tr>)
              : <tr><td colspan={4} class="empty">결제가 아직 없어요.</td></tr>}
          </table></div>
      </div>
    </AdminLayout>
  );
};

const Tabs = ({ items, current, base }: { items: [string, string][]; current: string; base: (k: string) => string }) => (
  <div class="toolbar tabs">{items.map(([k, n]) => <a class={current === k ? "on" : ""} href={base(k)}>{n}</a>)}</div>
);

export const Users = ({ c, items, premiumIds, deviceCounts, kw, kind, page, pages }: {
  c: PageCtx; items: User[]; premiumIds: Set<number>; deviceCounts: Map<number, number>; kw: string; kind: string; page: number; pages: number;
}) => (
  <AdminLayout c={c}>
    <div class="admin-top"><h1>회원 관리</h1></div>
    <div class="toolbar">
      <form class="toolbar" style="margin:0" method="get" action="/admin/users">
        <input class="input" name="q" value={kw} placeholder="이메일·이름 검색" /><input type="hidden" name="kind" value={kind} /><button class="btn btn-sm">검색</button>
      </form>
      <Tabs items={[["", "전체"], ["premium", "유료"], ["free", "무료"], ["admin", "관리자"], ["suspended", "정지"]]} current={kind}
        base={(k) => `/admin/users?kind=${k}&q=${encodeURIComponent(kw)}`} />
    </div>
    <div class="panel">
      <table class="table">
        <tr><th>#</th><th>이메일</th><th>이름</th><th>가입 방법</th><th>등급</th><th>PC</th><th>가입일</th><th>최근 로그인</th><th>상태</th></tr>
        {items.length ? items.map((u) => (
          <tr><td>{u.id}</td><td><a href={`/admin/users/${u.id}`}><b>{u.email}</b></a> {u.role === "admin" && <Badge kind="peach">관리자</Badge>}</td>
            <td>{u.name}</td><td>{u.provider}</td>
            <td>{premiumIds.has(u.id) ? <Badge>⭐ 유료</Badge> : <Badge kind="gray">무료</Badge>}</td>
            <td>{deviceCounts.get(u.id) || 0}</td><td>{fmt(u.created_at, "date")}</td><td>{fmt(u.last_login_at, "short")}</td>
            <td>{u.status === "active" ? <Badge kind="mint">정상</Badge> : <Badge kind="red">정지</Badge>}</td></tr>
        )) : <tr><td colspan={9} class="empty">회원이 없습니다.</td></tr>}
      </table>
      <Pager page={page} pages={pages} base={`/admin/users?kind=${kind}&q=${encodeURIComponent(kw)}`} />
    </div>
  </AdminLayout>
);

export const UserDetail = ({ c, u, sub, subs, devices, payments }: {
  c: PageCtx; u: User; sub: Subscription | null; subs: Subscription[]; devices: Device[]; payments: Payment[];
}) => (
  <AdminLayout c={c}>
    <div class="admin-top"><h1>{u.email}</h1><a class="btn btn-sm" href="/admin/users">← 목록</a></div>
    <div class="grid-2">
      <div class="panel"><h2>기본 정보</h2>
        <form method="post" action={`/admin/users/${u.id}/update`} class="form"><Csrf c={c} />
          <dl class="dl" style="margin-bottom:14px"><dt>가입</dt><dd>{fmt(u.created_at)} ({u.provider})</dd><dt>최근 로그인</dt><dd>{fmt(u.last_login_at)}</dd>
            <dt>소식 수신</dt><dd>{u.marketing ? "동의" : "미동의"}</dd></dl>
          <div class="form-grid">
            <div class="field"><label>이름</label><input class="input" name="name" value={u.name} /></div>
            <div class="field"><label>권한</label><select class="input" name="role">
              <option value="user" selected={u.role === "user"}>일반 회원</option><option value="admin" selected={u.role === "admin"}>관리자</option></select></div>
            <div class="field"><label>상태</label><select class="input" name="status">
              <option value="active" selected={u.status === "active"}>정상</option><option value="suspended" selected={u.status === "suspended"}>이용 정지</option></select></div>
            <div class="field full"><label>관리자 메모</label><textarea class="input" name="memo" rows={3}>{u.memo}</textarea></div>
          </div>
          <button class="btn btn-sm btn-dark">저장</button>
        </form>
      </div>
      <div class="panel"><h2>라이선스 (구독)</h2>
        {sub ? <p><Badge>⭐ {SUB_STATUS[sub.status]}</Badge> {SUB_METHOD[sub.method]} · <b>{fmt(sub.current_period_end, "date")}</b>까지</p>
          : <p><Badge kind="gray">무료 회원</Badge></p>}
        <form method="post" action={`/admin/users/${u.id}/grant`} class="toolbar"><Csrf c={c} />
          <select class="input" name="months">{[1, 3, 6, 12, 24].map((m) => <option value={m}>{m}개월</option>)}</select>
          <input class="input" name="note" placeholder="사유 (예: 이벤트 당첨)" />
          <button class="btn btn-sm btn-pink">{sub ? "기간 연장" : "이용권 부여"}</button>
        </form>
        {sub && <form method="post" action={`/admin/users/${u.id}/end-sub`} onsubmit="return confirm('구독을 즉시 종료할까요?')"><Csrf c={c} /><button class="btn btn-sm btn-danger">구독 즉시 종료</button></form>}
        <h2 style="margin-top:24px">구독 이력</h2>
        <table class="table"><tr><th>시작</th><th>종료(예정)</th><th>방식</th><th>상태</th></tr>
          {subs.length ? subs.map((s) => <tr><td>{fmt(s.started_at, "date")}</td><td>{fmt(s.current_period_end, "date")}</td><td>{SUB_METHOD[s.method]}</td><td>{SUB_STATUS[s.status]}</td></tr>)
            : <tr><td colspan={4} class="empty">없음</td></tr>}</table>
      </div>
    </div>
    <div class="panel"><h2>로그인된 PC <form method="post" action={`/admin/users/${u.id}/revoke-devices`} class="inline"><Csrf c={c} /><button class="btn btn-sm btn-danger">전체 해제</button></form></h2>
      <table class="table"><tr><th>PC 이름</th><th>프로그램</th><th>연결일</th><th>마지막 사용</th><th>상태</th></tr>
        {devices.length ? devices.map((d) => <tr><td>{d.device_name}</td><td>{APP_NAMES[d.app] || d.app} {d.app_version}</td><td>{fmt(d.created_at)}</td><td>{fmt(d.last_seen_at)}</td><td>{d.revoked ? "해제됨" : "사용 중"}</td></tr>)
          : <tr><td colspan={5} class="empty">없음</td></tr>}</table>
    </div>
    <div class="panel"><h2>결제 내역</h2>
      <table class="table"><tr><th>일시</th><th>주문번호</th><th>금액</th><th>상태</th></tr>
        {payments.length ? payments.map((p) => <tr><td>{fmt(p.paid_at)}</td><td class="small">{p.order_id}</td><td>{won(p.amount)}</td><td>{PAY_STATUS[p.status]} {p.fail_reason}</td></tr>)
          : <tr><td colspan={4} class="empty">없음</td></tr>}</table>
    </div>
  </AdminLayout>
);

export const Subscriptions = ({ c, items, status, page, pages }: { c: PageCtx; items: Subscription[]; status: string; page: number; pages: number }) => (
  <AdminLayout c={c}>
    <div class="admin-top"><h1>구독 관리</h1></div>
    <Tabs items={[["", "전체"], ...Object.entries(SUB_STATUS)] as [string, string][]} current={status} base={(k) => `/admin/subscriptions?status=${k}`} />
    <div class="panel"><table class="table">
      <tr><th>#</th><th>회원</th><th>방식</th><th>카드</th><th>요금</th><th>시작일</th><th>다음 결제/종료</th><th>상태</th></tr>
      {items.length ? items.map((s) => <tr><td>{s.id}</td><td><a href={`/admin/users/${s.user_id}`}><b>{s.email}</b></a></td><td>{SUB_METHOD[s.method]}</td><td>{s.card_info}</td>
        <td>{won(s.price)}</td><td>{fmt(s.started_at, "date")}</td><td>{fmt(s.current_period_end, "date")}</td><td><Badge kind={SUB_BADGE[s.status]}>{SUB_STATUS[s.status]}</Badge></td></tr>)
        : <tr><td colspan={8} class="empty">구독이 없습니다.</td></tr>}
    </table><Pager page={page} pages={pages} base={`/admin/subscriptions?status=${status}`} /></div>
  </AdminLayout>
);

export const Payments = ({ c, items, status, total, page, pages }: { c: PageCtx; items: Payment[]; status: string; total: number; page: number; pages: number }) => (
  <AdminLayout c={c}>
    <div class="admin-top"><h1>결제 내역</h1><div class="kpi" style="padding:10px 18px"><span>누적 결제액</span><b style="font-size:20px">{won(total)}</b></div></div>
    <Tabs items={[["", "전체"], ["paid", "결제 완료"], ["failed", "결제 실패"], ["refunded", "환불"]]} current={status} base={(k) => `/admin/payments?status=${k}`} />
    <div class="panel"><table class="table">
      <tr><th>일시</th><th>회원</th><th>상품</th><th>금액</th><th>결제수단</th><th>주문번호</th><th>상태</th><th></th></tr>
      {items.length ? items.map((p) => <tr><td>{fmt(p.paid_at)}</td><td><a href={`/admin/users/${p.user_id}`}>{p.email}</a></td><td>{p.order_name}</td><td><b>{won(p.amount)}</b></td>
        <td>{p.card || SUB_METHOD[p.method] || p.method}</td><td class="small muted">{p.order_id}</td>
        <td><Badge kind={PAY_BADGE[p.status]}>{PAY_STATUS[p.status]}</Badge>{p.fail_reason && <div class="small muted">{p.fail_reason}</div>}</td>
        <td>{p.status === "paid" && <form method="post" action={`/admin/payments/${p.id}/refund`} onsubmit={`return confirm('${won(p.amount)}을 환불할까요?')`}><Csrf c={c} /><button class="btn btn-sm btn-danger">환불</button></form>}</td></tr>)
        : <tr><td colspan={8} class="empty">결제 내역이 없습니다.</td></tr>}
    </table><Pager page={page} pages={pages} base={`/admin/payments?status=${status}`} /></div>
  </AdminLayout>
);

export const Devices = ({ c, items, premiumIds, show, page, pages }: { c: PageCtx; items: Device[]; premiumIds: Set<number>; show: string; page: number; pages: number }) => (
  <AdminLayout c={c}>
    <div class="admin-top"><h1>라이선스 (로그인된 PC)</h1></div>
    <Tabs items={[["", "사용 중"], ["all", "해제된 기기 포함"]]} current={show} base={(k) => `/admin/devices?show=${k}`} />
    <div class="panel"><table class="table">
      <tr><th>회원</th><th>PC 이름</th><th>프로그램</th><th>등급</th><th>연결일</th><th>마지막 사용</th><th></th></tr>
      {items.length ? items.map((d) => <tr><td><a href={`/admin/users/${d.user_id}`}>{d.email}</a></td><td><b>{d.device_name}</b></td><td>{APP_NAMES[d.app] || d.app} {d.app_version}</td>
        <td>{premiumIds.has(d.user_id) ? <Badge>⭐ 광고 제거</Badge> : <Badge kind="gray">무료(광고)</Badge>}</td><td>{fmt(d.created_at)}</td><td>{fmt(d.last_seen_at)}</td>
        <td>{!d.revoked ? <form method="post" action={`/admin/devices/${d.id}/revoke`}><Csrf c={c} /><button class="btn btn-sm btn-danger">해제</button></form> : <span class="muted small">해제됨</span>}</td></tr>)
        : <tr><td colspan={7} class="empty">로그인된 PC가 없습니다.</td></tr>}
    </table><Pager page={page} pages={pages} base={`/admin/devices?show=${show}`} /></div>
  </AdminLayout>
);

const APPS_LABEL: Record<string, string> = { all: "전체", capture: "모찌캡처", pdf: "모찌PDF" };
const ctrOf = (a: Ad) => (a.views ? ((a.clicks * 100) / a.views).toFixed(2) : "0");

export const Ads = ({ c, items }: { c: PageCtx; items: Ad[] }) => (
  <AdminLayout c={c}>
    <div class="admin-top"><h1>광고 관리</h1><a class="btn btn-pink btn-sm" href="/admin/ads/new">+ 새 광고</a></div>
    <p class="muted">무료 사용자의 PC 프로그램에 보이는 광고입니다. <b>배너</b> = 결과창 오른쪽 위, <b>팝업</b> = 캡처 후 결과창 왼쪽 아래.</p>
    <div class="panel"><table class="table">
      <tr><th>미리보기</th><th>제목</th><th>위치</th><th>제품</th><th>기간</th><th>비중</th><th>노출</th><th>클릭</th><th>CTR</th><th>상태</th><th></th></tr>
      {items.length ? items.map((a) => <tr>
        <td>{a.image ? <img class="ad-thumb" src={adImageUrl(a.image)} /> : <div class="ad-thumb" style={`background:${a.bg_color}`}></div>}</td>
        <td><a href={`/admin/ads/${a.id}`}><b>{a.title}</b></a><div class="small muted">{a.subtitle}</div></td>
        <td>{a.placement === "banner" ? "배너" : "팝업"}</td><td>{APPS_LABEL[a.apps] || a.apps}</td>
        <td class="small">{a.start_at ? fmt(a.start_at, "date").slice(5) : "시작"} ~ {a.end_at ? fmt(a.end_at, "date").slice(5) : "계속"}</td>
        <td>{a.weight}</td><td>{num(a.views)}</td><td>{num(a.clicks)}</td><td>{ctrOf(a)}%</td>
        <td><form method="post" action={`/admin/ads/${a.id}/toggle`}><Csrf c={c} /><button class={`badge ${adRunning(a) ? "badge-mint" : "badge-gray"}`} style="border:0;cursor:pointer">{adRunning(a) ? "노출 중" : !a.active ? "중지" : "기간 외"}</button></form></td>
        <td><form method="post" action={`/admin/ads/${a.id}/delete`} onsubmit="return confirm('삭제할까요?')"><Csrf c={c} /><button class="btn btn-sm btn-danger">삭제</button></form></td></tr>)
        : <tr><td colspan={11} class="empty">광고가 없습니다.</td></tr>}
    </table></div>
  </AdminLayout>
);

export const AdEdit = ({ c, ad }: { c: PageCtx; ad: Partial<Ad> }) => (
  <AdminLayout c={c}>
    <div class="admin-top"><h1>{ad.id ? "광고 수정" : "새 광고"}</h1><a class="btn btn-sm" href="/admin/ads">← 목록</a></div>
    <div class="grid-2">
      <div class="panel">
        <form method="post" enctype="multipart/form-data" class="form" action={ad.id ? `/admin/ads/${ad.id}` : "/admin/ads/new"}><Csrf c={c} />
          <div class="form-grid">
            <div class="field full"><label>제목 *</label><input class="input" name="title" value={ad.title || ""} required /></div>
            <div class="field full"><label>설명</label><input class="input" name="subtitle" value={ad.subtitle || ""} /></div>
            <div class="field full"><label>클릭하면 이동할 주소</label><input class="input" name="link_url" value={ad.link_url || ""} placeholder="https://… 또는 /pricing" /></div>
            <div class="field"><label>위치</label><select class="input" name="placement">
              <option value="banner" selected={ad.placement === "banner"}>배너 (결과창 오른쪽 위, 약 600×170)</option>
              <option value="popup" selected={ad.placement === "popup"}>팝업 (결과창 왼쪽 아래, 약 680×400)</option></select></div>
            <div class="field"><label>보여줄 제품</label><select class="input" name="apps">
              {Object.entries(APPS_LABEL).map(([k, n]) => <option value={k} selected={ad.apps === k}>{k === "all" ? "전체 제품" : n}</option>)}</select></div>
            <div class="field"><label>버튼 글자</label><input class="input" name="button_text" value={ad.button_text || ""} /></div>
            <div class="field"><label>배경색 (이미지 없을 때)</label><input class="input" type="color" name="bg_color" value={ad.bg_color || "#ff6f91"} style="height:46px" /></div>
            <div class="field"><label>시작일</label><input class="input" type="date" name="start_at" value={ad.start_at ? fmt(ad.start_at, "date") : ""} /></div>
            <div class="field"><label>종료일</label><input class="input" type="date" name="end_at" value={ad.end_at ? fmt(ad.end_at, "date") : ""} /></div>
            <div class="field"><label>노출 비중 (클수록 자주)</label><input class="input" type="number" min="1" name="weight" value={String(ad.weight || 1)} /></div>
            <div class="field"><label>&nbsp;</label><label class="check"><input type="checkbox" name="active" checked={!!ad.active} /> 광고 노출하기</label></div>
            <div class="field full"><label>이미지 파일 올리기 (png·jpg·gif·webp, 1MB 이하)</label><input class="input" type="file" name="image_file" accept="image/*" /></div>
            <div class="field full"><label>또는 이미지 주소</label><input class="input" name="image_url" placeholder="https://…" value={ad.image && ad.image.startsWith("http") ? ad.image : ""} />
              {ad.image && <label class="check"><input type="checkbox" name="remove_image" /> 이미지 지우기 (배경색+글자 광고로)</label>}</div>
          </div>
          <button class="btn btn-pink">저장</button>
        </form>
      </div>
      <div class="panel"><h2>미리보기</h2>
        {ad.image ? <img src={adImageUrl(ad.image)} style="border-radius:12px;width:100%" />
          : <div class="ad-preview" style={`background:${ad.bg_color || "#ff6f91"}`}><img src="/img/mochi.svg" style="width:70px" /><div><b>{ad.title || "광고 제목"}</b>{ad.subtitle}</div></div>}
        <p class="small muted">이미지가 없으면 PC 프로그램에서 배경색 + 모찌 캐릭터 + 제목/설명으로 자동으로 그려집니다.</p>
        {ad.id && <dl class="dl"><dt>노출</dt><dd>{ad.views}회</dd><dt>클릭</dt><dd>{ad.clicks}회 (CTR {ctrOf(ad as Ad)}%)</dd></dl>}
      </div>
    </div>
  </AdminLayout>
);

export const Products = ({ c, items }: { c: PageCtx; items: Product[] }) => (
  <AdminLayout c={c}>
    <div class="admin-top"><h1>제품 관리</h1></div>
    <p class="muted">새 버전을 배포할 때 <b>버전</b>과 <b>다운로드 주소</b>를 바꾸세요. 출시 예정 제품은 '출시 예정'으로 두면 사이트에 표시만 됩니다.</p>
    {[...items, null].map((p) => (
      <div class="panel">
        <h2>{p ? p.name : "+ 새 제품 추가"} {p && <Badge kind="gray">다운로드 {p.downloads}회</Badge>}</h2>
        <form method="post" action="/admin/products" class="form"><Csrf c={c} /><input type="hidden" name="id" value={p ? String(p.id) : ""} />
          <div class="form-grid">
            <div class="field"><label>코드 (영문)</label><input class="input" name="slug" value={p?.slug || ""} placeholder="pdf" required /></div>
            <div class="field"><label>이름</label><input class="input" name="name" value={p?.name || ""} placeholder="모찌PDF" required /></div>
            <div class="field full"><label>한 줄 소개</label><input class="input" name="tagline" value={p?.tagline || ""} /></div>
            <div class="field full"><label>설명</label><input class="input" name="description" value={p?.description || ""} /></div>
            <div class="field"><label>버전</label><input class="input" name="version" value={p?.version || "1.0.0"} /></div>
            <div class="field"><label>상태</label><select class="input" name="status">
              <option value="released" selected={p?.status === "released"}>출시</option><option value="coming" selected={!p || p.status === "coming"}>출시 예정</option></select></div>
            <div class="field full"><label>다운로드 주소 (설치파일 링크)</label><input class="input" name="download_url" value={p?.download_url || ""} placeholder="https://github.com/…/releases/download/v1.0.0/MochiCapture_Setup_1.0.0.exe" /></div>
            <div class="field"><label>대표 색</label><input class="input" type="color" name="color" value={p?.color || "#ff6f91"} style="height:46px" /></div>
            <div class="field"><label>표시 순서</label><input class="input" type="number" name="sort" value={String(p?.sort ?? 9)} /></div>
          </div>
          <button class="btn btn-sm btn-dark">저장</button>
        </form>
      </div>
    ))}
  </AdminLayout>
);

export const Settings = ({ c, toss }: { c: PageCtx; toss: boolean }) => (
  <AdminLayout c={c}>
    <div class="admin-top"><h1>설정</h1></div>
    <div class="grid-2">
      <div class="panel"><h2>구독 상품</h2>
        <form method="post" action="/admin/settings" class="form"><Csrf c={c} />
          <div class="field"><label>구독 상품 이름</label><input class="input" name="plan_name" value={c.s.plan_name} /></div>
          <div class="field"><label>월 요금 (원)</label><input class="input" type="number" name="price" value={c.s.price} /><span class="small muted">바꾸면 다음 결제부터 적용됩니다.</span></div>
          <div class="field"><label>계정당 PC 최대 대수</label><input class="input" type="number" min="1" name="device_limit" value={c.s.device_limit} /></div>
          <div class="field"><label>팝업 광고 빈도 (무료 사용자: N번 캡처마다 1번)</label><input class="input" type="number" min="1" name="popup_every" value={c.s.popup_every} /></div>
          <button class="btn btn-pink">저장</button>
        </form>
      </div>
      <div class="panel"><h2>결제 연동 상태</h2>
        {toss ? <p><Badge kind="mint">연결됨</Badge> 토스페이먼츠 자동결제 사용 중</p> : <>
          <p><Badge kind="peach">테스트 모드</Badge> 실제 결제가 되지 않습니다.</p>
          <p class="small muted">토스페이먼츠 개발자센터에서 키 발급 → Cloudflare 대시보드 → Workers → mozzilab → 설정 → 변수 및 비밀(Variables and Secrets)에 <code>TOSS_CLIENT_KEY</code>, <code>TOSS_SECRET_KEY</code> 를 '비밀(Secret)'로 추가하세요.</p></>}
        <h2 style="margin-top:22px">정기결제 자동 실행</h2>
        <p class="small muted">Cloudflare Cron 이 매일 오전 9시(한국 시간)에 자동으로 실행합니다. 바로 실행하려면 대시보드의 [정기결제 지금 실행]을 누르세요.</p>
      </div>
    </div>
  </AdminLayout>
);
