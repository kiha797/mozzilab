// 모찌한글: 편집 화면 위에 모찌LAB. 로그인 · 광고 · 업데이트 알림을 그린다.
// (상태와 동작은 Rust 쪽 mozzi.rs 가 맡고, 여기서는 1초마다 상태를 받아 화면만 바꾼다)
(function () {
  if (window.__mozziOverlay) return;
  window.__mozziOverlay = true;
  const ACCENT = '#ff6f91';
  const invoke = (cmd, args) => {
    const t = window.__TAURI__;
    if (!t || !t.core) return Promise.resolve(null);
    return t.core.invoke(cmd, args || {}).catch(() => null);
  };
  const act = (name, arg) => invoke('mozzi_action', { name, arg: arg === undefined ? null : arg });

  const css = `
  #mozzi-bar { position: fixed; top: 4px; right: 10px; z-index: 2147483000; display: flex; gap: 8px; align-items: center;
    font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; font-size: 12px; }
  #mozzi-bar .mz-ad { display: flex; align-items: center; gap: 6px; height: 24px; max-width: 320px; padding: 0 12px 0 6px;
    border-radius: 12px; color: #fff; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  #mozzi-bar .mz-ad b { background: rgba(0,0,0,.25); border-radius: 4px; padding: 0 4px; font-size: 10px; }
  #mozzi-bar .mz-ad span { overflow: hidden; text-overflow: ellipsis; }
  #mozzi-bar .mz-login { height: 24px; padding: 0 12px; border-radius: 6px; border: 1.3px solid ${ACCENT}; background: #fff;
    color: ${ACCENT}; font-weight: bold; cursor: pointer; font-size: 12px; }
  #mozzi-bar .mz-login:hover { background: #fff0f4; }
  #mozzi-menu { position: fixed; top: 32px; right: 10px; z-index: 2147483001; background: #fff; border: 1px solid #e3dcd8;
    border-radius: 10px; box-shadow: 0 10px 30px rgba(59,47,47,.15); padding: 6px; min-width: 210px; display: none;
    font-family: 'Malgun Gothic', sans-serif; font-size: 13px; color: #3b2f2f; }
  #mozzi-menu .mz-sub { color: #8a7f82; padding: 6px 10px; font-size: 12px; }
  #mozzi-menu button { display: block; width: 100%; text-align: left; border: none; background: none; padding: 8px 10px;
    border-radius: 6px; cursor: pointer; font-size: 13px; color: #3b2f2f; }
  #mozzi-menu button:hover { background: #fff0f4; color: ${ACCENT}; }
  .mz-card { position: fixed; z-index: 2147483002; background: #fff; border-radius: 14px; box-shadow: 0 16px 40px rgba(59,47,47,.25);
    font-family: 'Malgun Gothic', sans-serif; color: #3b2f2f; }
  .mz-card button.mz-primary { width: 100%; height: 34px; border: none; border-radius: 8px; color: #fff; background: ${ACCENT};
    font-weight: bold; cursor: pointer; font-size: 13px; margin-top: 10px; }
  .mz-card button.mz-ghost { border: 1px solid #e3dcd8; background: #fff; border-radius: 8px; padding: 6px 12px; cursor: pointer; font-size: 12px; }
  .mz-x { position: absolute; top: 8px; right: 10px; border: none; background: none; cursor: pointer; color: #999; font-size: 13px; }
  #mozzi-modal-bg { position: fixed; inset: 0; background: rgba(40,30,32,.45); z-index: 2147483003; display: none; }
  #mozzi-login { left: 50%; top: 50%; transform: translate(-50%, -50%); width: 380px; padding: 24px; text-align: center; z-index: 2147483004; display: none; }
  #mozzi-login .mz-code { font-size: 30px; font-weight: bold; letter-spacing: 4px; margin: 12px 0 4px; font-family: Consolas, monospace; }
  #mozzi-popup { left: 16px; bottom: 36px; width: 300px; padding: 14px; display: none; }
  #mozzi-update { right: 16px; bottom: 36px; width: 300px; padding: 14px; display: none; border: 1.5px solid ${ACCENT}; }
  #mozzi-update .mz-bar { height: 8px; background: #f3e9ec; border-radius: 4px; overflow: hidden; margin-top: 8px; }
  #mozzi-update .mz-bar i { display: block; height: 100%; background: ${ACCENT}; width: 0; }
  #mozzi-info { left: 50%; bottom: 40px; transform: translateX(-50%); padding: 12px 18px; display: none; }
  `;

  function el(tag, attrs, html) {
    const e = document.createElement(tag);
    Object.assign(e, attrs || {});
    if (html !== undefined) e.innerHTML = html;
    return e;
  }
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  function mount() {
    if (!document.body) return setTimeout(mount, 100);
    document.head.appendChild(el('style', {}, css));
    const bar = el('div', { id: 'mozzi-bar' });
    const ad = el('div', { className: 'mz-ad', title: '' });
    const login = el('button', { className: 'mz-login' }, '로그인');
    bar.append(ad, login);
    const menu = el('div', { id: 'mozzi-menu' });
    const bg = el('div', { id: 'mozzi-modal-bg' });
    const loginBox = el('div', { id: 'mozzi-login', className: 'mz-card' });
    const popup = el('div', { id: 'mozzi-popup', className: 'mz-card' });
    const update = el('div', { id: 'mozzi-update', className: 'mz-card' });
    const info = el('div', { id: 'mozzi-info', className: 'mz-card' });
    document.body.append(bar, menu, bg, loginBox, popup, update, info);

    let st = null;
    let adNow = null;
    ad.onclick = () => adNow && act('ad_click', adNow);
    login.onclick = () => {
      if (!st) return;
      if (!st.logged_in) return act('login');
      menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
    };
    document.addEventListener('mousedown', (e) => {
      if (!menu.contains(e.target) && e.target !== login) menu.style.display = 'none';
    }, true);

    function renderMenu() {
      menu.innerHTML = '';
      menu.append(el('div', { className: 'mz-sub' }, esc(st.email || '') + '<br>' + (st.premium ? '모찌 플러스 이용 중 · 광고 없음' : '무료 이용 중')));
      const item = (label, fn) => { const b = el('button', {}, label); b.onclick = () => { menu.style.display = 'none'; fn(); }; menu.append(b); };
      item('마이페이지', () => act('open', st.mypage_url || '/mypage'));
      if (!st.premium) item('광고 없이 쓰기 (모찌 플러스)', () => act('open', st.pricing_url || '/pricing'));
      item('구독 상태 새로고침', () => act('refresh'));
      item(`업데이트 확인 (지금 v${esc(st.version)})`, () => act('check_update'));
      item('로그아웃', () => act('logout'));
    }

    function render() {
      if (!st) return;
      // 오른쪽 위: 광고 + 로그인
      adNow = st.show_ads ? st.banner : null;
      ad.style.display = adNow ? 'flex' : 'none';
      if (adNow) {
        ad.style.background = adNow.bg_color || ACCENT;
        ad.innerHTML = `<b>AD</b><span>${esc(adNow.title)}</span>`;
        ad.title = (adNow.subtitle || '') + '\n누르면 자세히 볼 수 있어요';
      }
      login.textContent = st.logged_in ? `${st.premium ? '[플러스] ' : ''}${st.name} 님` : '로그인';
      if (st.logged_in) renderMenu();
      // 로그인 창
      const l = st.login;
      bg.style.display = loginBox.style.display = l ? 'block' : 'none';
      if (l) {
        loginBox.innerHTML = `<button class="mz-x">닫기</button>
          <div style="font-size:18px;font-weight:bold;color:${ACCENT}">모찌LAB. 계정 연결</div>
          <div style="margin-top:10px;white-space:pre-line;font-size:13px;color:#5b4a50">${esc(l.info)}</div>
          ${l.user_code && !l.failed ? `<div class="mz-code">${esc(l.user_code)}</div><div style="font-size:12px;color:#999">승인을 기다리는 중… (10분 안에 완료해 주세요)</div>` : ''}
          <div style="margin-top:14px;display:flex;gap:8px;justify-content:center">
            ${l.verify_url ? '<button class="mz-ghost" data-a="reopen">브라우저 다시 열기</button>' : ''}
            ${l.failed ? '<button class="mz-ghost" data-a="retry">다시 시도</button>' : ''}
          </div>`;
        loginBox.querySelector('.mz-x').onclick = () => act('login_close');
        const re = loginBox.querySelector('[data-a=reopen]'); if (re) re.onclick = () => act('open', l.verify_url);
        const rt = loginBox.querySelector('[data-a=retry]'); if (rt) rt.onclick = () => act('login');
      }
      // 저장 후 팝업 광고
      const p = st.popup;
      popup.style.display = p ? 'block' : 'none';
      if (p) {
        const color = p.bg_color || ACCENT;
        popup.innerHTML = `<button class="mz-x">닫기</button>
          <span style="background:${color};color:#fff;font-size:10px;border-radius:4px;padding:1px 5px">AD</span>
          <div style="font-size:15px;font-weight:bold;margin-top:6px">${esc(p.title)}</div>
          <div style="font-size:12px;color:#666;margin-top:4px">${esc(p.subtitle)}</div>
          <button class="mz-primary" style="background:${color}">${esc(p.button_text || '자세히 알아보기')}</button>`;
        popup.querySelector('.mz-x').onclick = () => act('popup_close');
        popup.querySelector('.mz-primary').onclick = () => act('ad_click', p);
      }
      // 자동 업데이트 알림 (작업을 막지 않음)
      const u = st.update;
      const showU = u && (u.downloading || u.ready || u.error);
      update.style.display = showU ? 'block' : 'none';
      if (showU) {
        let body = '';
        if (u.error) body = `<div style="color:#e5484d;font-size:12px;margin-top:6px">${esc(u.error)}</div><button class="mz-ghost" data-a="close" style="margin-top:8px">닫기</button>`;
        else if (u.downloading) body = `<div style="font-size:12px;color:#666;margin-top:6px">새 버전을 내려받는 중이에요. 계속 작업하셔도 돼요.</div><div class="mz-bar"><i style="width:${Math.round((u.progress || 0) * 100)}%"></i></div>`;
        else if (u.install_in) body = `<div style="font-size:12px;color:#666;margin-top:6px">${u.install_in}초 뒤 업데이트를 설치하고 다시 켜요.</div><button class="mz-primary" data-a="now">지금 설치</button>`;
        else if (u.dirty) body = `<div style="font-size:12px;color:#666;margin-top:6px">저장하지 않은 문서가 있어요.<br>저장하면 자동으로 업데이트돼요.</div><button class="mz-ghost" data-a="now" style="margin-top:8px">저장하지 않고 지금 설치</button>`;
        update.innerHTML = `<div style="font-weight:bold">${esc(st.app)} 새 버전 v${esc(u.tag)}</div>${body}`;
        const now = update.querySelector('[data-a=now]'); if (now) now.onclick = () => act('install_now');
        const cl = update.querySelector('[data-a=close]'); if (cl) cl.onclick = () => act('update_close');
      }
      // 짧은 안내
      info.style.display = st.info ? 'block' : 'none';
      if (st.info) {
        info.innerHTML = `<span style="font-size:13px">${esc(st.info)}</span> <button class="mz-ghost" style="margin-left:10px">확인</button>`;
        info.querySelector('button').onclick = () => act('info_close');
      }
    }

    async function loop() {
      const ds = window.__documentState;
      let dirty = false;
      try { dirty = !!(ds && typeof ds.isDirty === 'function' && ds.isDirty()); } catch (e) { dirty = false; }
      act('dirty', dirty);
      const s = await invoke('mozzi_state');
      if (s) { st = s; render(); }
      setTimeout(loop, 1000);
    }
    loop();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
