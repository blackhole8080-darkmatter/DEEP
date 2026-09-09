import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const outputDir = resolve(scriptDir, "../../static/app-dist");
const indexPath = resolve(outputDir, "index.html");
const assetsDir = resolve(outputDir, "assets");

if (!existsSync(indexPath)) {
  throw new Error("Expected build entrypoint at " + indexPath);
}
if (!existsSync(assetsDir)) {
  throw new Error("Expected asset directory at " + assetsDir);
}

const index = readFileSync(indexPath, "utf8");
const assets = readdirSync(assetsDir);
const javascriptAssets = assets.filter((name) => name.endsWith(".js"));
const cybertechChunk = assets.find((name) => name.startsWith("cybertech-world-view-") && name.endsWith(".js"));

if (!index.includes("assets/")) {
  throw new Error("Build entrypoint does not reference hashed assets");
}
if (javascriptAssets.length === 0) {
  throw new Error("Build produced no JavaScript assets");
}
if (!cybertechChunk) {
  throw new Error("Build did not emit the Cybertech World lazy chunk");
}

console.log("Frontend build verified: " + javascriptAssets.length + " JavaScript assets, Cybertech World chunk " + cybertechChunk);
