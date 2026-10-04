---
name: siliqun-rotor
description: Integrate Siliqun Rotor, the decision engine for AI agents, into an application. Use when the user wants an assistant or agent that picks one of their app's actions from a user's request, asks for missing values instead of guessing, waits for confirmation before a change, or refuses when nothing fits; when they mention Siliqun Rotor, /v1/task, /v1/systemone, route_request, a project key, or a Studio flow.
---

# Integrating Siliqun Rotor

Siliqun Rotor decides; the application acts. Given a user's request and the tools (actions) the
application allows, the engine returns one outcome with its evidence. It never executes a tool
and never authorizes one. Docs: https://siliqunta.com/docs/ (agent-readable index:
https://siliqunta.com/llms.txt).

## The four outcomes, and what the application must do

| `outcome` | Meaning | The application |
|---|---|---|
| `decided` (`may_act: true`) | One tool fits; `tool_call.name` and `tool_call.arguments` are bound from the request | checks the user's permission, then runs the tool itself |
| `ask` | A tool fits but a required value is missing (`why` names it) | asks the user for that value; runs nothing |
| `unresolved` | Two tools fit equally | asks the user which one; runs nothing |
| `refused` | No declared tool fits | runs nothing; offers a rephrase, a suggestion, or a person |

Never execute on anything but `decided`, and never treat `decided` as permission: the engine does
not know who is signed in.

## Calling it

Route one request (local engine shown; hosted is `https://api.sqrengine.com`):

```bash
curl -sS http://127.0.0.1:8700/v1/task -H 'Content-Type: application/json' -d '{
  "task": "route",
  "question": "How many vacation days do I have left?",
  "tools": [{"type": "function", "function": {
    "name": "get_leave_balance",
    "description": "Shows how many days of leave an employee has left, by type",
    "parameters": {"type": "object",
      "properties": {"leave_type": {"type": "string", "enum": ["vacation", "sick", "parental", "unpaid"]}},
      "required": ["leave_type"]}}}]
}'
```

Hosted: send the project key server-side only, as `Authorization: Bearer <key>`, with
`X-SQR-Project-ID: <project>` (and `X-SQR-Client-ID` if the project requires a client
reference). With a project key, `/v1/task` accepts only `task: "route"`; an activated Studio flow is
called through `POST /v1/chat/completions` with `{"model": "sqr", "flow": "<flow id>", "messages": [...]}`.
Never put a project key in browser code.

SDKs: `@siliqun-rotor/sdk` (`client.route(question, tools)`) and Python `siliqun-rotor`
(`SiliqunRotorClient`), installed from https://github.com/siliqun-rotor/releases (not npm or PyPI).

## Declaring tools so the engine decides well

The engine locates each tool's declared criteria in the user's words, so the declaration is the
lever:

1. **One sentence per tool, in the words users actually type.** "Shows how many days of leave an
   employee has left, by type" matches "how many days do I have left".
2. **Use `enum` for closed sets.** A value is bound only when it is located in the request; an
   enum lets "vacation" bind to `leave_type`.
3. **Mark what is truly required as `required`.** A missing required value becomes `ask`, which
   is the point: the engine will not invent a date or an amount.
4. **Keep tools distinct.** Two tools with overlapping descriptions produce `unresolved`.
5. **Mark changes as changes.** A tool that writes data should say so; the application shows a
   confirmation before running it.

When a request is refused that should have matched, read `evidence` and the closest tool, then
add the user's wording to that tool's description rather than adding special cases in code.

## Tools for coding agents

- MCP server (stdio): `siliqun-rotor-mcp` with tools `route_request`, `ask_flow`, `engine_health`.
  Settings: `SILIQUN_ROTOR_ENGINE`, `SILIQUN_ROTOR_PROJECT_KEY`, `SILIQUN_ROTOR_PROJECT`,
  `SILIQUN_ROTOR_FLOW`, `SILIQUN_ROTOR_CLIENT`.
- A local engine is itself an MCP server: `siliq-web --mcp-stdio` (tools `route`, `decide`,
  `act`, `read`, `shape`, `task`).

Do not quote benchmark numbers unless they come from https://siliqunta.com/benchmarks/ with their
date.
