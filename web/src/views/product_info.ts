// 제품 상세 페이지(자세히)에 보이는 화면 캡처 · 설명
// 화면 캡처 파일은 web/public/img/shots/ 에 있다 (제품 화면을 실제로 띄워서 찍은 것)

export type Shot = { src: string; title: string; desc: string };
export type Feature = { icon: string; title: string; desc: string };
export type ProductInfo = {
  headline: string;
  intro: string;
  shots: Shot[];
  features: Feature[];
  steps: { title: string; desc: string }[];
  formats: string[];
  similar?: string;
};

export const PRODUCT_INFO: Record<string, ProductInfo> = {
  capture: {
    headline: "클릭 한 번으로 쏙! 알캡처처럼 쉬운 화면 캡처",
    intro: "원하는 부분을 찍고, 결과창에서 바로 표시·글자·모자이크까지. 보고서나 업무 메신저에 붙이기 좋은 캡처를 가장 빠르게 만들어요.",
    similar: "알캡처 · 픽픽 대체",
    shots: [
      { src: "/img/shots/capture-editor.png", title: "결과창에서 바로 편집", desc: "캡처하자마자 도형 · 화살표 · 글자 · 형광펜 · 모자이크로 표시하고, 오른쪽 '최근 캡처 목록'에서 다시 열 수 있어요." },
      { src: "/img/shots/capture-launcher.png", title: "작은 실행창", desc: "직접지정 · 창 · 단위영역 · 전체화면 · 스크롤 · 크기지정, 6가지 캡처를 한 줄에서 골라요. 숫자키 1~6 으로도 돼요." },
      { src: "/img/shots/capture-settings.png", title: "꼼꼼한 환경설정", desc: "자동 저장 · 자동 복사 · 단축키 · 저장 폴더 · 파일 이름 규칙까지 내 방식대로 맞출 수 있어요." },
    ],
    features: [
      { icon: "🖱️", title: "6가지 캡처", desc: "직접지정, 창, 단위영역, 전체화면, 스크롤(긴 웹페이지), 크기지정(같은 위치 반복)" },
      { icon: "✏️", title: "바로 편집", desc: "사각형 · 원 · 화살표 · 펜 · 형광펜 · 글자 · 모자이크 · 자르기" },
      { icon: "⌨️", title: "단축키", desc: "캡처 방식마다 원하는 단축키를 지정 (Print Screen 등)" },
      { icon: "📋", title: "자동 복사 · 저장", desc: "찍자마자 클립보드에 복사되고, 정한 폴더에 자동 저장" },
      { icon: "🗂️", title: "최근 캡처 100장", desc: "지난 캡처를 목록에서 다시 열어 편집 · 저장 · 인쇄" },
      { icon: "🔔", title: "트레이에서 대기", desc: "작업 표시줄 아이콘을 누르면 언제든 바로 캡처" },
    ],
    steps: [
      { title: "설치하고 실행", desc: "설치가 끝나면 화면 위쪽에 작은 '실행창'이 떠요. 작업 표시줄 오른쪽에 모찌 아이콘도 생겨요." },
      { title: "캡처 방식 고르기", desc: "실행창에서 '직접지정'을 누르고 원하는 부분을 드래그하세요. 단축키로도 바로 찍을 수 있어요." },
      { title: "표시하고 저장", desc: "결과창에서 화살표 · 글자를 넣고 [저장] 또는 [복사]. 메신저에 Ctrl+V 로 붙여 넣으면 끝!" },
    ],
    formats: ["PNG", "JPG", "BMP", "GIF", "인쇄"],
  },
  pdf: {
    headline: "PDF 합치기 · 나누기 · 변환을 말랑하게",
    intro: "여러 PDF를 하나로 합치거나 필요한 쪽만 뽑고, 사진을 PDF로 바꾸고, 메일로 보내기 좋게 용량까지 줄여요. 인터넷에 올리지 않고 내 PC에서 처리해서 안전해요.",
    similar: "알PDF · 이지PDF 대체",
    shots: [
      { src: "/img/shots/pdf-home.png", title: "한눈에 보이는 도구", desc: "합치기 · 나누기 · 페이지 편집 · 이미지↔PDF · 용량 줄이기 · 암호를 카드로 골라요." },
      { src: "/img/shots/pdf-merge.png", title: "끌어다 놓고 합치기", desc: "PDF 파일을 끌어다 놓고 순서만 정하면 한 파일로 합쳐져요." },
      { src: "/img/shots/pdf-pages.png", title: "쪽 단위 편집", desc: "미리보기를 보면서 쪽을 회전 · 삭제하고 끌어서 순서를 바꿔요." },
    ],
    features: [
      { icon: "📚", title: "합치기", desc: "여러 PDF를 원하는 순서로 하나의 파일로" },
      { icon: "✂️", title: "나누기", desc: "한 쪽씩, N쪽마다, 원하는 범위(1-3, 5)만 골라서" },
      { icon: "🔄", title: "페이지 편집", desc: "회전 · 삭제 · 순서 바꾸기를 미리보기로" },
      { icon: "🖼️", title: "이미지 ↔ PDF", desc: "사진 · 스캔 이미지를 PDF로, PDF를 PNG · JPG로" },
      { icon: "🪶", title: "용량 줄이기", desc: "스캔 PDF 22MB → 1MB 처럼 메일 첨부하기 좋게" },
      { icon: "🔒", title: "암호", desc: "AES-256 암호 걸기 · 풀기" },
    ],
    steps: [
      { title: "도구 고르기", desc: "첫 화면에서 하고 싶은 일(예: 합치기)을 누르세요." },
      { title: "파일 넣기", desc: "PDF 파일을 창에 끌어다 놓거나 [파일 추가]를 누르세요. PDF 파일에서 오른쪽 클릭 → '모찌PDF로 열기'도 돼요." },
      { title: "실행", desc: "아래 분홍 버튼을 누르면 끝. 다 되면 오른쪽 아래에 알림이 떠요." },
    ],
    formats: ["PDF", "PNG", "JPG", "BMP", "GIF", "WEBP", "TIFF"],
  },
  zip: {
    headline: "꾹 눌러 담는 압축 프로그램",
    intro: "파일에서 오른쪽 클릭 한 번으로 압축하고 풀어요. 다른 PC에서 만든 ZIP의 한글 이름이 깨져 있으면 자동으로 고쳐 줘요.",
    similar: "알집 · 반디집 대체",
    shots: [
      { src: "/img/shots/zip-home.png", title: "간단한 첫 화면", desc: "압축하기 · 압축 파일 열기 · 바로 풀기, 세 가지만 기억하면 돼요." },
      { src: "/img/shots/zip-view.png", title: "압축 파일 안 미리 보기", desc: "풀기 전에 안에 든 파일과 폴더를 보고, 필요한 것만 골라 풀 수 있어요." },
      { src: "/img/shots/zip-compress.png", title: "압축하기", desc: "파일 · 폴더를 끌어다 놓고 형식(ZIP · 7Z) · 압축 정도 · 암호를 정해요." },
    ],
    features: [
      { icon: "🗜️", title: "압축", desc: "ZIP · 7Z, 압축 정도 선택" },
      { icon: "📂", title: "풀기", desc: "ZIP · 7Z · TAR(.tar.gz 등)" },
      { icon: "🔐", title: "암호", desc: "AES-256 암호, 7Z 는 파일 이름까지 숨김" },
      { icon: "🇰🇷", title: "한글 깨짐 복구", desc: "윈도우 ZIP 의 깨진 한글 파일 이름을 자동으로 바로잡아요" },
      { icon: "🖱️", title: "오른쪽 클릭 메뉴", desc: "'여기에 풀기' · '압축하기'를 탐색기에서 바로" },
      { icon: "🛡️", title: "안전하게", desc: "압축 파일 밖으로 파일을 쓰는 위험한 경로를 막아요" },
    ],
    steps: [
      { title: "압축하려면", desc: "파일이나 폴더에서 오른쪽 클릭 → '모찌압축으로 압축하기'." },
      { title: "풀려면", desc: "ZIP · 7Z 파일에서 오른쪽 클릭 → '모찌압축으로 여기에 풀기'." },
      { title: "골라서 풀려면", desc: "압축 파일을 두 번 눌러 열고, 필요한 파일만 골라 [고른 것만 풀기]." },
    ],
    formats: ["ZIP", "7Z", "TAR", "TAR.GZ", "TAR.BZ2", "TAR.XZ"],
  },
  photo: {
    headline: "포토샵을 그대로, 모찌포토",
    intro: "포토샵과 거의 같은 화면 · 메뉴 · 단축키라서 쓰던 그대로 바로 쓸 수 있어요. PSD 파일을 레이어 그대로 열고 저장하고, 무료로 써요.",
    similar: "포토샵 · 포토피아 대체",
    shots: [
      { src: "/img/shots/photo-editor.png", title: "포토샵과 같은 작업 화면", desc: "왼쪽 도구 상자, 위쪽 옵션 막대, 오른쪽 색상 · 속성 · 레이어 패널까지 익숙한 그대로예요." },
      { src: "/img/shots/photo-menu.png", title: "필터 · 조정 메뉴", desc: "흐림 · 선명하게 · 왜곡 · 노이즈 같은 필터와 레벨 · 곡선 · 색조/채도 같은 보정이 메뉴에 그대로 있어요." },
      { src: "/img/shots/photo-start.png", title: "시작 화면", desc: "새 문서 · 열기 · 최근 파일. PSD · PNG · JPG 파일을 끌어다 놓아도 열려요." },
    ],
    features: [
      { icon: "🧱", title: "레이어 · 마스크", desc: "레이어 그룹, 레이어 마스크, 조정 레이어, 혼합 모드" },
      { icon: "✨", title: "레이어 스타일", desc: "그림자 · 획 · 외부 광선 · 경사와 엠보스 등" },
      { icon: "🪄", title: "선택 도구", desc: "사각형 · 올가미 · 빠른 선택 · 마술봉 · 색상 범위" },
      { icon: "🖌️", title: "브러시 · 복구", desc: "브러시 사전 설정, 복제 도장, 복구 브러시, 지우개" },
      { icon: "🔤", title: "문자 · 펜", desc: "나중에 다시 고칠 수 있는 문자 레이어, 펜 도구로 패스" },
      { icon: "📁", title: "PSD 호환", desc: "포토샵 PSD · PSB 를 레이어 그대로 열고 저장" },
      { icon: "⌨️", title: "포토샵 단축키", desc: "V · M · B · Ctrl+J · Ctrl+T 등 손에 익은 그대로" },
      { icon: "💻", title: "내 PC 에서", desc: "인터넷 없이도 동작, 파일이 밖으로 나가지 않아요" },
    ],
    steps: [
      { title: "파일 열기", desc: "PSD · JPG · PNG 파일에서 오른쪽 클릭 → '모찌포토로 편집', 또는 [파일 → 열기]." },
      { title: "편집", desc: "포토샵처럼 레이어를 만들고 도구로 편집하세요. 메뉴 이름도 포토샵과 같아요." },
      { title: "저장 · 내보내기", desc: "PSD 로 저장하면 레이어가 그대로 남고, [파일 → 내보내기]로 PNG · JPG 를 만들어요." },
    ],
    formats: ["PSD", "PSB", "PNG", "JPG", "WEBP", "TIFF", "GIF", "BMP", "TGA", "ICO", "XCF", "KRA", "ORA"],
  },
  vector: {
    headline: "일러스트레이터를 그대로, 모찌벡터",
    intro: "일러스트레이터와 거의 같은 화면 · 도구 · 단축키로 로고 · 아이콘 · 포스터 · 명함을 만들어요. SVG · PDF · AI 파일을 열고 저장할 수 있어요.",
    similar: "일러스트레이터 · 벡터피아 대체",
    shots: [
      { src: "/img/shots/vector-editor.png", title: "일러스트레이터와 같은 작업 화면", desc: "왼쪽 도구 상자, 위쪽 컨트롤 막대, 오른쪽 속성 · 레이어 · 라이브러리 패널이 익숙한 그대로예요." },
      { src: "/img/shots/vector-menu.png", title: "개체 · 효과 메뉴", desc: "패스파인더, 정렬, 변형, 패턴, 효과 메뉴가 일러스트레이터처럼 들어 있어요." },
      { src: "/img/shots/vector-start.png", title: "시작 화면", desc: "레터 · A4 · 웹 · 휴대폰 · 엽서 · SNS 크기로 바로 새 문서를 만들어요." },
    ],
    features: [
      { icon: "🖋️", title: "펜 · 곡선", desc: "펜 · 곡률 · 연필 · 브러시 도구, 기준점 편집" },
      { icon: "🔷", title: "도형", desc: "사각형 · 원 · 다각형 · 별 · 선, 모서리 둥글리기" },
      { icon: "🧩", title: "패스파인더", desc: "합치기 · 빼기 · 교차 · 나누기" },
      { icon: "🔤", title: "문자", desc: "글상자 · 패스 위의 문자 · 윤곽선 만들기" },
      { icon: "🎨", title: "색 · 그레이디언트", desc: "견본 · 그레이디언트 · 패턴 · 투명도" },
      { icon: "📐", title: "대지 · 정렬", desc: "여러 대지, 안내선, 격자, 정렬 · 분포" },
      { icon: "📁", title: "파일 호환", desc: "SVG · PDF · AI(PDF 호환) · EPS 열기, SVG · PDF 저장" },
      { icon: "⌨️", title: "일러스트 단축키", desc: "V · A · P · M · L · Ctrl+G 등 손에 익은 그대로" },
    ],
    steps: [
      { title: "새 문서", desc: "시작 화면에서 크기(A4 · 웹 · 명함 등)를 고르세요. SVG 파일에서 오른쪽 클릭 → '모찌벡터로 열기'도 돼요." },
      { title: "그리기", desc: "도형 · 펜 · 문자 도구로 그리고, 오른쪽 속성 패널에서 색과 선을 바꿔요." },
      { title: "저장 · 내보내기", desc: "작업 파일로 저장하고, SVG · PDF · PNG 로 내보내 인쇄소 · 웹에 써요." },
    ],
    formats: ["SVG", "PDF", "AI", "EPS", "PNG", "JPG"],
  },
};
