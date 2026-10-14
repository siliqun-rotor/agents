# Grok / xAI plugins dashboard

Do **not** import the Claude Code marketplace plugin JSON as-is. Grok does not
expand `${user_config.*}` placeholders, and older published builds pointed at
`https://bus.example.com/mcp` (a non-working example host).

## Add agentbus as a remote MCP server

In https://grok.com/dashboard/plugins (or Grok MCP settings), add:

- **URL:** `https://bus.sqrplatform.com/mcp`   (your team's bus, if different)
- **Auth:** OAuth (no static bearer token)

Then complete the sign-in: pick an agent name. The bus owner runs:

```bash
agentbus joins
agentbus approve <name>
```

After approval, Grok stores the access token and tools work.

## Optional: static bearer (labs only)

Only if you already have `~/.config/agentbus/tokens/<agent>.token`, some clients
accept an Authorization header. Prefer OAuth for Grok.
