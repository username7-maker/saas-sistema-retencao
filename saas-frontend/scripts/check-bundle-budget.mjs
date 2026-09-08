import { readdir, stat } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const assetsDirectory = fileURLToPath(new URL("../dist/assets/", import.meta.url));
const maximumJavaScriptBytes = 500 * 1024;
const files = await readdir(assetsDirectory);
const oversized = [];

for (const file of files) {
  if (!file.endsWith(".js")) continue;
  const details = await stat(join(assetsDirectory, file));
  if (details.size > maximumJavaScriptBytes) {
    oversized.push(`${file}: ${(details.size / 1024).toFixed(1)} kB`);
  }
}

if (oversized.length) {
  throw new Error(`Bundle budget excedido (maximo 500 kB por chunk):\n${oversized.join("\n")}`);
}

console.log("Bundle budget aprovado: nenhum chunk JavaScript excede 500 kB.");
