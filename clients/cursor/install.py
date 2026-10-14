#!/usr/bin/env python3
"""Connect Cursor to agentbus over OAuth (auto agent token).

Cursor does not interpolate Claude `${user_config.*}` placeholders, so this
writes a **resolved** `url` into `~/.cursor/mcp.json` with **no** Authorization
header. Cursor's MCP OAuth flow then: 401 → discover metadata → agent names
itself → owner `agentbus approve <name>` → client stores the access token.

Optional `--auth bearer --token-file …` keeps the old static-header path for
labs that already have a token.

usage:
  python3 install.py --bus https://bus.example.com
  python3 install.py --bus https://bus.example.com --auth bearer --token-file ~/.config/agentbus/tokens/cursor.token
"""
from __future__ import annotations

import argparse
import json
import shutil
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

CURSOR_NOTE = """
## In Cursor

1. Install writes `~/.cursor/mcp.json` with a resolved `url` (no bearer header).
2. Open Cursor → MCP → agentbus → **authenticate / login** (OAuth). Pick an agent name.
3. Owner runs `agentbus joins` then `agentbus approve <name>`.
4. Cursor stores the access token; tools work. Do **not** paste
   `${user_config.bus_url}` / `${user_config.bus_token}` into Cursor — those
   placeholders are not substituted and the connection fails.
5. Hooks under `~/.cursor/hooks/` are optional helpers (unread context / stop
   heartbeat). They stay silent until `AGENTBUS_URL` and a token file or
   `AGENTBUS_TOKEN` exist; MCP OAuth alone is enough for tools.
"""


def install(cursor_home: Path, bus: str, *, auth: str = 'oauth', token_file: Path | None = None) -> list[str]:
    done: list[str] = []
    url = mcp_url(bus)
    if auth == 'oauth':
        entry = oauth_entry(url, style='cursor')
        assert_oauth_entry(entry)
    elif auth == 'bearer':
        if token_file is None:
            raise SystemExit('refused: --auth bearer requires --token-file')
        entry = bearer_entry(url, read_token(token_file), style='cursor')
    else:
        raise SystemExit("refused: --auth must be 'oauth' or 'bearer'")

    mcp_path = cursor_home / 'mcp.json'
    if merge_mcp_servers(mcp_path, 'agentbus', entry):
        done.append(f'mcp {mcp_path} ({auth})')
    assert_no_placeholders(mcp_path)

    hooks_src = HERE / 'hooks'
    hooks_dst = cursor_home / 'hooks'
    hooks_dst.mkdir(parents=True, exist_ok=True)
    for name in ('agentbus-context.mjs', 'agentbus-stop.mjs'):
        src = hooks_src / name
        dst = hooks_dst / name
        if src.is_file() and (not dst.exists() or dst.read_bytes() != src.read_bytes()):
            shutil.copyfile(src, dst)
            dst.chmod(0o755)
            done.append(f'hook {dst}')

    hooks_json = cursor_home / 'hooks.json'
    node = shutil.which('node') or '/usr/bin/node'
    wanted_hooks = {
        'sessionStart': [{
            'command': f'{node} ./hooks/agentbus-context.mjs',
            'matcher': 'startup|resume|clear|compact',
            'timeout': 8,
        }],
        'beforeSubmitPrompt': [{
            'command': f'{node} ./hooks/agentbus-context.mjs',
            'timeout': 8,
        }],
        'stop': [{
            'command': f'{node} ./hooks/agentbus-stop.mjs',
            'timeout': 8,
            'loop_limit': 8,
        }],
    }
    existing: dict = {}
    if hooks_json.exists():
        try:
            existing = json.loads(hooks_json.read_text() or '{}')
        except json.JSONDecodeError:
            existing = {}
    hooks = dict(existing.get('hooks') or {})
    for k, v in wanted_hooks.items():
        hooks[k] = v
    new = {'version': 1, 'hooks': hooks}
    for k, v in existing.items():
        if k not in ('version', 'hooks'):
            new[k] = v
    text = json.dumps(new, indent=2) + '\n'
    if not hooks_json.exists() or hooks_json.read_text() != text:
        hooks_json.write_text(text)
        done.append(f'hooks.json {hooks_json}')

    # Point hooks at this bus without embedding a token.
    env_hint = cursor_home / 'agentbus.env'
    env_text = f'AGENTBUS_URL={bus.rstrip("/")}\n'
    if not env_hint.exists() or env_hint.read_text() != env_text:
        env_hint.write_text(env_text)
        done.append(f'env hint {env_hint}')

    skill_text = (PLUGIN / 'skills' / 'agentbus' / 'SKILL.md').read_text() + CURSOR_NOTE
    for target in (
        cursor_home / 'skills-cursor' / 'agentbus' / 'SKILL.md',
        cursor_home / 'skills' / 'agentbus' / 'SKILL.md',
    ):
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_text() != skill_text:
            target.write_text(skill_text)
            done.append(f'skill {target}')
            break

    return done


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--bus', required=True, help='agentbus base URL, no trailing slash')
    ap.add_argument('--auth', choices=('oauth', 'bearer'), default='oauth')
    ap.add_argument('--token-file', type=Path, help='only for --auth bearer')
    ap.add_argument('--cursor-home', default=Path.home() / '.cursor', type=Path)
    a = ap.parse_args()
    tok = a.token_file.expanduser().resolve() if a.token_file else None
    changed = install(a.cursor_home.expanduser(), a.bus, auth=a.auth, token_file=tok)
    print('\n'.join(['installed:', *changed]) if changed else 'already installed; nothing changed')
    if a.auth == 'oauth':
        print('Next: reload Cursor MCP → authenticate agentbus → owner runs: agentbus approve <name>')
    else:
        print('Reload Cursor MCP servers to use the bearer entry.')


if __name__ == '__main__':
    main()
