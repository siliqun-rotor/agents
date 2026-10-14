#!/usr/bin/env python3
"""Connect Antigravity (agy) to agentbus over OAuth (auto agent token).

Writes a resolved `serverUrl` into `~/.gemini/config/mcp_config.json` **without**
an Authorization header so Antigravity's MCP OAuth login can create the agent
token after the owner approves.

usage:
  python3 install.py --bus https://bus.example.com
  python3 install.py --bus https://bus.example.com --auth bearer --token-file ~/.config/agentbus/tokens/antigravity.token
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENTS = HERE.parent
PLUGIN = AGENTS / 'agentbus-plugin'
sys.path.insert(0, str(AGENTS))
from lib.mcp_auth import (  # noqa: E402
    assert_no_placeholders,
    assert_oauth_entry,
    bearer_entry,
    mcp_url,
    merge_mcp_servers,
    oauth_entry,
    read_token,
)

AGY_NOTE = """
## In Antigravity

1. Install writes `~/.gemini/config/mcp_config.json` with `serverUrl` only (OAuth).
2. In Antigravity / `agy`: open MCP servers → authenticate **agentbus**.
3. Choose an agent name; owner runs `agentbus approve <name>`.
4. Tools appear after approval. Optional `--auth bearer --token-file` is for
   static tokens only.
"""


def install(
    gemini_home: Path,
    bus: str,
    *,
    auth: str = 'oauth',
    token_file: Path | None = None,
    install_plugin: bool = True,
) -> list[str]:
    done: list[str] = []
    url = mcp_url(bus)
    if auth == 'oauth':
        entry = oauth_entry(url, style='antigravity')
        assert_oauth_entry(entry)
    elif auth == 'bearer':
        if token_file is None:
            raise SystemExit('refused: --auth bearer requires --token-file')
        entry = bearer_entry(url, read_token(token_file), style='antigravity')
    else:
        raise SystemExit("refused: --auth must be 'oauth' or 'bearer'")

    mcp_path = gemini_home / 'config' / 'mcp_config.json'
    if merge_mcp_servers(mcp_path, 'agentbus', entry):
        done.append(f'mcp {mcp_path} ({auth})')
    assert_no_placeholders(mcp_path)

    skill_text = (PLUGIN / 'skills' / 'agentbus' / 'SKILL.md').read_text() + AGY_NOTE
    skill = gemini_home / 'antigravity' / 'skills' / 'agentbus' / 'SKILL.md'
    skill.parent.mkdir(parents=True, exist_ok=True)
    if not skill.exists() or skill.read_text() != skill_text:
        skill.write_text(skill_text)
        done.append(f'skill {skill}')

    if install_plugin:
        plug = gemini_home / 'antigravity' / 'plugins' / 'agentbus'
        plug.mkdir(parents=True, exist_ok=True)
        manifest = {'name': 'agentbus'}
        mf = plug / 'plugin.json'
        if not mf.exists() or json.loads(mf.read_text()) != manifest:
            mf.write_text(json.dumps(manifest, indent=2) + '\n')
            done.append(f'plugin manifest {mf}')
        pmc = plug / 'mcp_config.json'
        # Plugin MCP: URL only for OAuth so the IDE can complete login.
        wanted = {'mcpServers': {'agentbus': entry}}
        text = json.dumps(wanted, indent=2) + '\n'
        if not pmc.exists() or pmc.read_text() != text:
            pmc.write_text(text)
            pmc.chmod(0o600)
            done.append(f'plugin mcp {pmc}')
        assert_no_placeholders(pmc)
        rules = plug / 'rules' / 'AGENTS.md'
        rules.parent.mkdir(parents=True, exist_ok=True)
        rule = (
            '# agentbus\n\n'
            'Authenticate the agentbus MCP server with OAuth if prompted. '
            'Use inbox/tasks tools after the owner approves your join.\n'
        )
        if not rules.exists() or rules.read_text() != rule:
            rules.write_text(rule)
            done.append(f'plugin rule {rules}')
        pskill = plug / 'skills' / 'agentbus' / 'SKILL.md'
        pskill.parent.mkdir(parents=True, exist_ok=True)
        if not pskill.exists() or pskill.read_text() != skill_text:
            pskill.write_text(skill_text)
            done.append(f'plugin skill {pskill}')

    return done


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--bus', required=True)
    ap.add_argument('--auth', choices=('oauth', 'bearer'), default='oauth')
    ap.add_argument('--token-file', type=Path)
    ap.add_argument('--gemini-home', default=Path.home() / '.gemini', type=Path)
    ap.add_argument('--no-plugin', action='store_true')
    a = ap.parse_args()
    tok = a.token_file.expanduser().resolve() if a.token_file else None
    changed = install(
        a.gemini_home.expanduser(),
        a.bus,
        auth=a.auth,
        token_file=tok,
        install_plugin=not a.no_plugin,
    )
    print('\n'.join(['installed:', *changed]) if changed else 'already installed; nothing changed')
    if a.auth == 'oauth':
        print('Next: authenticate agentbus in Antigravity → owner: agentbus approve <name>')
    else:
        print('Reload Antigravity MCP servers to use the bearer entry.')


if __name__ == '__main__':
    main()
