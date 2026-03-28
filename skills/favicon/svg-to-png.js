"use strict";

const fs = require("fs");

const RED = "\x1b[31m";
const GREEN = "\x1b[32m";
const RESET = "\x1b[0m";

const args = process.argv.slice(2);
if (args.length !== 3) {
  process.stderr.write(
    "Usage: node svg-to-png.js <input.svg> <output.png> <size>\n",
  );
  process.exit(1);
}

const [input, output, sizeArg] = args;

if (!/^\d+$/.test(sizeArg)) {
  process.stderr.write(
    `${RED}Error: <size> must be a positive integer (got: ${sizeArg})${RESET}\n`,
  );
  process.stderr.write(
    "Usage: node svg-to-png.js <input.svg> <output.png> <size>\n",
  );
  process.exit(1);
}

const size = parseInt(sizeArg, 10);
if (size <= 0) {
  process.stderr.write(
    `${RED}Error: <size> must be a positive integer (got: ${sizeArg})${RESET}\n`,
  );
  process.stderr.write(
    "Usage: node svg-to-png.js <input.svg> <output.png> <size>\n",
  );
  process.exit(1);
}

let sharp;
try {
  sharp = require("sharp");
} catch {
  process.stderr.write(
    `${RED}Error: sharp is not installed. Run: npm install -g sharp${RESET}\n`,
  );
  process.exit(1);
}

if (!fs.existsSync(input)) {
  process.stderr.write(`${RED}Error: Input file not found: ${input}${RESET}\n`);
  process.exit(1);
}

sharp(input)
  .resize(size, size)
  .png()
  .toFile(output)
  .then(() => {
    console.log(`${GREEN}✓ Generated ${output} (${size}x${size})${RESET}`);
    process.exit(0);
  })
  .catch((err) => {
    process.stderr.write(`${RED}Error: ${err.message}${RESET}\n`);
    process.exit(1);
  });
