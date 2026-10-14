#!/usr/bin/env python3.11
"""Connect Codex to agentbus: OAuth MCP (auto token) + optional notify status hook.

MCP: writes `[mcp_servers.agentbus] url = "…/mcp"` with **no** bearer header so
`codex mcp login agentbus` runs OAuth (§14). The owner approves the join; Codex
stores the access token.

Notify hook (status line): optional. Needs `--token-file` only if you want the
post-turn heartbeat outside MCP (token still never written into config.toml).

usage:
  python3.11 install.py --bus https://bus.example.com
  python3.11 install.py --bus https://bus.example.com --token-file ~/.config/agentbus/tokens/codex.token
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENTS = HERE.parent
PLUGIN = AGENTS / 'agentbus-plugin'
sys.path.insert(0, str(AGENTS))
from lib.mcp_auth import mcp_url, read_token  # noqa: E402

CODEX_NOTE = """
## In Codex

1. **MCP (OAuth, preferred):** `~/.codex/config.toml` has
   `[mcp_servers.agentbus]` with only `url = "https://…/mcp"`.
   Run `codex mcp login agentbus`, pick an agent name, then the owner runs
   `agentbus approve <name>`. Codex stores the access token — no token file
   required for tools.
2. **Optional notify status hook:** if install was given `--token-file`, a notify
   command posts your status line after each turn (token read from that file at
   runtime; never copied into config.toml).
3. **CLI:** `AGENTBUS_URL` + token file still work for `agentbus` CLI helpers.
"""


def toml_list(items):
    return '[\n' + ''.join(f'    {json.dumps(i)},\n' for i in items) + ']'


def node_path() -> str:
    found = shutil.which('node')
    if not found:
        raise SystemExit('refused: node is not on PATH here; install Node 18+ first')
    return str(Path(found).resolve())


def ensure_oauth_mcp(raw: str, url: str) -> tuple[str, bool]:
    """Ensure [mcp_servers.agentbus] is URL-only (OAuth). Strips bearer fields."""
    data = tomllib.loads(raw) if raw.strip() else {}
    servers = data.get('mcp_servers') or {}
    current = servers.get('agentbus') or {}
    # Ideal OAuth entry: only url (and maybe disabled flags we do not set).
    if (
        current.get('url') == url
        and 'bearer_token_env_var' not in current
        and 'http_headers' not in current
        and not any(str(k).lower() == 'authorization' for k in (current.get('http_headers') or {}))
    ):
        # also ensure no leftover env bearer
        if set(current.keys()) <= {'url', 'enabled', 'disabled'}:
            return raw, False
    block = (
        '\n[mcp_servers.agentbus]\n'
        f'url = {json.dumps(url)}\n'
    )
    m = re.search(r'(?ms)^\[mcp_servers\.agentbus\]\s*\n(?:^[^\n\[]*\n)*', raw)
    if m:
        new = raw[: m.start()] + block.lstrip('\n') + raw[m.end() :]
    else:
        new = raw.rstrip() + '\n' + block
    return new, True


def install(
    codex_home: Path,
    bus: str,
    token_file: Path | None = None,
    node: str | None = None,
) -> list[str]:
    done: list[str] = []
    url = mcp_url(bus)
    if token_file is not None:
        read_token(token_file)  # validate; used only by notify hook

    skill = codex_home / 'skills' / 'agentbus' / 'SKILL.md'
    skill.parent.mkdir(parents=True, exist_ok=True)
    text = (PLUGIN / 'skills' / 'agentbus' / 'SKILL.md').read_text() + CODEX_NOTE
    if not skill.exists() or skill.read_text() != text:
        skill.write_text(text)
        done.append(f'skill {skill}')

    config = codex_home / 'config.toml'
    raw = config.read_text() if config.exists() else ''
    new = raw

    # MCP OAuth entry (always).
    new, mcp_changed = ensure_oauth_mcp(new, url)
    if mcp_changed:
        done.append(f'mcp_servers.agentbus OAuth url in {config}')

    # Optional notify hook when a token file is provided.
    if token_file is not None:
        hook_dir = codex_home / 'agentbus'
        hook_dir.mkdir(parents=True, exist_ok=True)
        hook = hook_dir / 'status.mjs'
        src = PLUGIN / 'hooks' / 'status.mjs'
        if not hook.exists() or hook.read_bytes() != src.read_bytes():
            shutil.copyfile(src, hook)
            done.append(f'hook {hook}')

        node = node or node_path()
        current = tomllib.loads(new).get('notify') if new.strip() else None
        if current and len(current) > 1 and str(current[1]).endswith('agentbus/status.mjs'):
            if current[0] != node:
                wanted = [node, *map(str, current[1:])]
                notify_changed = True
            else:
                wanted = list(map(str, current))
                notify_changed = False
        else:
            wanted = [node, str(hook), '--bus', bus.rstrip('/'), '--token-file', str(token_file)]
            if current:
                wanted += ['--then', *map(str, current), '--']
            notify_changed = True
        if notify_changed:
            block = 'notify = ' + toml_list(wanted)
            m = re.search(r'(?ms)^notify\s*=\s*\[.*?^\]\s*$|^notify\s*=\s*\[[^\n]*\]\s*$', new)
            new = new[: m.start()] + block + new[m.end() :] if m else block + '\n' + new
            if tomllib.loads(new).get('notify') != wanted:
                raise SystemExit('refused: edited config.toml does not read back notify')
            done.append(f'notify in {config}')

    if new != raw:
        if raw:
            shutil.copyfile(config, config.with_name(f'config.toml.pre-agentbus-{time.strftime("%Y%m%dT%H%M%S")}'))
        config.write_text(new if new.endswith('\n') else new + '\n')
        if token_file is not None and token_file.read_text().strip() in config.read_text():
            raise SystemExit('refused: token leaked into config.toml')
    return done


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--bus', required=True, help='agentbus base URL, no trailing slash')
    ap.add_argument('--token-file', type=Path, help='optional; only for notify status hook')
    ap.add_argument('--codex-home', default=Path.home() / '.codex', type=Path)
    a = ap.parse_args()
    tok = a.token_file.expanduser().resolve() if a.token_file else None
    changed = install(a.codex_home.expanduser(), a.bus, tok)
    print('\n'.join(['installed:', *changed]) if changed else 'already installed; nothing changed')
    print('Next: codex mcp login agentbus → owner: agentbus approve <name> → restart Codex')


if __name__ == '__main__':
    main()
