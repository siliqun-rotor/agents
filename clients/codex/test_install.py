"""python3 platform/agents/codex/test_install.py"""
import tempfile
import tomllib
import unittest
from pathlib import Path

import install


class CodexInstall(unittest.TestCase):
    def test_oauth_mcp_without_token_file(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / '.codex'
            home.mkdir()
            (home / 'config.toml').write_text('model = "m"\n')
            changed = install.install(home, 'https://bus.example', None, '/opt/node/bin/node')
            self.assertTrue(any('OAuth' in c or 'mcp_servers' in c for c in changed))
            cfg = tomllib.loads((home / 'config.toml').read_text())
            self.assertEqual(cfg['mcp_servers']['agentbus']['url'], 'https://bus.example/mcp')
            self.assertNotIn('bearer_token_env_var', cfg['mcp_servers']['agentbus'])
            self.assertNotIn('notify', cfg)
            self.assertIn('OAuth', (home / 'skills/agentbus/SKILL.md').read_text())

    def test_strips_bearer_env_var_to_oauth(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            (home / 'config.toml').write_text(
                '[mcp_servers.agentbus]\n'
                'url = "https://bus.example/mcp"\n'
                'bearer_token_env_var = "AGENTBUS_TOKEN"\n'
            )
            install.install(home, 'https://bus.example', None, '/opt/node/bin/node')
            agentbus = tomllib.loads((home / 'config.toml').read_text())['mcp_servers']['agentbus']
            self.assertEqual(agentbus, {'url': 'https://bus.example/mcp'})

    def test_optional_notify_with_token_file_chains(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / '.codex'
            home.mkdir()
            tok = Path(d) / 'codex.token'
            tok.write_text('secret-token-value')
            (home / 'config.toml').write_text(
                'notify = [\n    "/apps/Client",\n    "turn-ended",\n]\nmodel = "m"\n'
            )
            install.install(home, 'https://bus.example', tok, '/opt/node/bin/node')
            cfg = (home / 'config.toml').read_text()
            notify = tomllib.loads(cfg)['notify']
            self.assertEqual(notify[0], '/opt/node/bin/node')
            self.assertTrue(notify[1].endswith('agentbus/status.mjs'))
            self.assertEqual(notify[-4:], ['--then', '/apps/Client', 'turn-ended', '--'])
            self.assertNotIn('secret-token-value', cfg)
            self.assertEqual(
                tomllib.loads(cfg)['mcp_servers']['agentbus']['url'],
                'https://bus.example/mcp',
            )


if __name__ == '__main__':
    unittest.main()
