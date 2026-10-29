// Minimal lint: no tabs, no trailing whitespace, no console.log in src/.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

let problems = 0;
for (const dir of ["src", "test", "scripts"]) {
  for (const name of readdirSync(dir)) {
    if (!name.endsWith(".js")) continue;
    const path = join(dir, name);
    readFileSync(path, "utf8").split("\n").forEach((line, i) => {
      if (/\t/.test(line) || /\s+$/.test(line) || (dir === "src" && /console\.log/.test(line))) {
        console.error(`${path}:${i + 1}: ${line.trim()}`);
        problems += 1;
      }
    });
  }
}
process.exit(problems ? 1 : 0);
