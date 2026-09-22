import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader("release", str(Path(__file__).resolve().parents[1] / "bin/sdlc-release"))
spec = importlib.util.spec_from_loader(loader.name, loader)
r = importlib.util.module_from_spec(spec)
loader.exec_module(r)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.artifact = "sha256:" + "b" * 64
        self.config = {"acceptance": ["bin/accept"], "delivery_profile": "service"}
        self.impl = [{"number": 2, "head": "c" * 40, "merge": self.sha, "author": "Builder"}]
        self.candidate = {"repo": "o/r", "issue": 1, "sha": self.sha, "artifact": self.artifact,
                          "implementation": self.impl, "spec_sha256": r.e.sha256(b"Specification"),
                          "config_sha256": r.e.sha256(r.e.encoded(self.config))}

    def gate(self, actor="Reviewer", subject=None, candidate=None):
        with patch.object(r.e, "identity"), patch.object(r, "on_default_branch"), patch.object(r, "latest_candidate", return_value=candidate or self.candidate), \
             patch.object(r.e, "api", return_value=subject or {"state": "open", "body": "Specification"}), \
             patch.object(r, "remote_config", return_value=self.config), \
             patch.object(r, "implementation", return_value=self.impl), \
             patch.object(r.e, "trusted_receipt", return_value="https://evidence") as verify:
            result = r.gate("o/r", 1, self.sha, self.artifact, actor)
            self.assertEqual(verify.call_args.kwargs["candidate_sha256"], r.e.sha256(r.e.encoded(self.candidate)))
            return result

    def test_gate_binds_acceptance_to_nomination_and_implementation(self):
        self.assertEqual(self.gate()["candidate"], self.candidate)

    def test_changed_spec_closed_issue_wrong_artifact_and_self_promotion_fail(self):
        cases = [{"subject": {"state": "open", "body": "Changed"}},
                 {"subject": {"state": "closed", "body": "Specification"}},
                 {"candidate": dict(self.candidate, artifact="sha256:" + "d" * 64)},
                 {"actor": "Builder"}]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(r.e.Failure):
                self.gate(**case)

    def test_unmerged_or_missing_implementation_is_rejected(self):
        with self.assertRaises(r.e.Failure):
            r.implementation("o/r", self.sha, [])
        with patch.object(r.e, "api", return_value={"merged": False}):
            with self.assertRaises(r.e.Failure):
                r.implementation("o/r", self.sha, [2])

    def test_merged_but_unreviewed_implementation_is_rejected(self):
        pr = {"merged": True, "base": {"repo": {"full_name": "o/r"}},
              "merge_commit_sha": self.sha, "head": {"sha": self.sha}, "user": {"login": "Builder"}}
        with patch.object(r.e, "api", side_effect=[pr, {"status": "identical"}]), patch.object(r.e, "pages", return_value=[]):
            with self.assertRaisesRegex(r.e.Failure, "approval"):
                r.implementation("o/r", self.sha, [2])

    def test_candidate_outside_default_branch_is_rejected(self):
        with patch.object(r.e, "api", side_effect=[{"default_branch": "main"}, {"status": "diverged"}]):
            with self.assertRaises(r.e.Failure):
                r.on_default_branch("o/r", self.sha)


    def test_transition_gate_binds_policy_and_nomination_to_receipt(self):
        provenance = {"number": 3, "head": "e" * 40, "merge": "d" * 40, "author": "PolicyBuilder"}
        candidate = dict(self.candidate, policy_sha="d" * 40, policy_review=provenance)
        with patch.object(r.e, "identity"), patch.object(r, "on_default_branch"), \
             patch.object(r, "latest_candidate", return_value=candidate), \
             patch.object(r.e, "api", return_value={"state": "open", "body": "Specification"}), \
             patch.object(r, "candidate_config", return_value=self.config) as policy, \
             patch.object(r, "reviewed_policy", return_value=provenance), \
             patch.object(r, "implementation", return_value=self.impl), \
             patch.object(r.e, "trusted_receipt", return_value="https://evidence") as verify:
            r.gate("o/r", 1, self.sha, self.artifact, "Reviewer")
            policy.assert_called_once_with("o/r", self.sha, self.artifact, "d" * 40)
            self.assertEqual(verify.call_args.kwargs["candidate_sha256"], r.e.sha256(r.e.encoded(candidate)))

    def test_changed_transition_policy_fails_before_receipt_lookup(self):
        with patch.object(r.e, "identity"), patch.object(r, "on_default_branch"), \
             patch.object(r, "latest_candidate", return_value=dict(self.candidate, policy_sha="d" * 40)), \
             patch.object(r.e, "api", return_value={"state": "open", "body": "Specification"}), \
             patch.object(r, "candidate_config", return_value=dict(self.config, validation=["changed"])), \
             patch.object(r, "reviewed_policy", return_value=None), \
             patch.object(r.e, "trusted_receipt") as verify, self.assertRaisesRegex(r.e.Failure, "configuration changed"):
            r.gate("o/r", 1, self.sha, self.artifact, "Reviewer")
        verify.assert_not_called()


