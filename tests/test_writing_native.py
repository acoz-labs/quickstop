"""Native discovery regression; no model credentials or trust bypass required."""
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import tempfile
import time
import unittest


@unittest.skipUnless(shutil.which('codex'), 'Native Codex CLI is not installed')
class CodexWritingDiscovery(unittest.TestCase):
    def test_installed_candidate_exposes_untrusted_lifecycle_hooks(self):
        with tempfile.TemporaryDirectory(prefix='writing-native-') as tmp:
            root = Path(tmp)
            home = root / 'home'; home.mkdir()
            work = root / 'work'; work.mkdir()
            market = root / 'market'
            metadata = market / '.agents/plugins'; metadata.mkdir(parents=True)
            package = market / 'plugins/writing-for-humans'
            source = Path(__file__).resolve().parents[1] / 'plugins/codex/writing-for-humans'
            shutil.copytree(source, package)
            (metadata / 'marketplace.json').write_text(json.dumps({
                'name': 'writing-fixture', 'interface': {'displayName': 'Synthetic fixture'},
                'plugins': [{'name': 'writing-for-humans',
                             'source': {'source': 'local', 'path': './plugins/writing-for-humans'},
                             'category': 'Productivity',
                             'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'}}]}))
            env = os.environ.copy(); env['CODEX_HOME'] = str(home)
            for args in [['marketplace', 'add', str(market)], ['add', 'writing-for-humans@writing-fixture']]:
                result = subprocess.run(['codex', 'plugin', *args], cwd=work, env=env,
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
            server = subprocess.Popen(['codex', 'app-server', '--stdio'], cwd=work, env=env,
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True)
            try:
                for request in [
                    {'id': 1, 'method': 'initialize', 'params': {
                        'clientInfo': {'name': 'writing-discovery-fixture', 'version': '1.0'},
                        'capabilities': {'experimentalApi': True}}},
                    {'method': 'initialized', 'params': {}},
                    {'id': 2, 'method': 'hooks/list', 'params': {'cwds': [str(work)]}},
                ]:
                    server.stdin.write(json.dumps(request) + '\n'); server.stdin.flush()
                response = None
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if select.select([server.stdout], [], [], 0.5)[0]:
                        line = server.stdout.readline()
                        if not line:
                            break
                        item = json.loads(line)
                        if item.get('id') == 2:
                            response = item
                            break
                self.assertIsNotNone(response, 'hooks/list returned no response')
                self.assertNotIn('error', response)
                data = response['result']['data'][0]
                self.assertEqual(data['errors'], [])
                hooks = data['hooks']
                self.assertEqual({h['eventName'] for h in hooks}, {'sessionStart', 'subagentStart'})
                self.assertEqual(len(hooks), 2)
                for hook in hooks:
                    self.assertEqual(hook['source'], 'plugin')
                    self.assertTrue(hook['enabled'])
                    self.assertEqual(hook['trustStatus'], 'untrusted')
                    self.assertIn('/runtime/hook.mjs', hook['command'])
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill(); server.wait(timeout=5)
                for stream in (server.stdin, server.stdout, server.stderr):
                    stream.close()


if __name__ == '__main__':
    unittest.main()
