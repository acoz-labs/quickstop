import contextlib
import copy
import importlib.machinery
import importlib.util
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader("evidence", str(Path(__file__).resolve().parents[1] / "bin/sdlc-evidence"))
spec = importlib.util.spec_from_loader(loader.name, loader)
e = importlib.util.module_from_spec(spec)
loader.exec_module(e)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.root = self.folder / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("remote", "add", "origin", "https://github.com/o/r.git")
        (self.root / ".sdlc").mkdir()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def configure(self, commands):
        config = {"validation": commands, "acceptance": commands, "verification_mode": "local"}
        (self.root / ".sdlc/config.json").write_text(json.dumps(config))
        self.git("add", ".")
        self.git("commit", "-qm", "Fixture")

    def test_success_retains_exact_revision_commands_and_logs(self):
        self.configure(["printf 'actual output\\n'"])
        r = e.verify(self.root, "o/r", "validation", self.folder / "evidence")
        self.assertTrue(r["success"])
        self.assertEqual(r["sha"], self.git("rev-parse", "HEAD").stdout.decode().strip())
        self.assertEqual((self.folder / "evidence/command-1.log").read_text(), "actual output\n")

    def test_failure_retained_and_cannot_authorize(self):
        self.configure(["printf failure; exit 2"])
        with self.assertRaises(e.Failure):
            e.verify(self.root, "o/r", "validation", self.folder / "evidence")
        r = json.loads((self.folder / "evidence/receipt.json").read_text())
        self.assertFalse(r["success"])
        self.assertEqual(r["commands"][0]["exit_code"], 2)

    def test_pipeline_failure_is_not_hidden(self):
        self.configure(["false | cat"])
        with self.assertRaises(e.Failure):
            e.verify(self.root, "o/r", "validation", self.folder / "evidence")

    def test_wrong_repository_dirty_checkout_and_inside_output_refused(self):
        self.configure(["true"])
        with self.assertRaises(e.Failure):
            e.verify(self.root, "other/repo", "validation", self.folder / "evidence")
        with self.assertRaises(e.Failure):
            e.verify(self.root, "o/r", "validation", self.root / "evidence")
        (self.root / "untracked").touch()
        with self.assertRaises(e.Failure):
            e.verify(self.root, "o/r", "validation", self.folder / "evidence")

    def test_test_mutation_is_not_success(self):
        self.configure(["echo changed > .sdlc/config.json"])
        with self.assertRaises(e.Failure):
            e.verify(self.root, "o/r", "validation", self.folder / "evidence")
        self.assertFalse(json.loads((self.folder / "evidence/receipt.json").read_text())["success"])

    def test_acceptance_rejects_mutable_or_changed_artifact(self):
        self.configure(["printf changed >> \"$RELEASE_ARTIFACT_FILE\""])
        with self.assertRaises(e.Failure):
            e.verify(self.root, "o/r", "acceptance", self.folder / "evidence", "image:latest")
        artifact = self.folder / "release.tar"
        artifact.write_bytes(b"original")
        with self.assertRaises(e.Failure):
            e.verify(self.root, "o/r", "acceptance", self.folder / "evidence", artifact_file=artifact)
        self.assertFalse(json.loads((self.folder / "evidence/receipt.json").read_text())["success"])

    def test_pre_adoption_runs_original_source_with_pinned_separate_policy(self):
        (self.root / "product.txt").write_text("original-product")
        self.git("add", ".")
        self.git("commit", "-qm", "Product before delivery adoption")
        source_sha = self.git("rev-parse", "HEAD").stdout.decode().strip()
        artifact = self.folder / "artifact"
        artifact.write_bytes(b"retained-binary")
        digest = "sha256:" + e.sha256(artifact.read_bytes())
        command = 'test "$(cat product.txt)" = original-product && test ! -e .sdlc/config.json && printf original-source-tested'
        policy = {"validation": ["policy-only-command"], "acceptance_criteria": ["runtime"],
                  "retained_candidates": [{"sha": source_sha, "artifact": digest,
                    "validation": [command], "reason": "Run original source in separate checkout"}]}
        (self.root / ".sdlc/config.json").write_text(json.dumps(policy))
        (self.root / "product.txt").write_text("newer-product")
        self.git("add", ".")
        self.git("commit", "-qm", "Reviewed transition policy")
        policy_sha = self.git("rev-parse", "HEAD").stdout.decode().strip()
        source = self.folder / "original"
        self.git("worktree", "add", "--detach", str(source), source_sha)
        candidate = self.folder / "candidate.json"
        candidate.write_text(json.dumps({"repo": "o/r", "sha": source_sha, "artifact": digest,
            "policy_sha": policy_sha, "config_sha256": e.sha256(e.encoded(e.retained_config(policy, source_sha, digest)))}))
        report = self.folder / "report.json"
        report.write_text(json.dumps({"repo": "o/r", "sha": source_sha, "artifact": digest,
            "scenarios": [{"criterion": "runtime", "result": "passed", "observation": "Synthetic fixture",
                           "evidence": ["https://github.com/o/r/issues/1"]}]}))
        with self.assertRaisesRegex(e.Failure, "policy-root"):
            e.verify(source, "o/r", "acceptance", self.folder / "missing-policy", digest, artifact, candidate, report)
        result = e.verify(source, "o/r", "acceptance", self.folder / "accepted", digest, artifact,
                          candidate, report, self.root)
        self.assertEqual(result["sha"], source_sha)
        self.assertEqual(result["policy_sha"], policy_sha)
        self.assertTrue(result["success"])
        self.assertEqual((self.folder / "accepted/command-1.log").read_text(), "original-source-tested")
        self.assertEqual(artifact.read_bytes(), b"retained-binary")
        (self.root / "untracked").touch()
        with self.assertRaisesRegex(e.Failure, "clean checkout"):
            e.verify(source, "o/r", "acceptance", self.folder / "dirty-policy", digest, artifact,
                     candidate, report, self.root)


class RetainedPolicyTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.artifact = "sha256:" + "b" * 64
        self.policy = {
            "validation": ["bin/sdlc check", "bin/ci"],
            "acceptance_criteria": ["runtime", "recovery"],
            "release_criteria": ["same-bytes"],
            "retained_candidates": [{"sha": self.sha, "artifact": self.artifact,
                                     "validation": ["bin/ci"],
                                     "reason": "Source predates delivery tooling; run its full original suite."}]}

    def test_explicit_transition_preserves_all_nonvalidation_policy(self):
        original = copy.deepcopy(self.policy)
        selected = e.retained_config(self.policy, self.sha, self.artifact)
        self.assertEqual(selected["validation"], ["bin/ci"])
        self.assertEqual(selected["acceptance_criteria"], ["runtime", "recovery"])
        self.assertEqual(selected["release_criteria"], ["same-bytes"])
        self.assertEqual(self.policy, original)

    def test_no_fallback_for_unknown_or_changed_identity(self):
        for sha, artifact in [("c" * 40, self.artifact), (self.sha, "sha256:" + "d" * 64),
                              ("main", self.artifact), (self.sha, "latest")]:
            with self.subTest(sha=sha, artifact=artifact), self.assertRaises(e.Failure):
                e.retained_config(self.policy, sha, artifact)

    def test_ambiguous_missing_commands_or_policy_override_rejected(self):
        cases = [[], [self.policy["retained_candidates"][0]] * 2]
        for mutation in [{"validation": []}, {"reason": ""}, {"acceptance_criteria": []},
                         {"validation": "bin/ci"}, {"validation": [""]}]:
            cases.append([dict(self.policy["retained_candidates"][0], **mutation)])
        for entries in cases:
            with self.subTest(entries=entries), self.assertRaises(e.Failure):
                e.retained_config(dict(self.policy, retained_candidates=entries), self.sha, self.artifact)


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.config = {"validation": ["bin/ci"], "acceptance": ["bin/accept"]}
        self.receipt = {"schema": 1, "id": "run-id", "repo": "o/r", "subject": 1,
                        "phase": "validation", "sha": "a" * 40, "actor": "Reviewer",
                        "config_sha256": e.sha256(e.encoded(self.config)), "success": True,
                        "clean_before": True, "clean_after": True,
                        "commands": [{"command": "bin/ci", "exit_code": 0, "log": "command-1.log"}],
                        "logs": [{"command": "bin/ci", "sha256": e.sha256(b"passed"),
                                  "urls": ["https://github.com/o/r/issues/1#issuecomment-10"]}]}

    def comment(self, receipt, id=20, author="Reviewer"):
        return {"id": id, "user": {"login": author}, "body": e.MARKER + "\n```json\n" + json.dumps(receipt) + "\n```",
                "html_url": f"https://github.com/o/r/issues/1#issuecomment-{id}"}

    def api(self, endpoint):
        if endpoint.endswith("/permission"):
            return {"permission": "maintain"}
        if endpoint.endswith("/comments/10"):
            return {"user": {"login": "Reviewer"}, "body": "Verification log `run-id` / `command-1.log` / part 1\n\npassed"}
        raise AssertionError(endpoint)

    def trusted(self, comments):
        with patch.object(e, "pages", return_value=comments), patch.object(e, "api", side_effect=self.api):
            return e.trusted_receipt("o/r", 1, "a" * 40, self.config, "validation", ["Builder"], eligible=["Reviewer"])

    def test_independent_success_is_accepted(self):
        self.assertTrue(self.trusted([self.comment(self.receipt)]).endswith("20"))

    def test_stale_self_wrong_actor_missing_command_and_failed_receipts_refused(self):
        mutations = [{"sha": "b" * 40}, {"actor": "Builder"}, {"success": False},
                     {"commands": []}, {"config_sha256": "changed"}, {"subject": 2}]
        for fields in mutations:
            with self.subTest(fields=fields):
                r = dict(self.receipt, **fields)
                with self.assertRaises(e.Failure):
                    self.trusted([self.comment(r)])
        with self.assertRaises(e.Failure):
            self.trusted([self.comment(dict(self.receipt, actor="Builder"), author="Builder")])

    def test_latest_failure_revokes_success(self):
        with self.assertRaises(e.Failure):
            self.trusted([self.comment(self.receipt), self.comment(dict(self.receipt, success=False), id=21)])

    def test_altered_log_or_external_link_rejected(self):
        for key, value in [("sha256", "0" * 64), ("urls", ["https://example.org/log"])]:
            r = copy.deepcopy(self.receipt)
            r["logs"][0][key] = value
            with self.assertRaises(e.Failure):
                self.trusted([self.comment(r)])

    def test_wrong_artifact_acceptance_rejected(self):
        r = dict(self.receipt, phase="acceptance", artifact="sha256:" + "1" * 64,
                 commands=[{"command": "bin/accept", "exit_code": 0}])
        with self.assertRaises(e.Failure):
            e.validate_receipt(r, "o/r", "a" * 40, self.config, "acceptance", "sha256:" + "2" * 64)

    def test_publish_requires_log_review_before_api(self):
        with patch.object(e, "api") as api:
            with self.assertRaises(e.Failure):
                e.publish(Path("missing"), 1, "Reviewer", False, "review")
            api.assert_not_called()