class PolicyRevisionTests(unittest.TestCase):
    def setUp(self):
        self.sha, self.policy_sha = "a" * 40, "c" * 40
        self.artifact = "sha256:" + "b" * 64
        self.policy = {"validation": ["bin/check"], "retained_candidates": [
            {"sha": self.sha, "artifact": self.artifact, "validation": ["bin/ci"],
             "reason": "Pre-adoption source full suite"}]}

    def test_normal_candidate_keeps_source_policy(self):
        with patch.object(r, "remote_config", return_value=self.policy) as config:
            self.assertEqual(r.candidate_config("o/r", self.sha, self.artifact), self.policy)
            config.assert_called_once_with("o/r", self.sha)

    def test_transition_checks_default_ancestry_and_missing_original_config(self):
        with patch.object(r, "on_default_branch") as branch, \
             patch.object(r, "reviewed_policy") as reviewed, \
             patch.object(r, "source_has_config", return_value=False), \
             patch.object(r.e, "api", return_value={"status": "ahead"}), \
             patch.object(r, "remote_config", return_value=self.policy):
            config = r.candidate_config("o/r", self.sha, self.artifact, self.policy_sha)
            self.assertEqual(config["validation"], ["bin/ci"])
            branch.assert_called_once_with("o/r", self.policy_sha)
            reviewed.assert_called_once_with("o/r", self.policy_sha)

    def test_configured_source_or_non_descendant_policy_refused(self):
        for exists, status in [(True, "ahead"), (False, "diverged"), (False, "behind")]:
            with self.subTest(exists=exists, status=status), patch.object(r, "on_default_branch"), \
                 patch.object(r, "source_has_config", return_value=exists), \
                 patch.object(r.e, "api", return_value={"status": status}), \
                 patch.object(r, "remote_config", return_value=self.policy), self.assertRaises(r.e.Failure):
                r.candidate_config("o/r", self.sha, self.artifact, self.policy_sha)

    def test_symbolic_or_equal_policy_refused(self):
        for policy in ["main", self.sha]:
            with self.subTest(policy=policy), self.assertRaises(r.e.Failure):
                r.candidate_config("o/r", self.sha, self.artifact, policy)

    def test_source_tree_check_does_not_treat_truncation_as_absence(self):
        with patch.object(r.e, "api", return_value={"truncated": True, "tree": []}), self.assertRaises(r.e.Failure):
            r.source_has_config("o/r", self.sha)

    def test_unreviewed_direct_policy_push_is_refused(self):
        with patch.object(r.e, "api", return_value={"commit": {"tree": {"sha": "tree"}}}), \
             patch.object(r.e, "pages", return_value=[]), self.assertRaisesRegex(r.e.Failure, "independently reviewed"):
            r.reviewed_policy("o/r", self.policy_sha)

    def test_reviewed_policy_requires_exact_tree_and_independent_proof(self):
        pr = {"number": 3, "merged": True, "draft": False, "merge_commit_sha": self.policy_sha,
              "base": {"repo": {"full_name": "o/r"}}, "head": {"sha": "d" * 40}, "user": {"login": "Builder"}}
        def api(endpoint):
            if "/commits/" in endpoint:
                return {"commit": {"tree": {"sha": "tree"}}}
            if endpoint.endswith("/pulls/3"):
                return pr
            if endpoint.endswith("/permission"):
                return {"permission": "write"}
            raise AssertionError(endpoint)
        def pages(endpoint):
            if endpoint.endswith("/pulls"):
                return [{"number": 3}]
            return [{"user": {"login": "Reviewer"}}]
        with patch.object(r.e, "api", side_effect=api), patch.object(r.e, "pages", side_effect=pages), \
             patch.object(r.review, "approval", return_value=["Reviewer"]), \
             patch.object(r, "remote_config", return_value=self.policy), \
             patch.object(r.e, "trusted_receipt") as receipt:
            r.reviewed_policy("o/r", self.policy_sha)
            self.assertEqual(receipt.call_args.kwargs["eligible"], ["Reviewer"])
            receipt.side_effect = r.e.Failure("Missing proof")
            with self.assertRaises(r.e.Failure):
                r.reviewed_policy("o/r", self.policy_sha)


