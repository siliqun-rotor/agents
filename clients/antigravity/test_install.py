"""python3 platform/agents/antigravity/test_install.py"""
import json
import tempfile
import unittest
from pathlib import Path

import install


class AntigravityInstall(unittest.TestCase):
    def test_oauth_server_url_without_headers(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / '.gemini'
            (home / 'config').mkdir(parents=True)
            (home / 'config' / 'mcp_config.json').write_text(json.dumps({
                'mcpServers': {
                    'supabase': {'serverUrl': 'https://mcp.supabase.com/mcp'},
                    'agentbus': {
                        'serverUrl': 'https://old/mcp',
                        'headers': {'Authorization': 'Bearer x'},
                    },
                }
            }))
            changed = install.install(home, 'https://bus.example', auth='oauth')
            self.assertTrue(changed)
            data = json.loads((home / 'config' / 'mcp_config.json').read_text())
            self.assertEqual(
                data['mcpServers']['agentbus'],
                {'disabled': False, 'serverUrl': 'https://bus.example/mcp'},
            )
            self.assertIn('supabase', data['mcpServers'])
            self.assertNotIn('Bearer', (home / 'config' / 'mcp_config.json').read_text())
            self.assertTrue((home / 'antigravity/plugins/agentbus/plugin.json').is_file())


if __name__ == '__main__':
    unittest.main()
