import importlib.machinery
import importlib.util
import json
import base64
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('sdlc', str(Path(__file__).resolve().parents[1] / 'bin/sdlc'))
spec = importlib.util.spec_from_loader(loader.name, loader)
sdlc = importlib.util.module_from_spec(spec)
loader.exec_module(sdlc)

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.pr = {'user': {'login': 'Builder'}, 'head': {'sha': 'a'*40}}
    def review(self, actor='Reviewer', head='a'*40, state='APPROVED', id=1):
        return {'id': id, 'user': {'login': actor}, 'commit_id': head, 'state': state, 'submitted_at': str(id)}
    def test_rejects_self_stale_and_unauthorized_approval(self):
        for review, permissions in [(self.review('Builder'), {'builder':'admin'}),
                                    (self.review(head='b'*40), {'reviewer':'write'}),
                                    (self.review(), {'reviewer':'read'})]:
            with self.subTest(review=review), self.assertRaises(sdlc.Failure):
                sdlc.approval(self.pr, [review], permissions)
    def test_change_request_requires_resolution(self):
        reviews=[self.review(),self.review(state='CHANGES_REQUESTED',id=2)]
        with self.assertRaises(sdlc.Failure):sdlc.approval(self.pr,reviews,{'reviewer':'write'})
        sdlc.approval(self.pr,reviews+[self.review(id=3)],{'reviewer':'write'})
    def test_dismissal_revokes_approval(self):
        with self.assertRaises(sdlc.Failure):
            sdlc.approval(self.pr,[self.review(),self.review(state='DISMISSED',id=2)],{'reviewer':'write'})
    def test_missing_pending_failed_and_skipped_checks_fail(self):
        for state in ['pending','failure','skipped',None]:
            with self.subTest(state=state), self.assertRaises(sdlc.Failure):
                sdlc.checks_pass(['ci'],[] if state is None else [{'id':1,'name':'ci','status':'completed','conclusion':state}],[])
    def test_latest_check_overrides_old_success(self):
        checks=[{'id':i,'name':'ci','status':'completed','conclusion':c} for i,c in [(1,'success'),(2,'failure')]]
        with self.assertRaises(sdlc.Failure):sdlc.checks_pass(['ci'],checks,[])
        checks.append({'id':3,'name':'ci','status':'completed','conclusion':'success'})
        sdlc.checks_pass(['ci'],checks,[])
    def test_status_failure_cannot_be_hidden_by_check(self):
        with self.assertRaises(sdlc.Failure):
            sdlc.checks_pass(['ci'],[{'id':1,'name':'ci','status':'completed','conclusion':'success'}],
                            [{'id':2,'context':'ci','state':'failure'}])
    def test_wrong_actor_refused_before_pr_read(self):
        with patch.object(sdlc,'gh',return_value={'login':'Unexpected'}) as api:
            with self.assertRaises(sdlc.Failure):sdlc.review('o/r',1,['ci'],'Expected')
            self.assertEqual(api.call_count,1)
    def test_classifier_keeps_executable_and_policy_changes_in_review(self):
        self.assertEqual(sdlc.classify(['README.md','docs/architecture.md']),'documentation')
        for name in ['AGENTS.md','CLAUDE.md','docs/operations/sdlc.md','docs/example.py','docs/page.mdx','.github/workflows/ci.yml','bin/run','docs/SKILL.md']:
            self.assertEqual(sdlc.classify(['README.md',name]),'code')
    def test_local_approval_helper_requires_published_independent_evidence(self):
        from unittest.mock import Mock
        config = {'verification_mode': 'local', 'validation': ['bin/ci']}
        module = Mock()
        module.Failure = RuntimeError
        module.trusted_receipt.side_effect = RuntimeError('missing evidence')
        pr = dict(self.pr, number=3)
        with patch.object(sdlc, 'gh', return_value={'content': base64.b64encode(json.dumps(config).encode()).decode()}), \
             patch.object(sdlc, 'evidence_module', return_value=module):
            with self.assertRaisesRegex(sdlc.Failure, 'missing evidence'):
                sdlc.published_local_evidence('o/r', pr, ['reviewer'])
        self.assertEqual(module.trusted_receipt.call_args.args[-1], ['Builder'])
        self.assertEqual(module.trusted_receipt.call_args.kwargs['eligible'], ['reviewer'])
    def test_documentation_author_can_validate_own_documentation_pr(self):
        from unittest.mock import Mock
        config = {'verification_mode': 'local', 'validation': ['bin/ci']}
        pr = dict(self.pr, state='open', draft=False)
        module = Mock()
        module.Failure = RuntimeError
        def api(endpoint):
            if endpoint == 'user': return {'login': 'Builder'}
            if endpoint.endswith('/permission'): return {'permission': 'maintain'}
            if '/contents/' in endpoint: return {'content': base64.b64encode(json.dumps(config).encode()).decode()}
            if endpoint == 'repos/o/r/pulls/3': return pr
            raise AssertionError(endpoint)
        with patch.object(sdlc, 'gh', side_effect=api), patch.object(sdlc, 'pages', return_value=[{'filename': 'README.md'}]), \
             patch.object(sdlc, 'evidence_module', return_value=module):
            sdlc.review('o/r', 3, [], 'Builder', config=config)
        self.assertEqual(module.trusted_receipt.call_args.args[-1], [])
    def test_local_service_requires_actual_acceptance_and_release_contract(self):
        config = {'verification_mode': 'local', 'delivery_profile': 'service', 'validation': ['bin/ci']}
        with self.assertRaises(sdlc.Failure):
            sdlc.validate_config(config)
        config.update(acceptance_criteria=['runtime'], release_criteria=['deployed-digest'], delivery_runbook='docs/delivery.md')
        sdlc.validate_config(config)

