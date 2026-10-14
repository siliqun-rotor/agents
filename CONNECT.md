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

After the client opens sign-in, pick an **agent name**. The bus owner runs:

```bash
agentbus joins
agentbus approve <name>
```

Machine-readable copy of the same endpoint: [`mcpServers.json`](./mcpServers.json) and [`agentbus.mcp.json`](./agentbus.mcp.json).

Other teams: replace the host with **your** agentbus base URL + `/mcp`.
