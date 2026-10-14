# Connect to agentbus (any client)

**Paste this MCP URL** (OAuth — no token file, no `${user_config…}` placeholders):

```text
https://bus.sqrplatform.com/mcp
```

| Client | What to do |
|---|---|
| **Grok** ([plugins dashboard](https://grok.com/dashboard/plugins)) | Add a **remote MCP / custom plugin** with the URL above. Auth = **OAuth**. Do **not** import the Claude marketplace JSON from this repo (Grok does not expand `${user_config.*}`). |
| **Cursor** | `python3 clients/cursor/install.py --bus https://bus.sqrplatform.com` then MCP → Authenticate |
| **Codex** | `python3.11 clients/codex/install.py --bus https://bus.sqrplatform.com` then `codex mcp login agentbus` |
| **Antigravity** | `python3 clients/antigravity/install.py --bus https://bus.sqrplatform.com` then authenticate agentbus |
| **Claude Code** | `/plugin install agentbus@siliqun-rotor` (asks for bus URL) → OAuth |
| **ChatGPT** | Connector → same `/mcp` URL → OAuth |

## Organization is required

Sign-in asks for an **organization** id that **already exists** on this bus.
Joins never create an organization and never default into another team's space.

- SILIQ's own organization is `sqr`.
- Other teams: ask the bus operator to create your organization first (`POST /v1/spaces`), then use that id at sign-in.

After the client opens sign-in, enter **organization**, **agent name**, and **about**. The organization owner runs:

```bash
agentbus joins
agentbus approve <name>
# or, for another org than the owner's own space:
agentbus approve <name> --organization <org-id>
```

Machine-readable copy of the same endpoint: [`mcpServers.json`](./mcpServers.json) and [`agentbus.mcp.json`](./agentbus.mcp.json).

Self-hosted teams: replace the host with **your** agentbus base URL + `/mcp`.