class ApplyTests(unittest.TestCase):
    def test_version_marker_is_managed(self):
        self.assertIn('SDLC_VERSION', sdlc.MANAGED)
    def test_version_marker_propagates_and_drift_is_detected(self):
        with patch.object(sdlc,'VERSION','2026.09.18.3'):
            self.write_source('first')
        sdlc.apply(self.source,self.target,True)
        (self.target/'SDLC_VERSION').write_text('2026.09.18.3\n')
        (self.source/'SDLC_VERSION').write_text(sdlc.VERSION+'\n')
        with patch.object(sdlc,'MANAGED',['docs/managed.md','SDLC_VERSION']):
            sdlc.stamp(self.source)
        sdlc.apply(self.source,self.target)
        self.assertEqual((self.target/'SDLC_VERSION').read_text(),sdlc.VERSION+'\n')
        (self.target/'SDLC_VERSION').write_text('stale\n')
        self.assertIn('SDLC_VERSION',sdlc.differences(self.target,sdlc.load_manifest(self.target)))
        with self.assertRaises(sdlc.Failure):sdlc.apply(self.source,self.target)
    def test_new_marker_ownership_refuses_unknown_local_content_before_writes(self):
        sdlc.apply(self.source,self.target,True)
        (self.target/'SDLC_VERSION').write_text('local-customization\n')
        (self.source/'SDLC_VERSION').write_text(sdlc.VERSION+'\n')
        (self.source/'docs/managed.md').write_text('second')
        with patch.object(sdlc,'MANAGED',['docs/managed.md','SDLC_VERSION']):
            sdlc.stamp(self.source)
        with self.assertRaisesRegex(sdlc.Failure,'reconciliation'):
            sdlc.apply(self.source,self.target)
        self.assertEqual((self.target/'SDLC_VERSION').read_text(),'local-customization\n')
        self.assertEqual((self.target/'docs/managed.md').read_text(),'first')
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.target=self.root/'target'
        for p in [self.source,self.target]:
            p.mkdir();subprocess.run(['git','init','-q',str(p)],check=True)
        self.write_source('first')
    def write_source(self,text):
        (self.source/'docs').mkdir(exist_ok=True);(self.source/'docs/managed.md').write_text(text)
        with patch.object(sdlc,'MANAGED',['docs/managed.md']):sdlc.stamp(self.source)
    def test_initial_adoption_explicit_and_repeat_idempotent(self):
        with self.assertRaises(sdlc.Failure):sdlc.apply(self.source,self.target)
        sdlc.apply(self.source,self.target,True);sdlc.apply(self.source,self.target)
        self.assertEqual((self.target/'docs/managed.md').read_text(),'first')
    def test_drift_refused_and_product_content_preserved(self):
        (self.target/'product.txt').write_text('application')
        sdlc.apply(self.source,self.target,True)
        (self.target/'docs/managed.md').write_text('custom')
        self.write_source('second')
        with self.assertRaises(sdlc.Failure):sdlc.apply(self.source,self.target)
        self.assertEqual((self.target/'docs/managed.md').read_text(),'custom')
        self.assertEqual((self.target/'product.txt').read_text(),'application')
    def test_invalid_source_refused_before_target_writes(self):
        (self.source/'docs/managed.md').write_text('unstamped')
        with self.assertRaises(sdlc.Failure):sdlc.apply(self.source,self.target,True)
        self.assertFalse((self.target/'docs').exists())
    def test_symlink_and_traversal_refused(self):
        outside=self.root/'outside';outside.mkdir()
        (self.target/'docs').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(sdlc.Failure):sdlc.apply(self.source,self.target,True)
        self.assertFalse(list(outside.iterdir()))
        with self.assertRaises(sdlc.Failure):sdlc.path(self.target,'../outside/file')
    def test_interrupted_lock_does_not_claim_success(self):
        (self.target/'.git/sdlc-apply.lock').touch()
        with self.assertRaises(sdlc.Failure):sdlc.apply(self.source,self.target,True)
        self.assertFalse((self.target/'docs').exists())
    def test_changed_source_updates_existing_install(self):
        sdlc.apply(self.source,self.target,True);self.write_source('second')
        sdlc.apply(self.source,self.target)
        self.assertEqual((self.target/'docs/managed.md').read_text(),'second')

