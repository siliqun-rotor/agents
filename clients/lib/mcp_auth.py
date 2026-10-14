"""Shared helpers for agentbus client installers.

Default auth is **OAuth 2.1** on the remote `/mcp` endpoint (SPEC §14): the client
discovers metadata from a 401 `WWW-Authenticate`, the agent picks a name, the
owner runs `agentbus approve <name>`, and the client stores the access token.
No pre-issued token file is required for MCP.

Optional `--auth bearer` writes a static Authorization header from a token file
for labs that already have one. Never leave Claude-style `${user_config.*}`
placeholders unsubstituted (Cursor does not expand them).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PLACEHOLDER = re.compile(r'\$\{[^}]+\}')


def read_token(token_file: Path) -> str:
    if not token_file.is_file():
        raise SystemExit(f'refused: no token file at {token_file}')
    tok = token_file.read_text().strip()
    if not tok:
        raise SystemExit(f'refused: token file {token_file} is empty')
    if PLACEHOLDER.search(tok):
        raise SystemExit('refused: token looks like an unsubstituted placeholder')
    return tok


def mcp_url(bus: str) -> str:
    bus = bus.strip().rstrip('/')
    if not bus:
        raise SystemExit('refused: --bus is required (no default; do not land strangers on our bus)')
    if PLACEHOLDER.search(bus):
        raise SystemExit('refused: bus URL looks like an unsubstituted placeholder')
    if not re.match(r'^https?://', bus):
        raise SystemExit('refused: bus URL must start with http:// or https://')
    return f'{bus}/mcp'


def oauth_entry(url: str, *, style: str = 'cursor') -> dict:
    """MCP server entry that triggers the client's OAuth login (no static bearer)."""
    if style == 'antigravity':
        return {'disabled': False, 'serverUrl': url}
    if style == 'codex':
        return {'url': url}
    # Cursor / generic mcpServers
    return {'url': url}


def bearer_entry(url: str, token: str, *, style: str = 'cursor') -> dict:
    headers = {'Authorization': f'Bearer {token}'}
    if style == 'antigravity':
        return {'disabled': False, 'serverUrl': url, 'headers': headers}
    if style == 'codex':
        # Prefer env var so the token never lands in config.toml.
        return {'url': url, 'bearer_token_env_var': 'AGENTBUS_TOKEN'}
    return {'url': url, 'headers': headers}


def merge_mcp_servers(path: Path, name: str, entry: dict, *, servers_key: str = 'mcpServers') -> bool:
    """Write or update one MCP server entry. Returns True if the file changed."""
    existing: dict = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text() or '{}')
        except json.JSONDecodeError as e:
            raise SystemExit(f'refused: {path} is not valid JSON ({e})') from e
    servers = dict(existing.get(servers_key) or {})
    before = servers.get(name)
    if before == entry:
        return False
    servers[name] = entry
    out = {servers_key: servers}
    for k, v in existing.items():
        if k != servers_key:
            out[k] = v
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=2) + '\n'
    path.write_text(text)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    raw = path.read_text()
    if PLACEHOLDER.search(raw):
        raise SystemExit(f'refused: wrote unsubstituted placeholder into {path}')
    return True


def assert_no_placeholders(path: Path) -> None:
    if path.exists() and PLACEHOLDER.search(path.read_text()):
        raise SystemExit(f'refused: {path} still contains ${{...}} placeholders')


def assert_oauth_entry(entry: dict) -> None:
    """OAuth entries must not carry a static Authorization header."""
    headers = entry.get('headers') or {}
    auth = str(headers.get('Authorization') or headers.get('authorization') or '')
    if auth.lower().startswith('bearer '):
        raise SystemExit('refused: OAuth MCP entry must not include a Bearer header')
