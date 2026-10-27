// Test for extract-names.mjs: a name's diacritics are stripped and both cases of đ map to `dj`
// (NFD does not decompose Đ/đ, so a capital Đ used to survive and the whole name was dropped).
//   node test_extract_names.cjs
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const script = path.join(__dirname, "extract-names.mjs");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "extract-names-test-"));
const ideas = path.join(dir, "ideas");
fs.mkdirSync(ideas);
const out = path.join(dir, "out.txt");

let failed = 0;
const check = (name, ok, detail) => {
  console.log(`${ok ? "ok  " : "FAIL"} ${name}${ok ? "" : ": " + detail}`);
  if (!ok) failed++;
};

try {
  fs.writeFileSync(
    path.join(ideas, "a.md"),
    ["# Round", "Đakovo | city | capital D-stroke", "đurđevac | city | lowercase d-stroke", "Šibenik | city | caron", "Ab | too short | x"].join("\n") + "\n",
  );
  const r = spawnSync(process.execPath, [script, ideas, out], { encoding: "utf8" });
  check("script exits 0", r.status === 0, r.stderr);
  const names = fs.existsSync(out) ? fs.readFileSync(out, "utf8").split("\n").filter(Boolean) : [];
  check("capital Đakovo yields djakovo", names.includes("djakovo"), JSON.stringify(names));
  check("lowercase đurđevac yields djurdjevac", names.includes("djurdjevac"), JSON.stringify(names));
  check("Šibenik still yields sibenik", names.includes("sibenik"), JSON.stringify(names));
  check("too-short name is dropped", !names.includes("ab"), JSON.stringify(names));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}

process.exit(failed ? 1 : 0);