class AuditTests(unittest.TestCase):
    def test_code_hidden_before_documentation_tip_is_rejected(self):
        def api(endpoint):
            if endpoint.endswith('/permission'):return {'permission':'write'}
            raise AssertionError(endpoint)
        with patch.dict(os.environ,{'GITHUB_ACTOR':'Maintainer'}), patch.object(sdlc,'gh',side_effect=api), \
             patch.object(sdlc,'pushed_commits',return_value=['code','docs']), \
             patch.object(sdlc,'changed_files',side_effect=lambda repo,sha:['app.py'] if sha=='code' else ['README.md']), \
             patch.object(sdlc,'pages',return_value=[]):
            with self.assertRaises(sdlc.Failure):sdlc.audit('o/r','before','after')
    def test_documentation_push_requires_maintainer(self):
        with patch.dict(os.environ,{'GITHUB_ACTOR':'Reader'}),patch.object(sdlc,'gh',return_value={'permission':'read'}):
            with self.assertRaises(sdlc.Failure):sdlc.audit('o/r','before','after')
    def test_renames_include_old_path(self):
        with patch.object(sdlc,'gh',return_value={'files':[{'filename':'docs/old.md','previous_filename':'bin/run'}]}):
            self.assertEqual(sdlc.classify(sdlc.changed_files('o/r','sha')),'code')
    def test_non_fast_forward_push_rejected(self):
        with patch.object(sdlc,'gh',return_value={'status':'diverged','commits':[],'total_commits':0}):
            with self.assertRaises(sdlc.Failure):sdlc.pushed_commits('o/r','before','after')

class CascadeTests(unittest.TestCase):
    def test_all_active_targets_attempted_and_failure_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source';source.mkdir();workspace=root/'work'
            def command(*args,cwd=None):
                if args[:3]==('git','rev-parse','HEAD'):return 'a'*40
                if args[:3]==('git','status','--porcelain'):return ''
                if args[:2]==('git','clone'):raise sdlc.Failure('offline')
                raise AssertionError(args)
            with patch.object(sdlc,'load_manifest',return_value={'schema':1,'version':'v','files':{}}), \
                 patch.object(sdlc,'differences',return_value=[]),patch.object(sdlc,'run',side_effect=command), \
                 patch.object(sdlc,'inventory',return_value=['o/first','o/second']), \
                 patch.object(sdlc,'gh',return_value={'default_branch':'main'}):
                with self.assertRaises(sdlc.Failure):sdlc.cascade(source,workspace,'o',True)
            receipt=json.loads((workspace/'cascade-receipt.json').read_text())
            self.assertFalse(receipt['complete'])
            self.assertEqual(set(receipt['repositories']),{'o/first','o/second'})
            self.assertTrue(all(r['state']=='unresolved' for r in receipt['repositories'].values()))
    def test_inventory_growth_prevents_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source';source.mkdir();workspace=root/'work'
            with patch.object(sdlc,'load_manifest',return_value={'schema':1,'version':'v','files':{}}), \
                 patch.object(sdlc,'differences',return_value=[]), \
                 patch.object(sdlc,'run',side_effect=['a'*40,'']), \
                 patch.object(sdlc,'inventory',side_effect=[[],['o/new']]):
                with self.assertRaises(sdlc.Failure):sdlc.cascade(source,workspace,'o',verify=True)
            receipt=json.loads((workspace/'cascade-receipt.json').read_text())
            self.assertFalse(receipt['complete']);self.assertFalse(receipt['inventory_stable'])

if __name__=='__main__':unittest.main()
