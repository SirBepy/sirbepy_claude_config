"use strict";

const fs = require("fs");

const RED = "\x1b[31m";
const GREEN = "\x1b[32m";
const RESET = "\x1b[0m";

const args = process.argv.slice(2);
if (args.length !== 2) {
  process.stderr.write("Usage: node png-to-ico.js <input.png> <output.ico>\n");
  process.exit(1);
}

const [input, output] = args;

let pngToIco;
try {
  pngToIco = require("png-to-ico");
} catch {
  process.stderr.write(
    `${RED}Error: png-to-ico is not installed. Run: npm install -g png-to-ico${RESET}\n`,
  );
  process.exit(1);
}

if (!fs.existsSync(input)) {
  process.stderr.write(`${RED}Error: Input file not found: ${input}${RESET}\n`);
  process.exit(1);
}

pngToIco(input)
  .then((buf) => {
    fs.writeFileSync(output, buf);
    console.log(`${GREEN}✓ Generated ${output}${RESET}`);
    process.exit(0);
  })
  .catch((err) => {
    process.stderr.write(`${RED}Error: ${err.message}${RESET}\n`);
    process.exit(1);
  });
