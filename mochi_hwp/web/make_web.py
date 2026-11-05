"""모찌한글 웹 버전 마무리: 빌드된 편집 화면(dist-web)에 모찌LAB. 막대와 홈 화면 아이콘 설정을 붙인다.
사용법: python make_web.py <dist-web 폴더>
(편집 화면은 vite build --base /hwp/ 로 미리 만들어 둔다. 홈페이지의 /hwp/ 주소에 올라간다)"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

HEAD = """    <link rel="manifest" href="/hwp/manifest.webmanifest">
    <link rel="apple-touch-icon" href="/hwp/icons/icon-192.png">
    <meta name="theme-color" content="#3f7cf4">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-title" content="모찌한글">
    <meta name="description" content="한글(HWP · HWPX) 문서를 핸드폰과 브라우저에서 무료로 열고 고치기. 문서는 서버로 올라가지 않아요.">
"""


def main(dist):
    for name in ("mozzi-web.js", "manifest.webmanifest"):
        shutil.copy(os.path.join(HERE, name), os.path.join(dist, name))
    p = os.path.join(dist, "index.html")
    with open(p, encoding="utf-8") as f:
        html = f.read()
    if "mozzi-web.js" not in html:
        assert html.count("</head>") == 1, "index.html 의 </head> 를 찾지 못했어요"
        html = html.replace("</head>", HEAD + '    <script src="/hwp/mozzi-web.js" defer></script>\n  </head>')
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print("모찌한글 웹 준비 완료:", dist)


if __name__ == "__main__":
    main(sys.argv[1])
