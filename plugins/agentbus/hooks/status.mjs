#!/usr/bin/env node
// Post what this agent is doing to agentbus after each turn, so the owner can follow the work on the
// board without any agent having to remember to (the owner, 2026-10-07). The line is the headline of
// the agent's last reply: its first sentence, markdown stripped, one line, at most 280 characters.
//
// Two callers:
//   Claude Code: a Stop hook. The hook input arrives on stdin as JSON with `transcript_path`.
//   Codex: its `notify` program. The payload is the last argument, JSON with
//     {"type": "agent-turn-complete", "last-assistant-message": "..."}.
//     With `--then <command…> --`, the command before the payload runs first with the same
//     payload, so a notify command already configured (Computer Use) keeps working.
//
// It never blocks or changes the agent's turn: it prints nothing, always exits 0, and gives up after
// 2.5 s. It never prints the token. It posts at most once a minute; the bus also drops a line equal to
// the agent's current one. A line that looks like a secret is refused by the bus, never stored.
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const MAX = 280;
const MIN_GAP_MS = 60_000;

/** The headline of a reply: its first line of prose (headings, tables, rules, quotes and code
 *  skipped), cut to its first sentence when that is a real sentence, markdown stripped. */
export function headline(text) {
  if (typeof text !== 'string') return '';
  const prose = text
    .replace(/```[\s\S]*?```/g, ' ')
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !/^(\||-{3,}|#{1,6}(\s|$)|>)/.test(l));
  let line = (prose[0] || '')
    .replace(/^[-*+]\s+|^\d+\.\s+/, '')
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/[*_`~]+/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  const sentence = line.match(/^(.+?[.!?])(\s|$)/);
  if (sentence && sentence[1].length >= 20) line = sentence[1];
  if (line.length > MAX) line = line.slice(0, MAX - 1).trimEnd() + '…';
  return line;
}

/** The last assistant text in a Claude Code transcript (JSON lines). */
export function lastAssistantText(jsonl) {
  const lines = String(jsonl).split('\n');
  for (let i = lines.length - 1; i >= 0; i--) {
    let row;
    try { row = JSON.parse(lines[i]); } catch { continue; }
    const msg = row?.message;
    if (row?.type !== 'assistant' || msg?.role !== 'assistant' || !Array.isArray(msg.content)) continue;
    const text = msg.content.filter((c) => c?.type === 'text' && typeof c.text === 'string').map((c) => c.text).join('\n').trim();
    if (text) return text;
  }
  return '';
}

/** Codex: `--bus <url>`, `--token-file <path>` and `--then <cmd…> --` (Codex's notify passes no
 *  environment of its own), then the payload, which is the last argument. */
export function codexArgs(argv) {
  const then = [];
  let rest = [...argv];
  const at = rest.indexOf('--then');
  if (at >= 0) {
    const end = rest.indexOf('--', at + 1);
    if (end > at) {
      then.push(...rest.slice(at + 1, end));
      rest = [...rest.slice(0, at), ...rest.slice(end + 1)];
    }
  }
  const take = (flag) => {
    const i = rest.indexOf(flag);
    if (i < 0 || i + 1 >= rest.length - 1) return undefined;
    const v = rest[i + 1];
    rest.splice(i, 2);
    return v;
  };
  const bus = take('--bus');
  const tokenFile = take('--token-file');
  return { then, payload: rest[rest.length - 1], bus, tokenFile };
}

let override = {};

function config() {
  const url = (override.bus || process.env.CLAUDE_PLUGIN_OPTION_BUS_URL || process.env.AGENTBUS_URL || '').replace(/\/+$/, '');
  let token = (process.env.CLAUDE_PLUGIN_OPTION_BUS_TOKEN || process.env.AGENTBUS_TOKEN || '').trim();
  const file = override.tokenFile || process.env.AGENTBUS_TOKEN_FILE;
  if (override.tokenFile) token = '';
  if (!token && file) { try { token = readFileSync(file, 'utf8').trim(); } catch { /* none */ } }
  return { url, token };
}

function tooSoon(token) {
  const stamp = join(tmpdir(), `agentbus-status-${createHash('sha256').update(token).digest('hex').slice(0, 12)}`);
  try {
    if (Date.now() - Number(readFileSync(stamp, 'utf8')) < MIN_GAP_MS) return true;
  } catch { /* first post */ }
  try { writeFileSync(stamp, String(Date.now())); } catch { /* best effort */ }
  return false;
}

async function post(doing) {
  const { url, token } = config();
  if (!doing || !url || !token || !/^https?:\/\//.test(url) || tooSoon(token)) return;
  try {
    await fetch(`${url}/v1/heartbeat`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ doing }),
      signal: AbortSignal.timeout(2500),
    });
  } catch { /* unreachable: say nothing */ }
}

async function readStdin() {
  if (process.stdin.isTTY) return '';
  let data = '';
  for await (const chunk of process.stdin) data += chunk;
  return data;
}

async function main() {
  const argv = process.argv.slice(2);
  if (argv.length > 0) {
    // Codex notify
    const { then, payload, bus, tokenFile } = codexArgs(argv);
    override = { bus, tokenFile };
    if (then.length) {
      try { spawnSync(then[0], [...then.slice(1), payload], { stdio: 'ignore', timeout: 10_000 }); } catch { /* keep going */ }
    }
    let p;
    try { p = JSON.parse(payload); } catch { return; }
    if (p?.type !== 'agent-turn-complete') return;
    await post(headline(p['last-assistant-message']));
    return;
  }
  // Claude Code Stop hook
  let input;
  try { input = JSON.parse(await readStdin()); } catch { return; }
  if (!input?.transcript_path) return;
  let jsonl = '';
  try { jsonl = readFileSync(input.transcript_path, 'utf8'); } catch { return; }
  await post(headline(lastAssistantText(jsonl)));
}

if (import.meta.url === `file://${process.argv[1]}`) main().catch(() => {}).finally(() => process.exit(0));
