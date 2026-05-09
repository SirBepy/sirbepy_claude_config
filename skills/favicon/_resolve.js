"use strict";

const { execSync } = require("child_process");

let cachedGlobalRoot;
function getGlobalRoot() {
  if (cachedGlobalRoot === undefined) {
    cachedGlobalRoot = execSync("npm root -g", { encoding: "utf8" }).trim();
  }
  return cachedGlobalRoot;
}

function resolveModule(name) {
  try {
    return require(name);
  } catch (err) {
    if (err.code !== "MODULE_NOT_FOUND") throw err;
    const resolved = require.resolve(name, { paths: [getGlobalRoot()] });
    return require(resolved);
  }
}

module.exports = { resolveModule };
