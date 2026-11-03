#!/usr/bin/env node
// Print this agent's unread agentbus messages, one line each, so the agent sees them before it
// works. It marks nothing read (the agent reads a message with read_message), never prints the
// token, and stays silent when the bus is not configured or does not answer within 2.5 s.
// At session start it also prints the memory rule, so the agent keeps its memory and skills on
// the bus instead of in local files.
const url = (process.env.CLAUDE_PLUGIN_OPTION_BUS_URL || process.env.AGENTBUS_URL || '').replace(/\/+$/, '');
const token = (process.env.CLAUDE_PLUGIN_OPTION_BUS_TOKEN || process.env.AGENTBUS_TOKEN || '').trim();
const LIMIT = 10;

export function lines(messages) {
  if (!Array.isArray(messages) || messages.length === 0) return [];
  const shown = messages.slice(-LIMIT);
  const head = `agentbus: ${messages.length} unread message${messages.length === 1 ? '' : 's'} (read one with read_message; reply with send_message):`;
  const clean = (s) => String(s ?? '').replace(/[\r\n\t]+/g, ' ').slice(0, 160);
  return [head, ...shown.map((m) => `- ${clean(m.id).slice(0, 8)} ${clean(m.sender)}: ${clean(m.subject)}`)]
    .concat(messages.length > LIMIT ? [`- …and ${messages.length - LIMIT} more (inbox)`] : []);
}

export const MEMORY_RULE = [
  'agentbus memory: the bus is this team\'s memory. Before a task, run memory_index or recall for the subject',
  'and open one entry with memory_read; list_skills, then fetch_skill for one that fits. Write durable facts',
  'with memory_write, never into local memory files (~/.claude/projects/*/memory) or new .md handover notes.',
].join('\n');

export function sessionStart(raw) {
  try { return JSON.parse(raw).hook_event_name === 'SessionStart'; } catch { return false; }
}

async function stdin() {
  if (process.stdin.isTTY) return '';
  let s = '';
  for await (const chunk of process.stdin) s += chunk;
  return s;
}

async function main() {
  if (sessionStart(await stdin())) process.stdout.write(MEMORY_RULE + '\n');
  if (!url || !token || !/^https?:\/\//.test(url)) return;
  try {
    const res = await fetch(`${url}/v1/inbox?unread=1&limit=50`, {
      headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(2500),
    });
    if (!res.ok) return;
    const out = lines(await res.json());
    if (out.length) process.stdout.write(out.join('\n') + '\n');
  } catch { /* unreachable or malformed: say nothing, never block the prompt */ }
}

if (import.meta.url === `file://${process.argv[1]}`) main();
