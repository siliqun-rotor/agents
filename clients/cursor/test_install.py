"""python3 platform/agents/cursor/test_install.py"""
import json
import tempfile
import unittest
from pathlib import Path

import install


class CursorInstall(unittest.TestCase):
    def test_oauth_writes_url_without_bearer(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / '.cursor'
            home.mkdir()
            (home / 'mcp.json').write_text(json.dumps({
                'mcpServers': {
                    'agentbus': {
                        'url': 'https://bus.example/mcp',
                        'headers': {'Authorization': 'Bearer old-static'},
                    },
                    'other': {'url': 'https://example/mcp'},
                }
            }))
            changed = install.install(home, 'https://bus.example', auth='oauth')
            self.assertTrue(changed)
            data = json.loads((home / 'mcp.json').read_text())
            self.assertEqual(data['mcpServers']['agentbus'], {'url': 'https://bus.example/mcp'})
            self.assertIn('other', data['mcpServers'])
            self.assertTrue((home / 'hooks/agentbus-context.mjs').is_file())
            self.assertTrue((home / 'hooks.json').is_file())
            raw = (home / 'mcp.json').read_text()
            self.assertNotIn('Bearer', raw)
            self.assertNotIn('${', raw)

    def test_bearer_optional_path(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            tok = Path(d) / 't'
            tok.write_text('tok')
            install.install(home, 'https://bus.example', auth='bearer', token_file=tok)
            entry = json.loads((home / 'mcp.json').read_text())['mcpServers']['agentbus']
            self.assertEqual(entry['headers']['Authorization'], 'Bearer tok')


if __name__ == '__main__':
    unittest.main()
