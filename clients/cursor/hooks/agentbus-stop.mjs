#!/usr/bin/env node
// Cursor stop hook: post heartbeat status, clear/keep busy marker, and
// auto-continue when Agent Bus still has work for cursor.
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, unlinkSync, existsSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { join } from 'node:path';

const URL = (process.env.AGENTBUS_URL || '').replace(/\/+$/, '');
const TOKEN_FILE = process.env.AGENTBUS_TOKEN_FILE || join(homedir(), '.config/agentbus/tokens/cursor.token');
const BUSY = process.env.AGENTBUS_BUSY_FILE || join(homedir(), '.config/agentbus/wake/cursor.lock.busy');
const MAX = 280;
const MIN_GAP_MS = 60_000;

function token() {
  try {
    return (process.env.AGENTBUS_TOKEN || readFileSync(TOKEN_FILE, 'utf8')).trim();
  } catch {
    return '';
  }
}

function headline(text) {
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

function lastAssistantText(jsonl) {
  const lines = String(jsonl).split('\n');
  for (let i = lines.length - 1; i >= 0; i--) {
    let row;
    try { row = JSON.parse(lines[i]); } catch { continue; }
    const msg = row?.message;
    if (row?.type !== 'assistant' || msg?.role !== 'assistant' || !Array.isArray(msg.content)) continue;
    const text = msg.content
      .filter((c) => c?.type === 'text' && typeof c.text === 'string')
      .map((c) => c.text)
      .join('\n')
      .trim();
    if (text) return text;
  }
  // Cursor transcript variants
  for (let i = lines.length - 1; i >= 0; i--) {
    let row;
    try { row = JSON.parse(lines[i]); } catch { continue; }
    if (row?.role === 'assistant' && typeof row.content === 'string' && row.content.trim()) return row.content.trim();
    if (typeof row?.text === 'string' && row.text.trim() && (row.type === 'assistant' || row.role === 'assistant')) return row.text.trim();
  }
  return '';
}

function tooSoon(tok) {
  const stamp = join(tmpdir(), `agentbus-status-${createHash('sha256').update(tok).digest('hex').slice(0, 12)}`);
  try {
    if (Date.now() - Number(readFileSync(stamp, 'utf8')) < MIN_GAP_MS) return true;
  } catch { /* first */ }
  try { writeFileSync(stamp, String(Date.now())); } catch { /* best effort */ }
  return false;
}

async function postHeartbeat(tok, doing) {
  if (!doing || !tok || !/^https?:\/\//.test(URL) || tooSoon(tok)) return;
  try {
    await fetch(`${URL}/v1/heartbeat`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${tok}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ doing }),
      signal: AbortSignal.timeout(2500),
    });
  } catch { /* ignore */ }
}

async function get(path, tok) {
  const res = await fetch(`${URL}${path}`, {
    headers: { Authorization: `Bearer ${tok}` },
    signal: AbortSignal.timeout(2500),
  });
  if (!res.ok) return null;
  return res.json();
}

/** Fresh mail that looks like a handoff — ignore historical broadcasts. */
function actionableUnread(messages, maxAgeHours = 18) {
  const cutoff = Date.now() - maxAgeHours * 3600_000;
  const re = /\b(cursor|assign|handoff|please (take|fix|do)|your (task|queue)|for you)\b/i;
  return (Array.isArray(messages) ? messages : []).filter((m) => {
    const t = Date.parse(m?.created_at || m?.at || m?.ts || '');
    if (Number.isFinite(t) && t < cutoff) return false;
    const subject = String(m?.subject || '');
    const to = String(m?.recipient || m?.to || '');
    if (to === 'cursor') return true;
    if (to && to !== 'all' && to !== 'cursor') return false;
    // Broadcasts: only if clearly aimed at cursor, not generic "handoff" history.
    return /\bcursor\b/i.test(subject) && re.test(subject);
  });
}

async function readStdin() {
  if (process.stdin.isTTY) return '';
  let data = '';
  for await (const chunk of process.stdin) data += chunk;
  return data;
}

async function main() {
  let input = {};
  try { input = JSON.parse(await readStdin() || '{}'); } catch { input = {}; }

  const tok = token();
  let doing = '';
  if (input?.transcript_path && existsSync(input.transcript_path)) {
    try { doing = headline(lastAssistantText(readFileSync(input.transcript_path, 'utf8'))); } catch { /* ignore */ }
  }
  if (!doing && typeof input?.status === 'string') doing = headline(input.status);
  if (!doing) doing = 'cursor turn complete; checking agentbus queue';

  if (tok) await postHeartbeat(tok, doing);

  let followup = null;
  if (tok && /^https?:\/\//.test(URL)) {
    try {
      const [messages, tasks] = await Promise.all([
        get('/v1/inbox?unread=1&peek=true&limit=50', tok),
        get('/v1/tasks?owner=cursor&status=todo,doing', tok),
      ]);
      const open = Array.isArray(tasks) ? tasks : [];
      const doingTask = open.find((t) => t.status === 'doing');
      const todoTask = open.find((t) => t.status === 'todo' && t.ready !== false);
      const mail = actionableUnread(messages);

      if (doingTask) {
        followup = `AgentBus continue (no user needed): task ${doingTask.id} is still doing — "${doingTask.title}". Resume it: update the board, run the work, record checks/evidence, then move status. After that, take the next todo you own.`;
      } else if (todoTask) {
        followup = `AgentBus continue (no user needed): pick up todo ${todoTask.id} — "${todoTask.title}". Ack/set doing, execute with evidence on the board, notify the assigner, then take the next ready task.`;
      } else if (mail.length) {
        const m = mail[mail.length - 1];
        followup = `AgentBus continue (no user needed): actionable unread from ${m.sender}: "${m.subject}" (${String(m.id || '').slice(0, 8)}…). Read it, act if it assigns work to cursor, then idle or take the next board task.`;
      }
    } catch { /* ignore */ }
  }

  if (followup) {
    try { writeFileSync(BUSY, String(Date.now())); } catch { /* ignore */ }
    process.stdout.write(JSON.stringify({ followup_message: followup }) + '\n');
  } else {
    try { if (existsSync(BUSY)) unlinkSync(BUSY); } catch { /* ignore */ }
    process.stdout.write('{}\n');
  }
}

main().catch(() => {
  try { process.stdout.write('{}\n'); } catch { /* ignore */ }
}).finally(() => process.exit(0));
