#!/usr/bin/env node
/**
 * siliqun-rotor-mcp: Siliqun Rotor as an MCP server (stdio) for coding agents and any MCP client.
 *
 * It asks a Siliqun Rotor engine for decisions and returns them. It never executes a tool,
 * never stores a key on disk, and sends the project key only to the engine.
 *
 *   route_request   which declared tool fits a request, with its arguments; or ask; or refuse
 *   ask_flow        send a message to an activated Studio flow (hosted project)
 *   engine_health   is the engine reachable, and does it require a key
 *
 * Settings (environment):
 *   SILIQUN_ROTOR_ENGINE       engine URL; default http://127.0.0.1:8700 (hosted: https://api.sqrengine.com)
 *   SILIQUN_ROTOR_PROJECT_KEY  project key for the hosted engine (create it in Studio, Customer Settings)
 *   SILIQUN_ROTOR_PROJECT      project ID (sent as X-SQR-Project-ID with the key)
 *   SILIQUN_ROTOR_FLOW         activated flow ID, for ask_flow
 *   SILIQUN_ROTOR_CLIENT       client reference, when the project requires one (X-SQR-Client-ID)
 *
 * Node 18+; no dependencies. Protocol: MCP over stdio, newline-delimited JSON-RPC 2.0.
 */
import { createInterface } from 'node:readline';

export const VERSION = '0.1.0';
const PROTOCOL = '2025-06-18';

export function settings(env = process.env) {
  return {
    engine: (env.SILIQUN_ROTOR_ENGINE || 'http://127.0.0.1:8700').replace(/\/+$/, ''),
    key: env.SILIQUN_ROTOR_PROJECT_KEY || '',
    project: env.SILIQUN_ROTOR_PROJECT || '',
    flow: env.SILIQUN_ROTOR_FLOW || '',
    client: env.SILIQUN_ROTOR_CLIENT || '',
  };
}

const TOOL_SCHEMA = {
  type: 'object',
  description: 'One action your application allows, in the OpenAI function format: {"type":"function","function":{"name","description","parameters"}} or the bare {"name","description","parameters"}.',
  additionalProperties: true,
};

export const TOOLS = [
  {
    name: 'route_request',
    title: 'Route a request to a declared tool',
    description:
      'Ask Siliqun Rotor which of the declared tools fits a user request, with which argument values. ' +
      'The answer is one of: decided (a tool and its arguments, with evidence), ask (a tool fits but a value is missing: ask the user), ' +
      'or refused (no declared tool fits: do not call any tool). It never runs the tool: your application checks permissions and runs it.',
    inputSchema: {
      type: 'object',
      properties: {
        question: { type: 'string', description: "The user's request, in their own words." },
        tools: { type: 'array', items: TOOL_SCHEMA, description: 'The tools your application allows for this request.' },
        today: { type: 'string', format: 'date', description: 'Optional: the date that words like "tomorrow" refer to (YYYY-MM-DD).' },
      },
      required: ['question', 'tools'],
    },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: 'ask_flow',
    title: 'Ask an activated Studio flow',
    description:
      "Send one user message to the project's activated Studio flow (needs SILIQUN_ROTOR_PROJECT_KEY, SILIQUN_ROTOR_PROJECT and SILIQUN_ROTOR_FLOW). " +
      'Returns the flow\'s reply and its decision. A change waits for confirmation in your application; nothing is executed here.',
    inputSchema: {
      type: 'object',
      properties: { message: { type: 'string', description: "The user's message." } },
      required: ['message'],
    },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: 'engine_health',
    title: 'Check the engine',
    description: 'Check that the configured Siliqun Rotor engine is reachable, and whether it requires a key.',
    inputSchema: { type: 'object', properties: {} },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
];

function headers(s) {
  const h = { 'Content-Type': 'application/json', 'User-Agent': `siliqun-rotor-mcp/${VERSION}` };
  if (s.key) h.Authorization = `Bearer ${s.key}`;
  if (s.project) h['X-SQR-Project-ID'] = s.project;
  if (s.client) h['X-SQR-Client-ID'] = s.client;
  return h;
}

async function call(s, method, path, body, fetchImpl) {
  const res = await fetchImpl(`${s.engine}${path}`, {
    method, headers: headers(s), body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(30000),
  });
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = { body: text.slice(0, 500) }; }
  if (!res.ok) {
    const code = (data && (data.error?.code || data.code || data.error)) || `http_${res.status}`;
    const err = new Error(`engine answered ${res.status}: ${typeof code === 'string' ? code : JSON.stringify(code)}`);
    err.data = data;
    throw err;
  }
  return data;
}

export async function runTool(name, args = {}, s = settings(), fetchImpl = fetch) {
  if (name === 'route_request') {
    if (typeof args.question !== 'string' || !args.question.trim()) throw new Error('question is required');
    if (!Array.isArray(args.tools) || args.tools.length === 0) throw new Error('tools must be a non-empty array of declared tools');
    const body = { task: 'route', question: args.question, tools: args.tools };
    if (args.today) body.today = args.today;
    return call(s, 'POST', '/v1/task', body, fetchImpl);
  }
  if (name === 'ask_flow') {
    if (typeof args.message !== 'string' || !args.message.trim()) throw new Error('message is required');
    if (!s.flow) throw new Error('set SILIQUN_ROTOR_FLOW to the activated flow ID (Studio, Ship)');
    return call(s, 'POST', '/v1/chat/completions',
      { model: 'sqr', flow: s.flow, messages: [{ role: 'user', content: args.message }] }, fetchImpl);
  }
  if (name === 'engine_health') return call(s, 'GET', '/v1/health', undefined, fetchImpl);
  throw new Error(`no tool "${name}"`);
}

export async function handle(msg, s = settings(), fetchImpl = fetch) {
  const { id, method, params = {} } = msg;
  const reply = (result) => ({ jsonrpc: '2.0', id, result });
  switch (method) {
    case 'initialize':
      return reply({
        protocolVersion: params.protocolVersion || PROTOCOL,
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: 'siliqun-rotor', title: 'Siliqun Rotor', version: VERSION },
        instructions:
          'Use route_request before calling one of your own tools on a user request: act only on "decided", ask the user on "ask", ' +
          'and call nothing on "refused". The decision never authorizes the action; your application still checks permissions.',
      });
    case 'ping':
      return reply({});
    case 'tools/list':
      return reply({ tools: TOOLS });
    case 'tools/call': {
      try {
        const out = await runTool(params.name, params.arguments || {}, s, fetchImpl);
        return reply({ content: [{ type: 'text', text: JSON.stringify(out, null, 2) }], structuredContent: out });
      } catch (e) {
        return reply({ isError: true, content: [{ type: 'text', text: String(e.message || e) }] });
      }
    }
    default:
      if (id === undefined) return null; // a notification needs no answer
      return { jsonrpc: '2.0', id, error: { code: -32601, message: `method not found: ${method}` } };
  }
}

function serve() {
  const s = settings();
  const rl = createInterface({ input: process.stdin });
  rl.on('line', async (line) => {
    if (!line.trim()) return;
    let msg;
    try { msg = JSON.parse(line); } catch {
      process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'parse error' } }) + '\n');
      return;
    }
    const out = await handle(msg, s);
    if (out) process.stdout.write(JSON.stringify(out) + '\n');
  });
  process.stderr.write(`siliqun-rotor-mcp ${VERSION}: engine ${s.engine}${s.key ? ' (project key set)' : ''}\n`);
}

if (import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith('siliqun-rotor-mcp')) serve();
