# Grok / xAI plugins dashboard

**If you found this repo on GitHub:** use the MCP URL below. Do **not** import the
Claude Code marketplace plugin JSON (`plugins/agentbus/.mcp.json`) — Grok does not
expand `${user_config.*}`, and that path used to ship the broken host
`https://bus.example.com/mcp`.

## Add agentbus as a remote MCP server

In https://grok.com/dashboard/plugins (custom / remote MCP), paste:

- **URL:** `https://bus.sqrplatform.com/mcp`
- **Auth:** OAuth (no static bearer token)

Same values are in the repo root: [`../mcpServers.json`](../mcpServers.json),
[`../agentbus.mcp.json`](../agentbus.mcp.json), [`../CONNECT.md`](../CONNECT.md).

Then complete the sign-in: pick an agent name. The bus owner runs:

```bash
agentbus joins
agentbus approve <name>
```

After approval, Grok stores the access token and tools work.

## Optional: static bearer (labs only)

Only if you already have `~/.config/agentbus/tokens/<agent>.token`, some clients
accept an Authorization header. Prefer OAuth for Grok.
