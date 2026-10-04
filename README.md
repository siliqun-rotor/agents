# Siliqun Rotor for AI agents

[Siliqun Rotor](https://siliqunta.com) is a decision engine for AI agents. Give it a user's request
and the tools your application allows. It answers with one outcome:

- **decided**: one tool fits, with its arguments;
- **ask**: a tool fits, but a required value is missing;
- **unresolved**: two tools fit equally;
- **refused**: no tool fits.

Each outcome comes with its evidence. It never runs a tool. Your application checks permissions
and runs it.

This repository packages Siliqun Rotor for coding agents and MCP clients:

| | What it is |
|---|---|
| `mcp/siliqun-rotor-mcp.mjs` | An MCP server (stdio, Node 18+, no dependencies) with the tools `route_request`, `ask_flow` and `engine_health` |
| `plugins/siliqun-rotor/` | A Claude Code plugin: the MCP server and the integration skill |
| `skills/siliqun-rotor/SKILL.md` | The integration skill on its own, in the [Agent Skills](https://agentskills.io) format |
| `plugins/agentbus/` | A Claude Code plugin for agent teams: your agentbus over MCP, unread messages at each prompt, and a coordination skill |
| `skills/agentbus/SKILL.md` | The coordination skill on its own |
| `.claude-plugin/marketplace.json` | A Claude Code plugin marketplace with both plugins |

Documentation: https://siliqunta.com/docs/. Agent-readable index: https://siliqunta.com/llms.txt.

## Which engine

The MCP server talks to a Siliqun Rotor engine:

- **On your computer** (free): download the engine from
  [the releases](https://github.com/siliqun-rotor/releases/releases/latest), then start it with
  `bin/siliq-web --port 8700`. No key is needed. This is the default.
- **Hosted**: set `SILIQUN_ROTOR_ENGINE=https://api.sqrengine.com`. Create a project key in the
  [Studio](https://studio.sqrplatform.com) under Customer Settings. Then set
  `SILIQUN_ROTOR_PROJECT_KEY` and `SILIQUN_ROTOR_PROJECT`. To use `ask_flow`, also set
  `SILIQUN_ROTOR_FLOW` to an activated flow's ID.

The key goes only to the engine you set. Keep it in your environment, not in a file you commit.

## Claude Code

Install the plugin from this marketplace:

```text
/plugin marketplace add siliqun-rotor/agents
/plugin install siliqun-rotor@siliqun-rotor
```

Or add only the MCP server:

```bash
claude mcp add --transport stdio siliqun-rotor \
  --env SILIQUN_ROTOR_ENGINE=http://127.0.0.1:8700 \
  -- node /path/to/siliqun-rotor-mcp.mjs
```

## Codex CLI

Add the server to `~/.codex/config.toml`:

```toml
[mcp_servers.siliqun-rotor]
command = "node"
args = ["/path/to/siliqun-rotor-mcp.mjs"]
env = { SILIQUN_ROTOR_ENGINE = "http://127.0.0.1:8700" }
```

For the integration guidance, copy `skills/siliqun-rotor/` into the folder your agent reads skills
from.

## Cursor, Claude Desktop and other MCP clients

Use the standard `mcpServers` entry:

```json
{
  "mcpServers": {
    "siliqun-rotor": {
      "command": "node",
      "args": ["/path/to/siliqun-rotor-mcp.mjs"],
      "env": { "SILIQUN_ROTOR_ENGINE": "http://127.0.0.1:8700" }
    }
  }
}
```

## agentbus: a live channel for a team of agents

agentbus is the channel our own agents use to work together. Messages have read state. Tasks
have one owner, a status and a log. Questions for a person go to them as decisions. The server
is also a remote MCP server (Streamable HTTP, with OAuth 2.1 or an agent token), with these tools:
`inbox`, `read_message`, `send_message`, `my_tasks`, `update_task`, `record_check`,
`critical_tasks`, `ask_owner`, `heartbeat`, `search` and `fetch`.

The `agentbus` plugin connects Claude Code to **your team's own bus**:

```text
/plugin install agentbus@siliqun-rotor
```

Claude Code asks for two settings. One is the bus address. The other is this agent's token, which
your bus administrator creates with `agentbus token add <name>`. The token is kept in your
system's credential store. After that:

- each prompt starts with any unread messages;
- the agent can read, reply, update its tasks and ask a person for a decision;
- the skill teaches it the routine: check the inbox, set the task status, report, and check again.

Codex CLI, or any MCP client with a bearer token:

```toml
[mcp_servers.agentbus]
url = "https://bus.example.com/mcp"
bearer_token_env_var = "AGENTBUS_TOKEN"
```

ChatGPT connectors and agents use the OAuth sign-in at the same `/mcp` address.

**You need a bus to connect to.** The agentbus server is not yet published as a download, so
this plugin is for teams that already run one.

## A local engine is also an MCP server

Started as `bin/siliq-web --mcp-stdio`, the engine serves its own tools over stdio: `route`,
`decide`, `act`, `read`, `shape` and `task`. It needs no network and no key.

## Licence

Apache-2.0. See `LICENSE`.
