import { readFileSync } from 'node:fs';
const core = readFileSync(new URL('../skills/writing-for-humans/references/core.md', import.meta.url), 'utf8');
export default function writingForHumans(pi) {
  pi.on('before_agent_start', async (event) => {
    // Preserve the chained prompt, including changes from earlier extensions.
    // Pi rebuilds the base each turn; this also avoids duplicate registrations.
    if (event.systemPrompt.includes(core)) return {};
    return { systemPrompt: event.systemPrompt + '\n\n' + core };
  });
}
