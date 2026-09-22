"""Deterministic adapter checks; native model acceptance is separate."""
import importlib.machinery
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('writing_build', str(ROOT / 'bin/generate-writing'))
spec = importlib.util.spec_from_loader(loader.name, loader)
build = importlib.util.module_from_spec(spec)
loader.exec_module(build)


@unittest.skipUnless(shutil.which('node'), 'Node is required to exercise the native writing adapters')
class WritingAdapters(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='writing fixture ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / 'installed package'
        self.package.mkdir()

    def generate(self, target):
        build.generate(target, self.package)

    def run_hook(self, event, input_text=''):
        return subprocess.run(['node', str(self.package / 'runtime/hook.mjs'), event],
                              input=input_text, text=True, capture_output=True,
                              cwd=self.root, timeout=10)

    def test_hook_reads_only_own_core_from_install_with_spaces(self):
        self.generate('codex')
        # Private-looking input is synthetic. It must neither be opened nor echoed.
        supplied = json.dumps({'hook_event_name': 'SessionStart', 'source': 'compact',
                               'transcript_path': '/nonexistent/synthetic-transcript',
                               'message': 'SYNTHETIC_PRIVATE_SENTINEL'})
        before = build.files(self.root)
        for event in ['SessionStart', 'SubagentStart']:
            result = self.run_hook(event, supplied)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)['hookSpecificOutput']
            self.assertEqual(output['hookEventName'], event)
            self.assertEqual(output['additionalContext'], (build.SOURCE / 'core.md').read_text())
            self.assertNotIn('SYNTHETIC_PRIVATE_SENTINEL', result.stdout)
        self.assertEqual(before, build.files(self.root))

    def test_unknown_event_fails_without_injecting(self):
        self.generate('claude-code')
        result = self.run_hook('Stop')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_missing_resource_is_visible_failure(self):
        self.generate('codex')
        (self.package / 'skills/writing-for-humans/references/core.md').unlink()
        result = self.run_hook('SessionStart')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_hooks_are_bounded_and_no_style_or_tool_interception(self):
        for target in ['claude-code', 'codex']:
            with tempfile.TemporaryDirectory() as tmp:
                package = Path(tmp)
                build.generate(target, package)
                hooks = json.loads((package / 'hooks/hooks.json').read_text())['hooks']
                self.assertEqual(set(hooks), {'SessionStart', 'SubagentStart'} |
                                 ({'UserPromptSubmit'} if target == 'claude-code' else set()))
                for event, groups in hooks.items():
                    handler = groups[0]['hooks'][0]
                    self.assertLessEqual(handler['timeout'], 5)
                    self.assertEqual(handler['type'], 'command')
                    self.assertTrue(handler['command'].endswith(event))
                self.assertFalse((package / 'output-styles').exists())

    def test_pi_preserves_other_guidance_and_does_not_accumulate(self):
        self.generate('pi')
        script = self.root / 'exercise.mjs'
        script.write_text('''import plugin from './installed package/runtime/pi.mjs';
let callback;
plugin({on(event, handler) { if(event !== 'before_agent_start') throw Error(event); callback=handler; }});
const base='Existing user style and earlier extension instructions.';
const first=await callback({systemPrompt:base});
const duplicate=await callback({systemPrompt:first.systemPrompt});
const later=await callback({systemPrompt:base});
console.log(JSON.stringify({base,first,duplicate,later}));
''')
        result = subprocess.run(['node', str(script)], capture_output=True, text=True, check=True)
        values = json.loads(result.stdout)
        self.assertTrue(values['first']['systemPrompt'].startswith(values['base'] + '\n\n'))
        self.assertEqual(values['duplicate'], {})
        self.assertEqual(values['first'], values['later'])

    def test_installed_skill_references_resolve_inside_package(self):
        self.generate('codex')
        for markdown in (self.package / 'skills').rglob('*.md'):
            for link in re.findall(r'\]\(([^)]+)\)', markdown.read_text()):
                if '://' in link or link.startswith('#'):
                    continue
                resolved = (markdown.parent / link.split('#')[0]).resolve()
                self.assertTrue(resolved.is_relative_to(self.package.resolve()), link)
                self.assertTrue(resolved.is_file(), str(resolved))

    def test_each_package_is_self_contained_and_reproducible(self):
        for target in build.TARGETS:
            with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
                build.generate(target, Path(a)); build.generate(target, Path(b))
                self.assertEqual(build.files(Path(a)), build.files(Path(b)))
                for file in Path(a).rglob('*'):
                    self.assertFalse(file.is_symlink())
                self.assertEqual((Path(a) / 'skills/writing-for-humans/references/core.md').read_bytes(),
                                 (build.SOURCE / 'core.md').read_bytes())


if __name__ == '__main__':
    unittest.main()
