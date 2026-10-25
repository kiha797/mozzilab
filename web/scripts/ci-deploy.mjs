// GitHub Actions 에서 실행되는 자동 배포 스크립트
// 1) 데이터베이스(D1) 찾기/만들기  2) Cloudflare 에 배포  3) 비밀값(관리자 계정 등) 넣기
import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { randomBytes } from "node:crypto";

const DB_NAME = "mozzilab-db";
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const env = process.env;

function wrangler(args, input) {
  const r = spawnSync("npx", ["wrangler", ...args], { encoding: "utf8", input });
  return { ok: r.status === 0, out: (r.stdout || "") + (r.stderr || "") };
}
function fail(msg, detail = "") {
  console.log(`::error::${msg}`);
  if (detail) console.log(detail);
  process.exit(1);
}

if (!env.CLOUDFLARE_API_TOKEN || !env.CLOUDFLARE_ACCOUNT_ID) {
  console.log("::warning::GitHub 저장소 Secrets 에 CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID 가 아직 없어 배포를 건너뜁니다.");
  process.exit(0);
}

// 1. 데이터베이스
console.log("① 데이터베이스 준비");
let id = null;
const list = wrangler(["d1", "list", "--json"]);
if (!list.ok) fail("Cloudflare 에 연결하지 못했습니다. API 토큰 권한(D1 Edit)과 계정 ID 를 확인하세요.", list.out);
try { id = JSON.parse(list.out.slice(list.out.indexOf("["))).find((d) => d.name === DB_NAME)?.uuid || null; } catch { /* 빈 목록 */ }
if (!id) {
  const created = wrangler(["d1", "create", DB_NAME]);
  id = created.out.match(UUID)?.[0] || null;
  if (!id) fail("데이터베이스를 만들지 못했습니다.", created.out);
  console.log(`   새로 만듦: ${id}`);
} else console.log(`   기존 것 사용: ${id}`);
const tomlPath = new URL("../wrangler.toml", import.meta.url);
writeFileSync(tomlPath, readFileSync(tomlPath, "utf8").replace(/database_id\s*=\s*"[^"]*"/, `database_id = "${id}"`));

// 2. 배포
console.log("② 배포");
const dep = wrangler(["deploy"]);
console.log(dep.out.split("\n").filter((l) => /https?:\/\/|Uploaded|Deployed|Current Version|✘|ERROR|error/i.test(l)).join("\n"));
if (!dep.ok) {
  const hint = /zone|custom domain|labelpos/i.test(dep.out)
    ? "mozzilab.labelpos.com 연결 실패 - labelpos.com 이 이 Cloudflare 계정에 '활성'으로 등록되어 있는지, 토큰에 Zone 권한이 있는지 확인하세요."
    : "배포에 실패했습니다. 아래 기록을 확인하세요.";
  fail(hint, dep.out);
}

// 3. 비밀값
console.log("③ 비밀값 설정");
let existing = [];
const sl = wrangler(["secret", "list", "--format", "json"]);
try { existing = JSON.parse(sl.out.slice(sl.out.indexOf("["))).map((s) => s.name); } catch { /* 없음 */ }
function put(name, value) {
  const r = wrangler(["secret", "put", name], value);
  console.log(r.ok ? `   ${name} ✔` : `   ${name} 실패`);
  if (!r.ok) console.log(r.out);
}
if (!existing.includes("SECRET_KEY")) put("SECRET_KEY", env.MOZZI_SECRET_KEY || randomBytes(32).toString("hex"));
for (const name of ["ADMIN_EMAIL", "ADMIN_PASSWORD", "TOSS_CLIENT_KEY", "TOSS_SECRET_KEY",
  "NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "KAKAO_CLIENT_ID", "KAKAO_CLIENT_SECRET", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]) {
  if (env[name]) put(name, env[name]);
}
console.log("\n배포 완료 🍡  https://mozzilab.labelpos.com  (관리자: /admin)");
