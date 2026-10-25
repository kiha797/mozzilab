// 모찌랩 웹사이트를 Cloudflare 에 한 번에 배포하는 스크립트
// 1) Cloudflare 로그인  2) 데이터베이스(D1) 만들기  3) 배포  4) 비밀 설정(관리자 계정 등)
import { execSync, spawnSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { randomBytes } from "node:crypto";
import readline from "node:readline/promises";

const TOML = new URL("../../wrangler.toml", import.meta.url);
const DB_NAME = "mozzilab-db";
const isWin = process.platform === "win32";
const npx = isWin ? "npx.cmd" : "npx";

function run(args, opts = {}) {
  return spawnSync(npx, ["wrangler", ...args, "--config", "../wrangler.toml"], { encoding: "utf8", shell: isWin, ...opts });
}
function step(n, msg) { console.log(`\n[${n}/4] ${msg}`); }

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

// 1. 로그인
step(1, "Cloudflare 로그인 확인");
let who = run(["whoami"]);
if (!/You are logged in|associated with the email/i.test(who.stdout + who.stderr)) {
  console.log("  브라우저가 열리면 Cloudflare 에 로그인하고 [Allow] 를 눌러 주세요.");
  const r = run(["login"], { stdio: "inherit" });
  if (r.status !== 0) { console.log("  로그인에 실패했습니다. 다시 실행해 주세요."); process.exit(1); }
}
console.log("  로그인 OK");

// 2. 데이터베이스
step(2, `데이터베이스(${DB_NAME}) 준비`);
let toml = readFileSync(TOML, "utf8");
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
if (!UUID.test(toml.match(/database_id\s*=\s*"([^"]*)"/)?.[1] || "")) {
  let id = null;
  const list = run(["d1", "list", "--json"]);
  try { id = JSON.parse(list.stdout).find((d) => d.name === DB_NAME)?.uuid || null; } catch { /* 목록 없음 */ }
  if (!id) {
    const created = run(["d1", "create", DB_NAME]);
    id = (created.stdout + created.stderr).match(UUID)?.[0] || null;
    if (!id) { console.log(created.stdout + created.stderr); console.log("  데이터베이스를 만들지 못했습니다."); process.exit(1); }
    console.log("  새 데이터베이스를 만들었습니다.");
  } else console.log("  기존 데이터베이스를 사용합니다.");
  toml = toml.replace(/database_id\s*=\s*"[^"]*"/, `database_id = "${id}"`);
  writeFileSync(TOML, toml);
  console.log(`  wrangler.toml 에 저장: ${id}`);
} else console.log("  이미 설정되어 있습니다.");

// 3. 배포
step(3, "배포 (1~2분)");
const dep = run(["deploy"], { stdio: ["inherit", "pipe", "pipe"] });
const out = dep.stdout + dep.stderr;
console.log(out.split("\n").filter((l) => /https?:\/\/|Uploaded|Deployed|error|Error|✘/i.test(l)).join("\n"));
if (dep.status !== 0) {
  if (/custom domain|zone|labelpos/i.test(out))
    console.log("\n  ⚠ mozzilab.labelpos.com 연결에 실패했습니다. labelpos.com 이 이 Cloudflare 계정에 '활성' 상태로 등록되어 있는지 확인하세요.");
  process.exit(1);
}

// 4. 비밀 설정
step(4, "비밀 설정 (관리자 계정)");
let existing = [];
try { existing = JSON.parse(run(["secret", "list", "--format", "json"]).stdout).map((s) => s.name); } catch { /* 없음 */ }
async function put(name, value) {
  const r = run(["secret", "put", name], { input: value });
  console.log(r.status === 0 ? `  ${name} 저장 OK` : `  ${name} 저장 실패:\n${r.stderr}`);
}
if (!existing.includes("SECRET_KEY")) await put("SECRET_KEY", randomBytes(32).toString("hex"));
if (!existing.includes("ADMIN_EMAIL") || !existing.includes("ADMIN_PASSWORD")) {
  const email = (await rl.question("  관리자로 쓸 이메일: ")).trim();
  const pw = (await rl.question("  관리자 비밀번호 (8자 이상): ")).trim();
  if (email && pw.length >= 8) { await put("ADMIN_EMAIL", email); await put("ADMIN_PASSWORD", pw); }
  else console.log("  건너뜀 (나중에 다시 실행하면 물어봅니다)");
} else console.log("  이미 설정되어 있습니다.");
rl.close();

console.log(`
==========================================
  배포 완료! 🍡
  사이트      https://mozzilab.labelpos.com
  관리자      https://mozzilab.labelpos.com/admin
  (도메인 보안 인증서 발급에 처음 몇 분 걸릴 수 있어요.
   그동안은 위에 나온 *.workers.dev 주소로 먼저 접속해 보세요)
==========================================`);
