"""Disposable offline synthetic exercise; no native loading or acceptance proof."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def main():
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        consumer = work / 'consumer'
        consumer.mkdir()
        (consumer / '.sdlc').mkdir()
        config = consumer / '.sdlc/config.json'
        config.write_text('{"delivery_profile":"artifact","validation":["synthetic-check"]}')
        # Identity belongs only to this synthetic fixture, never the operator.
        git_env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                       GIT_AUTHOR_NAME='Synthetic Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                       GIT_COMMITTER_NAME='Synthetic Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')

        def git(*args):
            return subprocess.run(['git', '-C', str(consumer), *args], env=git_env,
                                  capture_output=True, text=True, check=True).stdout.strip()

        git('init', '-q')
        git('add', '.sdlc/config.json')
        git('commit', '-qm', 'Synthetic fixture')
        git('remote', 'add', 'origin', 'https://github.com/example/project.git')
        head = git('rev-parse', 'HEAD')
        contract = dict(schema=1, run='synthetic', attempt='one', generation=1,
                        repository='example/project', issue=1, base=head, head=head,
                        spec='1' * 64, config=hashlib.sha256(config.read_bytes()).hexdigest(),
                        package='2' * 64, guide='3' * 40, harness='4' * 64,
                        role='author', process='synthetic-author', session='synthetic-session',
                        scope=['example.txt'], constraints=['offline synthetic only'],
                        commands=['synthetic-check'], effects=['proposal'], limits=['fixture'],
                        capabilities=[], stop=None, tools=[dict(path=sys.executable,
                        sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest())])
        result = dict(schema=2, contract=hashlib.sha256(canonical(contract)).hexdigest(),
                      role=contract['role'], process=contract['process'], session=contract['session'],
                      author_process='synthetic-author', author_session='synthetic-session',
                      outcome='passed', commands=[dict(command='synthetic-check', status='executed', exit=0)],
                      evidence=[dict(locator='synthetic-only', sha256='5' * 64)], findings=[],
                      next_action='independent-review-required', limits=contract['limits'], effects=contract['effects'])
        resources = dict(contract=contract, result=result,
                         observations={k: contract[k] for k in ('spec', 'package', 'guide', 'harness')})
        for name, value in resources.items():
            (work / (name + '.json')).write_bytes(canonical(value))

        def helper(*args):
            actual = subprocess.run([sys.executable, str(PACKAGE / 'scripts/shipshape.py'), *map(str, args)],
                                    capture_output=True, text=True)
            if actual.returncode:
                raise RuntimeError(actual.stdout + actual.stderr)
            return json.loads(actual.stdout)

        helper('contract', 'check', '--repo-root', consumer, '--contract', work / 'contract.json',
               '--observations', work / 'observations.json')
        helper('result', 'check', '--contract', work / 'contract.json', '--result', work / 'result.json')
        for expected in ('persisted', 'replayed'):
            actual = helper('handoff', 'write', '--repo-root', consumer, '--contract', work / 'contract.json',
                            '--result', work / 'result.json', '--handoff-root', work.resolve(), '--output', 'handoff')
            if actual['decision'] != expected:
                raise RuntimeError('unexpected handoff decision')
    print(json.dumps({'synthetic': 'passed', 'acceptance': 'pending'}))


if __name__ == '__main__':
    main()
