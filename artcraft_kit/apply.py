"""아트크래프트(PhotoCraft · VectorCraft) 원본 소스를 모찌포토 · 모찌벡터로 바꾸는 스크립트

사용법:  python apply.py photo <원본 폴더> <버전>
         python apply.py vector <원본 폴더> <버전>

하는 일
 1. 화면에 보이는 'PhotoCraft' / 'VectorCraft' 이름을 '모찌포토' / '모찌벡터' 로 바꾼다
 2. 프로그램 아이콘을 모찌 아이콘으로 바꾼다
 3. 설정 폴더 · 앱 ID 를 바꿔서 PC 에 설치된 원본 PhotoCraft 와 섞이지 않게 한다
 4. 모찌랩 로그인 · 광고 · 자동 업데이트(mozzi.rs)를 붙인다
 5. 정보 창에 원본 출처(MIT/Apache-2.0)를 표시한다

원본 코드가 바뀌어서 고칠 곳을 못 찾으면 바로 멈추고 알려 준다 (조용히 틀리지 않도록)."""
import os
import re
import shutil
import sys

KIT = os.path.dirname(os.path.abspath(__file__))

APPS = {
    "photo": {"upstream": "PhotoCraft", "lower": "photocraft", "name": "모찌포토", "app_id": "MochiPhoto",
              "slug": "photo", "rdns": "ai.storyteller.photocraft"},
    "vector": {"upstream": "VectorCraft", "lower": "vectorcraft", "name": "모찌벡터", "app_id": "MochiVector",
               "slug": "vector", "rdns": "ai.storyteller.vectorcraft"},
}


BYTE_STR = re.compile(r'(?<![A-Za-z0-9_])br?#*"')   # b"..." · br"..." (GitHub" 같은 글자는 아님)


class ApplyError(Exception):
    pass