class PromotionTests(unittest.TestCase):
    def test_transition_refuses_generic_promotion_before_execution(self):
        with patch.object(r, "gate", return_value={"candidate": {"policy_sha": "c" * 40}}), \
             patch.object(r.e, "clean_head") as inspect, self.assertRaisesRegex(r.e.Failure, "runbook"):
            r.release(Path("source"), "o/r", 1, "a" * 40, "sha256:" + "b" * 64,
                      "Reviewer", Path("output"))
        inspect.assert_not_called()

    def test_resume_verifies_without_repeating_promotion(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "repo"
            root.mkdir()
            output = Path(folder) / "receipt"
            output.mkdir()
            candidate = {"sha": "a" * 40, "artifact": "sha256:" + "b" * 64}
            config = {"promotion": ["echo promotion >> deployed"],
                      "release_verification": ["echo verified"], "rollback": ["echo restore"]}
            receipt = {"candidate": candidate, "state": "promotion", "commands": []}
            (output / "release.json").write_text(json.dumps(receipt))
            checked = {"candidate": candidate, "config": config, "acceptance": "https://evidence"}
            with patch.object(r, "gate", return_value=checked), \
                 patch.object(r.e, "clean_head", return_value="a" * 40), \
                 patch.object(r.e, "config_at", return_value=config):
                with self.assertRaises(r.e.Failure):
                    r.release(root, "o/r", 1, "a" * 40, candidate["artifact"], "Reviewer", output)
                result = r.release(root, "o/r", 1, "a" * 40, candidate["artifact"], "Reviewer", output, True)
            self.assertEqual(result["state"], "verified")
            self.assertFalse((root / "deployed").exists())
            self.assertEqual([c["phase"] for c in result["commands"]], ["release_verification"])

    def test_missing_promotion_capability_is_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "repo"
            root.mkdir()
            config = {"promotion": [], "release_verification": ["true"], "rollback": ["true"]}
            with patch.object(r, "gate", return_value={"candidate": {}, "config": config}), \
                 patch.object(r.e, "clean_head", return_value="a" * 40), patch.object(r.e, "config_at", return_value=config):
                with self.assertRaises(r.e.Failure):
                    r.release(root, "o/r", 1, "a" * 40, "sha256:" + "b" * 64, "Reviewer", Path(folder) / "output")


if __name__ == "__main__":
    unittest.main()
