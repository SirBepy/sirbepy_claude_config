// Test for reachability.mjs: a superseded memory (frontmatter `superseded_by:`) is reported as
// `superseded`, never `orphan-file`; a true orphan still is one; a live indexed file is neither.
//   node test_reachability.cjs
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const script = path.join(__dirname, "reachability.mjs");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "reach-test-"));

const fm = (lines) => `---\n${lines.join("\n")}\n---\nbody\n`;
const write = (name, text) => fs.writeFileSync(path.join(dir, name), text);

let failed = 0;
const check = (name, ok, detail) => {
  console.log(`${ok ? "ok  " : "FAIL"} ${name}${ok ? "" : ": " + detail}`);
  if (!ok) failed++;
};

try {
  write("MEMORY.md", "- [Live](live.md) - the one indexed file\n");
  write("live.md", fm(["name: live", "description: indexed"]));
  write("old.md", fm(["name: old", "description: replaced", "superseded_by: live"]));
  write("orphan.md", fm(["name: orphan", "description: no index line"]));
  // recall.py treats an empty value as absent, so this file is a live orphan, not superseded.
  write("empty.md", fm(["name: empty", "description: blank key", "superseded_by:"]));

  const r = spawnSync(process.execPath, [script, dir], { encoding: "utf8", timeout: 60000 });
  if (r.status !== 0) {
    check("script exits 0", false, `status ${r.status}: ${r.stderr}`);
  } else {
    // A line naming a count opens a list; the 4-space-indented lines after it are its file entries.
    const lists = [];
    let cur = null;
    for (const line of r.stdout.split(/\r?\n/)) {
      if (/^ {4}\S/.test(line)) {
        if (cur) cur.files.push(path.basename(line.trim()));
      } else if (/^\s*(orphan-file|superseded)\b/.test(line)) {
        cur = { label: line.trim().split(":")[0].split(" ")[0], count: Number(/(\d+)\s*$/.exec(line)?.[1]), files: [] };
        lists.push(cur);
      } else {
        cur = null;
      }
    }
    const orphanLists = lists.filter((l) => l.label === "orphan-file");
    const supLists = lists.filter((l) => l.label === "superseded");

    check("three readings each print an orphan-file list", orphanLists.length === 3, String(orphanLists.length));
    check("authoritative orphan-file is exactly orphan.md + empty.md",
      orphanLists[0] && orphanLists[0].files.slice().sort().join(",") === "empty.md,orphan.md",
      JSON.stringify(orphanLists[0]));
    check("superseded file is not an orphan-file in any reading",
      orphanLists.every((l) => !l.files.includes("old.md")), JSON.stringify(orphanLists));
    check("live indexed file is not an orphan-file",
      orphanLists.every((l) => !l.files.includes("live.md")), JSON.stringify(orphanLists));
    check("superseded section has count 1 and lists exactly old.md",
      supLists.length === 1 && supLists[0].count === 1 && supLists[0].files.join(",") === "old.md",
      JSON.stringify(supLists));
  }
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}

check("scratch dir removed", !fs.existsSync(dir), dir);
process.exit(failed ? 1 : 0);