def read(p):
    # newline="" : 파일의 줄바꿈을 그대로 둔다. CRLF 파일이면 LF 로 맞춰서 비교한다.
    with open(p, encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")


def write(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def edit(root, rel, old, new, count=1):
    """정확히 일치하는 부분을 바꾼다. 못 찾으면 멈춘다."""
    p = os.path.join(root, rel)
    s = read(p)
    n = s.count(old)
    if n == 0:
        raise ApplyError(f"{rel}: 바꿀 부분을 찾지 못했어요:\n{old[:200]}")
    if count and n != count:
        raise ApplyError(f"{rel}: {n}곳이 일치해요 (예상 {count}곳):\n{old[:200]}")
    write(p, s.replace(old, new))


def is_test_file(path):
    b = os.path.basename(path)
    return b.endswith("_tests.rs") or b == "tests.rs" or f"{os.sep}tests{os.sep}" in path


def rename_everywhere(root, app):
    """원본 이름을 모찌 이름으로 (코드의 문자열 · 번역표). 테스트 파일은 건드리지 않는다."""
    up, name = app["upstream"], app["name"]
    # 한글 조사가 바로 붙는 경우(PhotoCraft에서)도 바꾸려고 영문자 경계만 본다
    word = re.compile(rf"(?<![A-Za-z0-9_]){up}(?![A-Za-z0-9_])")
    changed = 0
    for top in ("crates", "apps"):
        for d, dirs, files in os.walk(os.path.join(root, top)):
            dirs[:] = [x for x in dirs if x not in ("tests", "target", "corpus", "fixtures")]
            for fn in files:
                if not fn.endswith((".rs", ".tsv")):
                    continue
                p = os.path.join(d, fn)
                if fn.endswith(".rs") and is_test_file(p):
                    continue
                s = read(p)
                # 바이트 문자열(b"...")에는 한글을 넣을 수 없으니 그런 줄은 그대로 둔다
                t = "".join(ln if BYTE_STR.search(ln) else word.sub(name, ln) for ln in s.splitlines(keepends=True))
                if t != s:
                    write(p, t)
                    changed += 1
    return changed


def render_icons(root, app, svg_text):
    """모찌 아이콘(SVG)을 원본 아이콘 파일 자리에 PNG · ICO 로 넣는다"""
    from PIL import Image
    try:
        import cairosvg  # noqa: F401
        have_cairo = True
    except ImportError:
        have_cairo = False
    icon_dir = os.path.join(root, "assets", "app-icon")
    master = os.path.join(KIT, "icons", f"{app['slug']}-1024.png")
    if not os.path.exists(master):
        if not have_cairo:
            raise ApplyError(f"아이콘 그림이 없어요: {master}")
        import cairosvg
        cairosvg.svg2png(bytestring=svg_text.encode(), write_to=master, output_width=1024, output_height=1024)
    big = Image.open(master).convert("RGBA")
    lower, rdns = app["lower"], app["rdns"]
    for p in (os.path.join(icon_dir, f"{lower}-1024.png"),):
        if os.path.exists(p):
            big.save(p)
    hic = os.path.join(icon_dir, "hicolor")
    if os.path.isdir(hic):
        for size_dir in os.listdir(hic):
            m = re.match(r"(\d+)x\d+$", size_dir)
            png = os.path.join(hic, size_dir, "apps", f"{rdns}.png")
            if m and os.path.exists(png):
                n = int(m.group(1))
                big.resize((n, n), Image.LANCZOS).save(png)
            svg = os.path.join(hic, size_dir, "apps", f"{rdns}.svg")
            if os.path.exists(svg):
                write(svg, svg_text)
    for fn in os.listdir(icon_dir):
        p = os.path.join(icon_dir, fn)
        if fn.endswith(".svg"):
            write(p, svg_text)
        elif fn.endswith(".ico"):
            big.save(p, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        elif fn.endswith(".png") and fn != os.path.basename(master):
            im = Image.open(p)
            big.resize(im.size, Image.LANCZOS).save(p)
    # 원본(ArtCraft) 로고는 상표라 쓰지 않는다
    brand = os.path.join(root, "docs", "brand")
    if os.path.isdir(brand):
        shutil.rmtree(brand)


def install_mozzi(root, app, version, ui_crate):
    src = read(os.path.join(KIT, "mozzi.rs"))
    for k, v in (("@@SLUG@@", app["slug"]), ("@@APP_ID@@", app["app_id"]), ("@@NAME@@", app["name"]),
                 ("@@VERSION@@", version)):
        src = src.replace(k, v)
    write(os.path.join(root, ui_crate, "src", "mozzi.rs"), src)
    toml = os.path.join(root, ui_crate, "Cargo.toml")
    s = read(toml)
    if "ureq" not in s:
        s = s.rstrip() + ('\n\n# 모찌랩 로그인 · 광고 · 자동 업데이트 (mozzi.rs)\n'
                          '[target.\'cfg(not(target_arch = "wasm32"))\'.dependencies.ureq]\n'
                          'version = "3.4"\ndefault-features = false\nfeatures = ["rustls", "platform-verifier"]\n')
        write(toml, s)


ATTRIBUTION = ("이 프로그램은 오픈소스 {up}(ArtCraft 팀 · MIT/Apache-2.0)를 바탕으로 모찌LAB.이 만들었습니다. "
               "원본 소스: https://github.com/storytold/{lower}")


def apply_photo(root, version):
    app = APPS["photo"]
    n = rename_everywhere(root, app)
    print(f"  이름 바꾼 파일: {n}개")
    ui = "crates/ui-egui"
    install_mozzi(root, app, version, ui)
    edit(root, f"{ui}/src/lib.rs", "mod brand;\n", "mod brand;\npub mod mozzi;\n")
    edit(root, f"{ui}/src/lib.rs", "            panels::title_bar(self, ui);\n",
         "            panels::title_bar(self, ui);\n"
         "            crate::mozzi::show(ui.ctx());\n"
         "            crate::mozzi::note_dirty(self.session.documents().iter().any(|d| d.is_dirty()));\n")
    edit(root, f"{ui}/src/panels.rs", "                    let mut ws = app.ui.workspace.clone();\n",
         "                    crate::mozzi::title_controls(ui);\n                    let mut ws = app.ui.workspace.clone();\n")
    # 도움말 · 시작 화면 링크: 원본 커뮤니티 대신 모찌랩
    links = f"{ui}/src/links.rs"
    edit(root, links, 'pub const DISCORD: &str = "https://discord.gg/artcraft";',
         'pub const DISCORD: &str = "https://mozzilab.labelpos.com";')
    edit(root, links, 'pub const ARTCRAFT_WEBSITE: &str = "https://getartcraft.com";',
         'pub const ARTCRAFT_WEBSITE: &str = "https://github.com/storytold/photocraft";')
    edit(root, links, 'pub const APP_PAGE: &str = "https://getartcraft.com/apps/photocraft";',
         'pub const APP_PAGE: &str = "https://mozzilab.labelpos.com/products/photo";')
    edit(root, links, 'pub const ISSUES: &str = "https://github.com/storytold/photocraft/issues";',
         'pub const ISSUES: &str = "https://mozzilab.labelpos.com/support";')
    edit(root, links, 'tl!("Join us on Discord")', '"모찌LAB. 홈페이지"')
    edit(root, links, '(tl!("ArtCraft"), ARTCRAFT_WEBSITE)', '("원본 PhotoCraft 소스", ARTCRAFT_WEBSITE)')
    edit(root, "crates/engine/src/shell_commands.rs", '"Join the ArtCraft Discord…"', '"모찌LAB. 홈페이지"')
    edit(root, "crates/engine/src/shell_commands.rs", '"ArtCraft Website"', '"원본 PhotoCraft 소스 (GitHub)"')
    # 정보 창: 모찌 버전 + 원본 출처
    edit(root, f"{ui}/src/dialogs.rs",
         'ui.label(crate::i18n::fmt(tl!("Version {version}"), &[("version", &photocraft_engine::build_info::long_version())]));',
         'ui.label(format!("버전 {}  (PhotoCraft {})", crate::mozzi::VERSION, photocraft_engine::build_info::VERSION));\n'
         f'            ui.weak("{ATTRIBUTION.format(up="PhotoCraft", lower="photocraft")}");')
    # 원본 업데이트 확인은 끄고, 모찌랩 업데이트(mozzi.rs)를 쓴다
    edit(root, "apps/photocraft/src/updates.rs", "let result = fetch(LATEST, Duration::from_secs(15));",
         "let result: CheckResult = if LATEST.is_empty() { fetch(LATEST, Duration::from_secs(15)) } else { Ok(None) };")
    # 설정 폴더 · 앱 ID: PC 에 깔린 원본 PhotoCraft 와 따로 쓰기
    edit(root, "apps/photocraft/src/app_dirs.rs", 'join("Photocraft")', 'join("MochiPhoto")', count=0)
    edit(root, "apps/photocraft/src/main.rs", 'const APP_ID: &str = "ai.storyteller.photocraft";',
         'const APP_ID: &str = "com.mozzilab.MochiPhoto";')
    edit(root, "apps/photocraft/build.rs", '.set("CompanyName", "Learning Machines LLC")', '.set("CompanyName", "MozziLab")')
    edit(root, "apps/photocraft/build.rs", '.set("LegalCopyright", "Copyright (c) the 모찌포토 authors. MIT OR Apache-2.0.")',
         '.set("LegalCopyright", "Based on PhotoCraft (c) the PhotoCraft authors, MIT OR Apache-2.0. MozziLab.")')
    render_icons(root, app, read(os.path.join(KIT, "icons", "photo.svg")))


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in APPS:
        print(__doc__)
        return 2
    which, root, version = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3]
    print(f"{APPS[which]['name']} 만들기: {root} (v{version})")
    try:
        {"photo": apply_photo, "vector": apply_vector}[which](root, version)
    except ApplyError as e:
        print("\n[오류] " + str(e))
        print("원본 코드가 바뀐 것 같아요. artcraft_kit/upstream.json 의 커밋을 확인하세요.")
        return 1
    print("완료!")
    return 0


def replace_in_tree(root, dirs, old, new):
    """여러 파일에 걸친 같은 글자를 모두 바꾼다 (테스트 파일 제외). 한 곳도 없으면 멈춘다."""
    hits = 0
    for top in dirs:
        for d, sub, files in os.walk(os.path.join(root, top)):
            sub[:] = [x for x in sub if x not in ("tests", "target")]
            for fn in files:
                p = os.path.join(d, fn)
                if not fn.endswith((".rs", ".tsv")) or (fn.endswith(".rs") and (is_test_file(p) or fn.startswith("tests_"))):
                    continue
                t = read(p)
                if old in t:
                    hits += t.count(old)
                    write(p, t.replace(old, new))
    if not hits:
        raise ApplyError(f"바꿀 글자를 찾지 못했어요: {old}")


def apply_vector(root, version):
    app = APPS["vector"]
    n = rename_everywhere(root, app)
    print(f"  이름 바꾼 파일: {n}개")
    ui = "crates/ui-egui"
    install_mozzi(root, app, version, ui)
    edit(root, f"{ui}/src/lib.rs", "\nmod brand;\n", "\nmod brand;\npub mod mozzi;\n")
    edit(root, f"{ui}/src/lib.rs", "            chrome::app_bar(self, ui);\n",
         "            chrome::app_bar(self, ui);\n"
         "            crate::mozzi::show(ui.ctx());\n"
         "            crate::mozzi::note_dirty(self.session.documents().iter().any(|d| d.is_dirty()));\n")
    # 제목 표시줄 오른쪽: 디스코드 버튼 자리에 모찌랩 [로그인] · 광고
    edit(root, f"{ui}/src/chrome.rs",
         "            if discord {\n                ui.add_space(10.0);\n                crate::community::discord_button(app, ui, false);\n            }\n",
         "            let _ = discord;\n            ui.add_space(10.0);\n            crate::mozzi::title_controls(ui);\n")
    # 링크: 원본 커뮤니티 대신 모찌랩
    help_rs = "crates/engine/src/cmd/help.rs"
    edit(root, help_rs, 'pub const DISCORD_URL: &str = "https://discord.gg/artcraft";',
         'pub const DISCORD_URL: &str = "https://mozzilab.labelpos.com";')
    edit(root, help_rs, 'pub const WEBSITE_URL: &str = "https://getartcraft.com";',
         'pub const WEBSITE_URL: &str = "https://github.com/storytold/vectorcraft";')
    edit(root, help_rs, '    format!("{WEBSITE_URL}/apps/{APP_ID}")', '    "https://mozzilab.labelpos.com/products/vector".to_string()')
    for a, b in (('"Join Our Discord"', '"모찌LAB. 홈페이지"'), ('"ArtCraft Website"', '"원본 VectorCraft 소스 (GitHub)"'),
                 ('"모찌벡터 on getartcraft.com"', '"모찌벡터 소개 페이지"'), ('tl!("ArtCraft website")', '"원본 VectorCraft 소스"'),
                 ('tl!("Join our Discord")', '"모찌LAB. 홈페이지"')):
        replace_in_tree(root, ["crates"], a, b)
    com = f"{ui}/src/community.rs"
    edit(root, com, "const DISCORD: Color32 = Color32::from_rgb(0x58, 0x65, 0xF2);",
         "const DISCORD: Color32 = Color32::from_rgb(0xff, 0x6f, 0x91);")
    edit(root, com, 'tl!("Join the ArtCraft community on Discord (discord.gg/artcraft)")', '"모찌LAB. 홈페이지 (mozzilab.labelpos.com)"')
    # 정보 창: 모찌 버전 + 원본 출처
    about = f"{ui}/src/dialogs/about.rs"
    edit(root, about, '&[("version", env!("CARGO_PKG_VERSION"))],',
         '&[("version", &format!("{} (VectorCraft {})", crate::mozzi::VERSION, env!("CARGO_PKG_VERSION")))],')
    edit(root, about, '"Part of ArtCraft. MIT OR Apache-2.0. Fonts: Source Sans 3, Inter, JetBrains Mono (OFL). Icons: Lucide (ISC) + 모찌벡터."',
         f'"{ATTRIBUTION.format(up="VectorCraft", lower="vectorcraft")} 글꼴: Source Sans 3, Inter, JetBrains Mono (OFL). 아이콘: Lucide (ISC)."')
    # 설정 폴더 · 앱 ID: PC 에 깔린 원본 VectorCraft 와 따로 쓰기
    replace_in_tree(root, ["apps/vectorcraft/src"], 'prefs_path_for("모찌벡터", "vectorcraft")', 'prefs_path_for("MochiVector", "mochivector")')
    edit(root, "apps/vectorcraft/src/profile.rs", '("모찌벡터", "vectorcraft")', '("MochiVector", "mochivector")')
    edit(root, "apps/vectorcraft/src/main.rs", '.with_app_id("ai.storyteller.vectorcraft")', '.with_app_id("com.mozzilab.MochiVector")')
    edit(root, "apps/vectorcraft/build.rs", '.set("CompanyName", "Learning Machines LLC")', '.set("CompanyName", "MozziLab")')
    edit(root, "apps/vectorcraft/build.rs", '.set("LegalCopyright", "Copyright (c) the 모찌벡터 authors. MIT OR Apache-2.0.")',
         '.set("LegalCopyright", "Based on VectorCraft (c) the VectorCraft authors, MIT OR Apache-2.0. MozziLab.")')
    render_icons(root, app, read(os.path.join(KIT, "icons", "vector.svg")))


if __name__ == "__main__":
    sys.exit(main())
