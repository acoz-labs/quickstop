// Local instruction delivery only. Never inspect transcripts or consumer files.
import { readFileSync } from 'node:fs';
const allowed = new Set(['SessionStart', 'SubagentStart']);
const event = process.argv[2];
if (!allowed.has(event)) throw new Error('Unsupported writing hook event');
const core = readFileSync(new URL('../skills/writing-for-humans/references/core.md', import.meta.url), 'utf8');
process.stdout.write(JSON.stringify({hookSpecificOutput: {hookEventName: event, additionalContext: core}}) + '\n');
