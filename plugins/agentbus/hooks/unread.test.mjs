// node agentbus-plugin/hooks/unread.test.mjs: the unread hook's lines and its session-start rule.
import assert from 'node:assert/strict';
import { lines, MEMORY_RULE, sessionStart } from './unread.mjs';

assert.equal(sessionStart('{"hook_event_name":"SessionStart","source":"startup"}'), true);
assert.equal(sessionStart('{"hook_event_name":"UserPromptSubmit","prompt":"hi"}'), false);
assert.equal(sessionStart('not json'), false);
assert.equal(sessionStart(''), false);
assert.match(MEMORY_RULE, /memory_write/);
assert.match(MEMORY_RULE, /fetch_skill/);
assert.deepEqual(lines([]), []);
assert.equal(lines([{ id: 'abcdef123', sender: 'codex', subject: 'one\nline' }])[1], '- abcdef12 codex: one line');
console.log('unread.mjs: ok');
