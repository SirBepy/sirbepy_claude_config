// Test for reachability.mjs: a superseded memory (frontmatter `superseded_by:`) is reported as
// `superseded`, never `orphan-file`; a true orphan still is one; a live indexed file is neither.
// A file in any demotion-tier subfolder (rest/, cold/) is counted on the `demoted files` line, never
// orphan-file, and a link into one resolves; an index over the 8192-byte core cap is flagged OVER.
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
  // A link into a demotion tier is legal (index paths are relative to the memory dir) and must resolve, not dangle.
  write("MEMORY.md", "- [Live](live.md) - the one indexed file\n- [Demoted](rest/demoted.md) - linked into rest/\n");
  write("live.md", fm(["name: live", "description: indexed"]));
  write("old.md", fm(["name: old", "description: replaced", "superseded_by: live"]));
  write("orphan.md", fm(["name: orphan", "description: no index line"]));
  // recall.py treats an empty value as absent, so this file is a live orphan, not superseded.
  write("empty.md", fm(["name: empty", "description: blank key", "superseded_by:"]));

  // Every non-archive subfolder is a demotion tier (rest/ from the core cap, cold/ older): unindexed
  // on purpose, so never an orphan-file, and all counted on the one `demoted files` line.
  for (const [tier, file] of [["rest", "demoted.md"], ["rest", "demoted2.md"], ["cold", "chilly.md"]]) {
    fs.mkdirSync(path.join(dir, tier), { recursive: true });
    fs.writeFileSync(path.join(dir, tier, file), fm([`name: ${file}`, "description: moved out of core"]));
  }
  fs.mkdirSync(path.join(dir, "archive"));
  fs.writeFileSync(path.join(dir, "archive", "gone.md"), fm(["name: gone", "description: archived"]));

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

    const demoted = /^demoted files \(.*\): (\d+)\n((?:  \S.*\n)*)/m.exec(r.stdout.replace(/\r/g, ""));
    const demotedNames = demoted ? demoted[2].split("\n").filter(Boolean).map((l) => path.basename(l.trim())).sort().join(",") : "";
    check("every tier file (rest/ and cold/) is on the demoted files line, archive/ is not",
      demoted && demoted[1] === "3" && demotedNames === "chilly.md,demoted.md,demoted2.md", r.stdout);
    check("there is no separate rest line", !/^rest \(/m.test(r.stdout), r.stdout);
    check("a tier file is not an orphan-file in any reading",
      orphanLists.every((l) => !l.files.some((f) => f === "chilly.md" || f.startsWith("demoted"))), JSON.stringify(orphanLists));
    check("an index line pointing into a tier is not an orphan-index-entry",
      /orphan-index-entry: 0\b/.test(r.stdout), r.stdout);
    check("a small index reports its core size without OVER",
      /^core index: \d+ \/ 8192 bytes$/m.test(r.stdout), r.stdout);
  }

  // A MEMORY.md past the 8192-byte core cap is flagged OVER, with the overshoot.
  const bigDir = fs.mkdtempSync(path.join(os.tmpdir(), "reach-test-big-"));
  try {
    const bigIndex = Array.from({ length: 120 }, (_, i) => `- [Entry ${i}](e${i}.md) - ${"x".repeat(70)}`).join("\n") + "\n";
    fs.writeFileSync(path.join(bigDir, "MEMORY.md"), bigIndex);
    const bytes = Buffer.byteLength(bigIndex, "utf8");
    const big = spawnSync(process.execPath, [script, bigDir], { encoding: "utf8", timeout: 60000 });
    check("an index over 8192 bytes is flagged OVER",
      big.status === 0 && big.stdout.includes(`core index: ${bytes} / 8192 bytes OVER by ${bytes - 8192}`),
      bytes + " :: " + big.stdout.split("\n").slice(0, 4).join(" | ") + big.stderr);
  } finally {
    fs.rmSync(bigDir, { recursive: true, force: true });
    check("big scratch dir removed", !fs.existsSync(bigDir), bigDir);
  }
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}

check("scratch dir removed", !fs.existsSync(dir), dir);
process.exit(failed ? 1 : 0);