class PublishRoundTripTests(unittest.TestCase):
    """Publish to a fake GitHub that rewrites controls as GitHub does, then verify."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.config = {"validation": ["bin/ci"]}
        self.comments = []

    @staticmethod
    def caret(body):
        # Observed on GitHub: C0 except BS, TAB, LF, VT, FF, CR, and all C1, become ^X.
        return re.sub(r"[\x00-\x07\x0e-\x1f\x80-\x9f]",
                      lambda m: "^" + chr((ord(m[0]) & 0x1f) + 0x40), body)

    def api(self, endpoint, payload=None):
        if endpoint == "user":
            return {"login": "Reviewer"}
        if endpoint.endswith("/permission"):
            return {"permission": "maintain"}
        if endpoint == "repos/o/r/pulls/1":
            return {"state": "open", "draft": False, "head": {"sha": "a" * 40}}
        if endpoint == "repos/o/r/issues/1/comments" and payload is not None:
            id = 100 + len(self.comments)
            self.comments.append({"id": id, "user": {"login": "Reviewer"},
                                  "body": self.caret(payload["body"]),
                                  "html_url": f"https://github.com/o/r/pull/1#issuecomment-{id}"})
            return self.comments[-1]
        if endpoint.startswith("repos/o/r/issues/comments/"):
            return next(c for c in self.comments if str(c["id"]) == endpoint.rsplit("/", 1)[1])
        raise AssertionError(endpoint)

    def publish_and_verify(self, log):
        (self.folder / "command-1.log").write_bytes(log)
        receipt = {"schema": 1, "id": "run-id", "repo": "o/r", "phase": "validation", "sha": "a" * 40,
                   "config_sha256": e.sha256(e.encoded(self.config)), "success": True,
                   "clean_before": True, "clean_after": True,
                   "commands": [{"command": "bin/ci", "exit_code": 0, "log": "command-1.log",
                                 "sha256": e.sha256(log)}]}
        (self.folder / "receipt.json").write_text(json.dumps(receipt))
        with patch.object(e, "api", side_effect=self.api), \
             patch.object(e, "pages", side_effect=lambda endpoint: list(self.comments)), \
             contextlib.redirect_stdout(None):
            e.publish(self.folder / "receipt.json", 1, "Reviewer", True, "Logs reviewed")
            url = e.trusted_receipt("o/r", 1, "a" * 40, self.config, "validation", ["Builder"])
        published = e.parse_comment(self.comments[-1])
        self.assertEqual(url, self.comments[-1]["html_url"])
        self.assertEqual(published["commands"][0]["sha256"], e.sha256(log), "run hash stays the original bytes")
        return published["logs"][0]["sha256"], "".join(c["body"].split("\n\n", 1)[1] for c in self.comments[:-1])

    def test_coloured_log_publishes_without_escapes_and_verifies(self):
        log = (b"\x1b[1;32mOK\x1b[0m tests\n\x1b]8;;https://example.org\x07link\x1b]8;;\x07\n"
               b"\x1b[2K\x1b(Bplain\x1b\n")
        published_hash, text = self.publish_and_verify(log)
        self.assertEqual(text, "OK tests\nlink\nplain\n")
        self.assertEqual(published_hash, e.sha256(text.encode()))

    def test_other_controls_github_rewrites_are_removed(self):
        log = ("\x1b[32mOK\x1b[m\x0f tests\n"  # tmux/screen colour reset ends in SI
               "done\x07\n"
               "\x9b31mC1 colour\x9b0m \x85\x00\n").encode()
        _, text = self.publish_and_verify(log)
        self.assertEqual(text, "OK tests\ndone\nC1 colour \n")

    def test_unterminated_osc_keeps_later_lines(self):
        log = b"start\x1b]0;title\nreal log line 1\nreal log line 2\x07end\n"
        _, text = self.publish_and_verify(log)
        self.assertEqual(text, "start0;title\nreal log line 1\nreal log line 2end\n")

    def test_log_without_escapes_hashes_as_before(self):
        log = "passed ✓ [1/2] ^[ literal\b\t\x0b\x0c\x7f\r\n".encode() + b"bad byte \x9b\xff\n"
        published_hash, text = self.publish_and_verify(log)
        self.assertEqual(published_hash, e.sha256(log.decode("utf-8", errors="replace").encode()))
        self.assertEqual(text, log.decode("utf-8", errors="replace"))

    def test_long_coloured_log_splits_after_stripping(self):
        log = b"\x1b[31mx\x1b[0m" * 12000
        _, text = self.publish_and_verify(log)
        self.assertEqual(text, "x" * 12000)
        self.assertEqual(len(self.comments), 3)


class ScenarioReportTests(unittest.TestCase):
    def setUp(self):
        self.report = {"repo": "o/r", "sha": "a" * 40, "artifact": "sha256:" + "b" * 64,
                       "scenarios": [{"criterion": "runtime", "result": "passed", "observation": "Started retained candidate and exercised login",
                                      "evidence": ["https://github.com/o/r/issues/1#issuecomment-10"]}]}

    def check(self, report=None, criteria=None):
        return e.report_passes(report or self.report, criteria or ["runtime"], "o/r", "a" * 40, "sha256:" + "b" * 64)

    def test_observed_runbook_evidence_is_supported(self):
        self.assertTrue(self.check())
        self.assertEqual(e.commands_for({"validation": ["bin/ci"], "acceptance_criteria": ["runtime"]}, "acceptance"), ["bin/ci"])

    def test_missing_criterion_evidence_wrong_bytes_and_failure_rejected(self):
        with self.assertRaises(e.Failure):
            self.check(criteria=["runtime", "recovery"])
        for change in [{"artifact": "sha256:" + "c" * 64}, {"sha": "d" * 40}]:
            with self.assertRaises(e.Failure):
                self.check(dict(self.report, **change))
        bad = copy.deepcopy(self.report)
        bad["scenarios"][0]["evidence"] = []
        with self.assertRaises(e.Failure):
            self.check(bad)
        failed = copy.deepcopy(self.report)
        failed["scenarios"][0]["result"] = "failed"
        self.assertFalse(self.check(failed))


if __name__ == "__main__":
    unittest.main()
