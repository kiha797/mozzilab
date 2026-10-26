
// ---------------------------------------------------------------- 모찌한글(웹 화면)용 연결
// 화면은 overlay.js 가 그린다. 여기서는 상태(snapshot)와 동작(action)만 제공하고,
// tick() 을 0.5초마다 불러서 서버 응답 · 로그인 확인 · 자동 업데이트를 처리한다.

/// 작업(저장)이 끝날 때: 무료 사용자에게 가끔 팝업 광고
pub fn job_done() {
    with(|s| {
        if !s.show_ads() {
            return;
        }
        let n = s.cfg["job_count"].as_u64().unwrap_or(0) + 1;
        s.cfg["job_count"] = json!(n);
        s.save();
        let every = s.ads["popup_every"].as_u64().unwrap_or(1).max(1);
        if n % every == 0 {
            let list = s.ads["popup"].as_array().cloned().unwrap_or_default();
            if !list.is_empty() {
                s.popup = Some(list[(n as usize / every as usize) % list.len()].clone());
                if let Some(id) = s.popup.as_ref().and_then(|p| p["id"].as_i64()) {
                    spawn(&s.tx, move || {
                        let _ = request("POST", &format!("/api/ads/{id}/view"), None, None);
                        Msg::Me(0, Value::Null)
                    });
                }
            }
        }
    });
}

/// 화면이 1초마다 알려 주는 '저장 안 된 문서가 있나' (저장됨으로 바뀌면 저장 완료로 본다)
pub fn note_dirty(dirty: bool) {
    let saved = with(|s| {
        let saved = s.was_dirty && !dirty;
        s.was_dirty = dirty;
        saved
    });
    if saved {
        job_done();
    }
}

/// 0.5초마다: 서버 응답 처리 · 로그인 확인 · 자동 업데이트. 설치를 시작해서 끝내야 하면 true
pub fn tick() -> bool {
    with(|s| {
        while let Ok(m) = s.rx.try_recv() {
            s.handle(m);
        }
        let started = *s.started.get_or_insert_with(|| {
            s.refresh_needed = true;
            Instant::now()
        });
        if std::mem::take(&mut s.refresh_needed) {
            s.refresh();
        }
        if !s.auto_checked && started.elapsed() > Duration::from_secs(8) {
            s.auto_checked = true;
            s.check_update(false);
        }
        if s.auto_checked && s.last_update_check.elapsed() > UPDATE_EVERY {
            s.check_update(false);
        }
        let dirty = s.was_dirty;
        if let Some(u) = &mut s.update {
            if u.ready.is_some() {
                if dirty {
                    u.install_at = None;
                } else if u.install_at.is_none() {
                    u.install_at = Some(Instant::now() + Duration::from_secs(5));
                }
            }
        }
        if s.update.as_ref().and_then(|u| u.install_at).is_some_and(|t| Instant::now() >= t) {
            s.install();
        }
        if s.last_sync.elapsed() > Duration::from_secs(3 * 3600) {
            s.last_sync = Instant::now();
            s.refresh();
        }
        if s.login.open {
            if let Some(t) = s.login.next_poll {
                if Instant::now() >= t {
                    s.login.next_poll = None;
                    let code = s.login.device_code.clone();
                    spawn(&s.tx, move || {
                        let (c, v) = request("POST", "/api/device/poll", Some(json!({"device_code": code})), None);
                        Msg::DevicePoll(c, v)
                    });
                }
            }
        }
        s.quit
    })
}

/// 화면(overlay.js)에 보여 줄 지금 상태
pub fn snapshot() -> Value {
    with(|s| {
        let banners = s.ads["banner"].as_array().cloned().unwrap_or_default();
        if s.banner_at.elapsed() > Duration::from_secs(45) && !banners.is_empty() {
            s.banner = (s.banner + 1) % banners.len();
            s.banner_at = Instant::now();
        }
        let banner = banners.get(s.banner % banners.len().max(1)).cloned();
        let acc = &s.cfg["account"];
        json!({
            "app": APP_NAME, "version": VERSION,
            "logged_in": s.logged_in(), "name": s.name(), "email": acc["email"], "premium": s.premium(),
            "show_ads": s.show_ads(), "banner": banner, "pricing_url": s.ads["pricing_url"],
            "mypage_url": acc["mypage_url"],
            "login": if s.login.open { json!({"info": s.login.info, "user_code": s.login.user_code,
                                                 "failed": s.login.failed, "verify_url": s.login.verify_url}) } else { Value::Null },
            "popup": s.popup.clone(),
            "update": s.update.as_ref().map(|u| json!({
                "tag": u.tag, "downloading": u.downloading, "progress": u.progress, "ready": u.ready.is_some(),
                "install_in": u.install_at.map(|t| t.saturating_duration_since(Instant::now()).as_secs() + 1),
                "error": u.error, "dirty": s.was_dirty })),
            "info": s.info_msg.clone(),
        })
    })
}

/// 화면에서 누른 버튼 처리
pub fn action(name: &str, arg: &Value) {
    match name {
        "dirty" => note_dirty(arg.as_bool().unwrap_or(false)),
        "job_done" => job_done(),
        "open" => open_url(arg.as_str().unwrap_or("/")),
        _ => with(|s| match name {
            "login" => s.start_login(),
            "login_close" => s.login.open = false,
            "logout" => s.logout(),
            "refresh" => s.refresh(),
            "check_update" => s.check_update(true),
            "install_now" => s.install(),
            "update_close" => s.update = None,
            "popup_close" => s.popup = None,
            "info_close" => s.info_msg = None,
            "ad_click" => {
                let url = arg["click_url"].as_str().or(s.ads["pricing_url"].as_str()).unwrap_or("/pricing").to_string();
                open_url(&url);
                s.popup = None;
            }
            _ => {}
        }),
    }
}
