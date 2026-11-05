// 모찌한글 웹 (mozzilab.labelpos.com/hwp/): 편집 화면 위에 모찌LAB. 막대를 붙인다
// - 로그인은 홈페이지 로그인을 그대로 쓴다 (같은 주소라 따로 로그인할 필요 없음)
// - 무료 회원에게만 광고 한 줄, 모찌 플러스 회원은 광고 없음
// - 문서는 서버로 올라가지 않고 이 기기(브라우저) 안에서만 열고 고친다
(function () {
  if (window.__mozziWeb) return;
  window.__mozziWeb = true;
  const ACCENT = '#ff6f91';
  const BAR = 34;
  const css = `
  html { height: 100%; }
  body { padding-top: ${BAR}px !important; box-sizing: border-box; height: 100%; }
  #mz-web { position: fixed; top: 0; left: 0; right: 0; height: ${BAR}px; z-index: 2147483000; display: flex; align-items: center;
    gap: 8px; padding: 0 10px; background: #fff7f9; border-bottom: 1px solid #f3d6de; box-sizing: border-box;
    font: 13px 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; color: #3b2f2f; }
  #mz-web a { color: inherit; text-decoration: none; }
  #mz-web .mz-logo { display: flex; align-items: center; gap: 6px; font-weight: bold; white-space: nowrap; }
  #mz-web .mz-logo img { width: 20px; height: 20px; border-radius: 5px; }
  #mz-web .mz-ad { flex: 1; min-width: 0; display: none; align-items: center; gap: 6px; height: 24px; padding: 0 10px 0 4px;
    border-radius: 12px; color: #fff; cursor: pointer; overflow: hidden; white-space: nowrap; }
  #mz-web .mz-ad b { background: rgba(0,0,0,.25); border-radius: 4px; padding: 0 4px; font-size: 10px; }
  #mz-web .mz-ad span { overflow: hidden; text-overflow: ellipsis; }
  #mz-web .mz-gap { flex: 1; }
  #mz-web .mz-btn { height: 24px; line-height: 22px; padding: 0 10px; border-radius: 6px; border: 1.3px solid ${ACCENT};
    color: ${ACCENT}; background: #fff; font-weight: bold; white-space: nowrap; font-size: 12px; }
  #mz-web .mz-pc { border-color: #d9cdd1; color: #5b4a50; font-weight: normal; }
  @media (max-width: 640px) { #mz-web .mz-pc, #mz-web .mz-logo span { display: none; } }
  `;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  function mount() {
    if (!document.body) return setTimeout(mount, 50);
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
    const bar = document.createElement('div');
    bar.id = 'mz-web';
    bar.innerHTML = `<a class="mz-logo" href="/products/hwp" title="모찌LAB. 홈페이지"><img src="/hwp/icons/icon-192.png" alt=""><span>모찌한글 웹</span></a>
      <div class="mz-ad"></div><div class="mz-gap"></div>
      <a class="mz-btn mz-pc" href="/products/hwp">PC 버전 받기</a>
      <a class="mz-btn mz-acc" href="/login?next=/hwp/">로그인</a>`;
    document.body.prepend(bar);
    window.dispatchEvent(new Event('resize'));
    load(bar);
  }

  async function load(bar) {
    let me = {};
    try { me = await (await fetch('/hwp-me', { credentials: 'same-origin' })).json(); } catch (e) { /* 연결 안 됨: 무료로 표시 */ }
    const acc = bar.querySelector('.mz-acc');
    if (me.logged_in) {
      acc.textContent = (me.premium ? '⭐ ' : '') + me.name + ' 님';
      acc.href = '/mypage';
    }
    if (me.premium) return;
    let ads = {};
    try { ads = await (await fetch('/api/ads?app=hwp')).json(); } catch (e) { /* 광고 없이 */ }
    const list = (ads.banner && ads.banner.length) ? ads.banner
      : [{ title: '광고 없이 쾌적하게, 모찌 플러스', bg_color: ACCENT, click_url: '/pricing' }];
    const ad = bar.querySelector('.mz-ad');
    let i = 0;
    const show = () => {
      const a = list[i++ % list.length];
      ad.style.background = a.bg_color || ACCENT;
      ad.innerHTML = `<b>AD</b><span>${esc(a.title)}</span>`;
      ad.title = a.subtitle || '';
      ad.onclick = () => window.open(a.click_url || '/pricing', '_blank');
      ad.style.display = 'flex';
    };
    show();
    if (list.length > 1) setInterval(show, 45000);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
