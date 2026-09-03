#!/usr/bin/env node
/*
 * Compile the contracts with solc and write a flat artifact map to out/artifacts.json.
 *
 * Foundry is the project's contract toolchain (see foundry.toml and the .t.sol
 * suite), but `forge` needs a download this environment's egress policy blocks.
 * solc via npm compiles the same sources with the same settings, so the Python
 * EVM suite can execute real bytecode here and CI stays honest either way.
 */
const fs = require("fs");
const path = require("path");
const solc = require("solc");

const ROOT = __dirname;
const SOURCES = ["src", "test/mocks"];

function collect(dir, acc = {}) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) collect(full, acc);
    else if (entry.name.endsWith(".sol")) {
      acc[path.relative(ROOT, full)] = { content: fs.readFileSync(full, "utf8") };
    }
  }
  return acc;
}

const sources = SOURCES.reduce((acc, d) => collect(path.join(ROOT, d), acc), {});

const input = {
  language: "Solidity",
  sources,
  settings: {
    optimizer: { enabled: true, runs: 200 },
    evmVersion: "cancun",
    outputSelection: { "*": { "*": ["abi", "evm.bytecode.object", "evm.deployedBytecode.object"] } },
  },
};

function findImport(importPath) {
  for (const base of [ROOT, path.join(ROOT, "src"), path.join(ROOT, "test/mocks")]) {
    const candidate = path.resolve(base, importPath);
    if (fs.existsSync(candidate)) return { contents: fs.readFileSync(candidate, "utf8") };
  }
  return { error: "not found: " + importPath };
}

const output = JSON.parse(solc.compile(JSON.stringify(input), { import: findImport }));

let failed = false;
for (const err of output.errors || []) {
  if (err.severity === "error") { failed = true; console.error(err.formattedMessage); }
  else console.warn(err.formattedMessage);
}
if (failed) process.exit(1);

const artifacts = {};
for (const [file, contracts] of Object.entries(output.contracts || {})) {
  for (const [name, c] of Object.entries(contracts)) {
    artifacts[name] = {
      abi: c.abi,
      bytecode: "0x" + c.evm.bytecode.object,
      source: file,
    };
  }
}

fs.mkdirSync(path.join(ROOT, "out"), { recursive: true });
fs.writeFileSync(path.join(ROOT, "out", "artifacts.json"), JSON.stringify(artifacts, null, 2));
console.log("compiled:", Object.keys(artifacts).join(", "));
