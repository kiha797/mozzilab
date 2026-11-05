// 홈페이지 배포 직전에 실행 (wrangler.toml 의 [build]):
// 다운로드 페이지(GitHub Releases)에서 모찌한글 웹 버전(MochiHwp_Web.zip)을 받아 web/public/hwp 에 푼다.
// - 받을 버전은 web/hwp-version.txt (설치파일 배포가 끝나면 자동으로 바뀜)
// - 받지 못하면 배포를 멈춰서, 홈페이지에 /hwp/ 가 빠진 채로 올라가지 않게 한다
// - 내 PC 에서 시험할 때 건너뛰려면 MOZZI_SKIP_HWP=1
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { inflateRawSync } from "node:zlib";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(WEB, "public", "hwp");
const REPO = "kiha797/mozzilab";

if (process.env.MOZZI_SKIP_HWP === "1") {
  console.log("모찌한글 웹: 건너뜀 (MOZZI_SKIP_HWP=1)");
  process.exit(0);
}
const version = readFileSync(join(WEB, "hwp-version.txt"), "utf8").trim();
const url = `https://github.com/${REPO}/releases/download/v${version}/MochiHwp_Web.zip`;
console.log(`모찌한글 웹 v${version} 받는 중: ${url}`);

let zip;
for (let i = 1; i <= 4; i++) {
  try {
    const r = await fetch(url, { redirect: "follow" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    zip = Buffer.from(await r.arrayBuffer());
    break;
  } catch (e) {
    console.log(`  ${i}번째 실패: ${e.message}`);
    if (i === 4) { console.error("모찌한글 웹을 받지 못해 배포를 멈춥니다."); process.exit(1); }
    await new Promise((ok) => setTimeout(ok, 2000 * i));
  }
}

// ZIP 풀기 (압축 안 함 · deflate 두 가지만 쓰임)
let eocd = zip.length - 22;
while (eocd >= 0 && zip.readUInt32LE(eocd) !== 0x06054b50) eocd--;
if (eocd < 0) { console.error("ZIP 파일이 올바르지 않아요."); process.exit(1); }
const count = zip.readUInt16LE(eocd + 10);
let p = zip.readUInt32LE(eocd + 16);
rmSync(OUT, { recursive: true, force: true });
let files = 0;
for (let n = 0; n < count; n++) {
  const method = zip.readUInt16LE(p + 10);
  const csize = zip.readUInt32LE(p + 20);
  const nlen = zip.readUInt16LE(p + 28), xlen = zip.readUInt16LE(p + 30), clen = zip.readUInt16LE(p + 32);
  const local = zip.readUInt32LE(p + 42);
  const name = zip.toString("utf8", p + 46, p + 46 + nlen);
  p += 46 + nlen + xlen + clen;
  if (name.endsWith("/")) continue;
  const target = normalize(join(OUT, name));
  if (!target.startsWith(OUT)) continue; // 폴더 밖으로 나가는 이름은 무시
  const start = local + 30 + zip.readUInt16LE(local + 26) + zip.readUInt16LE(local + 28);
  const raw = zip.subarray(start, start + csize);
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, method === 8 ? inflateRawSync(raw) : raw);
  files++;
}
if (!existsSync(join(OUT, "index.html"))) { console.error("웹 버전에 index.html 이 없어요."); process.exit(1); }
console.log(`모찌한글 웹 v${version} 준비 완료: 파일 ${files}개 → web/public/hwp`);
