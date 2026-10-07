// node agentbus-plugin/hooks/status.test.mjs: the status hook's line and its two callers.
import assert from 'node:assert/strict';
import { codexArgs, headline, lastAssistantText } from './status.mjs';

assert.equal(headline('**Merged PR158 and deployed it.** The Studio is next.'), 'Merged PR158 and deployed it.');
assert.equal(headline('Short. Then a longer second sentence.'), 'Short. Then a longer second sentence.');
assert.equal(headline('## Status\n\nThe board is live at [the board](https://x). More here.'), 'The board is live at the board.');
assert.equal(headline('```\ncode\n```\n- First item done and verified live today. Then more.'), 'First item done and verified live today.');
assert.equal(headline('| a | b |\n|---|---|\nAfter the table, a real line of status.'), 'After the table, a real line of status.');
assert.equal(headline('x'.repeat(400)).length, 280);
assert.equal(headline(null), '');

const t = [
  { type: 'user', message: { role: 'user', content: 'hi' } },
  { type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text: 'Old reply.' }] } },
  { type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text: 'Newest reply here.' }] } },
  { type: 'assistant', message: { role: 'assistant', content: [{ type: 'tool_use', name: 'Bash' }] } },
].map((r) => JSON.stringify(r)).join('\n') + '\nnot json';
assert.equal(lastAssistantText(t), 'Newest reply here.');

assert.deepEqual(codexArgs(['--then', '/app/client', 'turn-ended', '--', '{"a":1}']), { then: ['/app/client', 'turn-ended'], payload: '{"a":1}', bus: undefined, tokenFile: undefined });
assert.deepEqual(codexArgs(['{"a":1}']), { then: [], payload: '{"a":1}', bus: undefined, tokenFile: undefined });
assert.deepEqual(
  codexArgs(['--bus', 'https://bus.example', '--token-file', '/t/codex.token', '--then', 'c', 'turn-ended', '--', '{"b":2}']),
  { then: ['c', 'turn-ended'], payload: '{"b":2}', bus: 'https://bus.example', tokenFile: '/t/codex.token' },
);
console.log('status.mjs: ok');
