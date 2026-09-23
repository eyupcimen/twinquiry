import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from twinquiry import providers
from twinquiry.__main__ import main
from twinquiry.schema import ANSWER, check_response
from twinquiry.session import accept, create, load, lock, pending, write_json


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.folder = self.root / "study with spaces"
        self.dossier, self.state = create(self.folder, "Which option is justified?", [], rounds=4)

    def advance(self, verdict=None):
        task, prompt = pending(self.folder, self.dossier, self.state)
        response, metadata = providers.demo(task)
        if task["stage"] == "review" and verdict:
            response["verdict"] = verdict
            if verdict == "REVISE":
                response["findings"] = [{"severity": "high", "issue": "Missing evidence",
                                         "evidence": "No measurement is supplied", "suggestion": "State uncertainty"}]
        accept(self.folder, self.dossier, self.state, task, response, metadata)
        return task, prompt

    def test_blind_initial_drafts(self):
        self.advance()
        task, prompt = pending(self.folder, self.dossier, self.state)
        self.assertEqual(task["provider"], "claude")
        self.assertNotIn("Synthetic codex answer", prompt)
        self.assertNotIn("CANDIDATE", prompt)

    def test_review_receives_peer_answer_without_provider_label(self):
        self.advance()
        self.advance()
        task, prompt = pending(self.folder, self.dossier, self.state)
        self.assertEqual(task["provider"], "codex")
        self.assertIn("Synthetic claude answer", prompt)  # Text may reveal authorship; not cryptographic anonymity.
        self.assertNotIn('"provider": "claude"', prompt)

    def test_mutual_approval_stops_after_four_calls(self):
        for _ in range(4):
            self.advance()
        self.assertEqual(self.state["outcome"], "mutual_approval")
        self.assertIsNone(pending(self.folder, self.dossier, self.state))

    def test_four_round_cap_is_sixteen_calls_without_unreviewed_final_revision(self):
        while not self.state["outcome"]:
            self.advance("REVISE")
        self.assertEqual(len(self.state["history"]), 16)
        self.assertEqual(self.state["outcome"], "unresolved")
        self.assertEqual(self.state["history"][-1]["stage"], "review")
        self.assertEqual(self.state["history"][-1]["round"], 4)

    def test_revised_answer_does_not_inherit_old_verdict_in_report(self):
        for _ in range(4):
            self.advance("REVISE")
        self.advance()
        report = (self.folder / "report.md").read_text(encoding="utf-8")
        self.assertIn("revised; awaiting review", report)

    def test_blocked_is_not_approval(self):
        for _ in range(4):
            self.advance("BLOCKED")
        self.assertEqual(self.state["outcome"], "blocked")

    def test_compare_mode_preserves_original_answers(self):
        folder = self.root / "comparison"
        dossier, state = create(folder, "Compare", [], mode="compare")
        for _ in range(4):
            task, _ = pending(folder, dossier, state)
            response, metadata = providers.demo(task)
            if task["stage"] == "review":
                response.update(verdict="BLOCKED")
            accept(folder, dossier, state, task, response, metadata)
        self.assertEqual(len(state["history"]), 4)
        self.assertNotIn("revise", [x["stage"] for x in state["history"]])

    def test_resume_uses_next_unfinished_task(self):
        self.advance()
        dossier, state = load(self.folder)
        task, _ = pending(self.folder, dossier, state)
        self.assertEqual(task["provider"], "claude")

    def test_input_mutation_requires_new_session(self):
        self.dossier["question"] = "Different question"
        write_json(self.folder / "dossier.json", self.dossier)
        with self.assertRaisesRegex(ValueError, "inputs changed"):
            load(self.folder)

    def test_stale_submission_does_not_advance_history(self):
        task, _ = pending(self.folder, self.dossier, self.state)
        value, metadata = providers.demo(task)
        self.advance()
        with self.assertRaises(ValueError):
            accept(self.folder, self.dossier, self.state, task, value, metadata)
        self.assertEqual(len(self.state["history"]), 1)

    def test_lock_prevents_concurrent_writers(self):
        with lock(self.folder):
            with self.assertRaises(ValueError):
                with lock(self.folder):
                    pass
        self.assertFalse((self.folder / ".lock").exists())

    def test_schema_rejects_false_approval(self):
        response, _ = providers.demo({"stage": "review"})
        response["findings"] = [{"severity": "high", "issue": "x", "evidence": "y", "suggestion": "z"}]
        with self.assertRaises(ValueError):
            check_response(response, "review", {})

    def test_unknown_and_missing_source_rejected(self):
        response, _ = providers.demo({"stage": "draft", "provider": "codex"})
        claim = response["claims"][0]
        claim.update(status="supported", source_ids=["S9"])
        with self.assertRaises(ValueError):
            check_response(response, "draft", {})
        claim["source_ids"] = []
        with self.assertRaises(ValueError):
            check_response(response, "draft", {})
        claim["source_ids"] = ["https://example.com/research"]
        check_response(response, "draft", {}, web=True)

    def test_empty_malformed_and_extra_fields_rejected(self):
        for response in ({}, None, [], {"surprise": "field"}):
            with self.assertRaises(ValueError):
                check_response(response, "draft", {})

    def test_source_packet_is_snapshotted(self):
        source = self.root / "source.txt"
        source.write_text("Original evidence", encoding="utf-8")
        dossier, _ = create(self.root / "sourced", "Question", [source])
        source.write_text("Changed", encoding="utf-8")
        self.assertEqual(dossier["sources"]["S1"]["text"], "Original evidence")

    def test_failed_live_call_does_not_advance(self):
        with patch.object(providers, "probe", return_value=("fake", "1.0")), \
             patch.object(providers, "call", side_effect=ValueError("Provider unavailable")):
            self.assertEqual(main(["run", str(self.folder), "--codex-model", "a", "--claude-model", "b"]), 1)
        self.assertEqual(load(self.folder)[1]["history"], [])

    def test_demo_cannot_mix_with_live(self):
        self.assertEqual(main(["run", str(self.folder), "--demo", "--steps", "1"]), 0)
        self.assertEqual(main(["run", str(self.folder), "--codex-model", "a", "--claude-model", "b"]), 1)

    def test_manual_submission_round_trip_and_stale_id(self):
        self.assertEqual(main(["next", str(self.folder)]), 0)
        task = json.loads((self.folder / "pending.json").read_text(encoding="utf-8"))
        response, _ = providers.demo(task)
        response_file = self.root / "response.json"
        write_json(response_file, response)
        args = ["submit", str(self.folder), "--task-id", task["id"], "--response", str(response_file)]
        self.assertEqual(main(args), 0)
        self.assertEqual(main(args), 1)
        _, state = load(self.folder)
        self.assertEqual(len(state["history"]), 1)
        self.assertEqual(state["settings"]["execution"], "manual")

    def test_round_range_and_existing_session_rejected(self):
        for rounds in (0, 21):
            with self.assertRaises(ValueError):
                create(self.root / "invalid", "Question", [], rounds=rounds)
        with self.assertRaises(FileExistsError):
            create(self.folder, "Question", [])

    def test_cli_demo_end_to_end(self):
        self.assertEqual(main(["run", str(self.folder), "--demo"]), 0)
        self.assertIn("DEMO: synthetic", (self.folder / "report.md").read_text(encoding="utf-8"))


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def test_explicit_permissions_and_models(self):
        argv = providers.argv_for("claude", "claude", "chosen", self.folder, ANSWER)
        self.assertIn("--safe-mode", argv)
        self.assertIn("dontAsk", argv)
        self.assertNotIn("--dangerously-skip-permissions", argv)
        bypass = providers.argv_for("claude", "claude", "chosen", self.folder, ANSWER, skip_permissions=True)
        self.assertIn("--dangerously-skip-permissions", bypass)
        self.assertNotIn("dontAsk", bypass)
        self.assertEqual(bypass[bypass.index("--tools") + 1], "")
        codex = providers.argv_for("codex", "codex", "chosen", self.folder, ANSWER)
        self.assertIn("read-only", codex)
        self.assertIn("--ignore-user-config", codex)
        self.assertIn('web_search="disabled"', codex)

    def test_codex_needs_completed_turn_not_just_answer_file(self):
        write_json(self.folder / "answer.json", {"summary": "exists"})
        with self.assertRaises(ValueError):
            providers.parse("codex", '{"type":"thread.started"}', self.folder)
        with self.assertRaises(ValueError):
            providers.parse("codex", '{"type":"turn.completed"}\n{"type":"turn.failed"}', self.folder)

    def test_claude_errors_and_denials_are_rejected(self):
        for envelope in ({"type": "result", "subtype": "error"},
                         {"type": "result", "subtype": "success", "permission_denials": ["WebFetch"]},
                         {"type": "result", "subtype": "success"}):
            with self.assertRaises(ValueError):
                providers.parse("claude", json.dumps(envelope), self.folder)

    def test_fake_cli_transport_without_model_calls(self):
        session = self.folder / "session"
        session.mkdir()
        script = self.folder / "fake.py"
        response, _ = providers.demo({"stage": "draft", "provider": "claude"})
        envelope = {"type": "result", "subtype": "success", "structured_output": response,
                    "modelUsage": {"fake-observed-model": {}}, "usage": {"input_tokens": 10}}
        script.write_text("import sys\nsys.stdin.read()\nprint(" + repr(json.dumps(envelope)) + ")\n", encoding="utf-8")
        settings = {"models": {"claude": "requested"}, "web": False, "claude_skip_permissions": False}
        with patch.object(providers, "probe", return_value=(sys.executable, "fake-cli")), \
             patch.object(providers, "argv_for", return_value=[sys.executable, str(script)]):
            result, metadata = providers.call({"stage": "draft", "provider": "claude", "round": 0, "id": "x"},
                                              "Prompt with `literal` $characters", session, settings, 5)
        self.assertEqual(result, response)
        self.assertEqual(metadata["observed_models"], ["fake-observed-model"])

    def test_timeout_stops_process_and_preserves_diagnostics(self):
        session = self.folder / "session"
        session.mkdir()
        settings = {"models": {"claude": "requested"}, "web": False, "claude_skip_permissions": False}
        with patch.object(providers, "probe", return_value=(sys.executable, "fake-cli")), \
             patch.object(providers, "argv_for", return_value=[sys.executable, "-c", "import time; time.sleep(20)"]):
            with self.assertRaises(subprocess.TimeoutExpired):
                providers.call({"stage": "draft", "provider": "claude", "round": 0, "id": "x"},
                               "Prompt", session, settings, 0.1)
        self.assertEqual(len(list(session.glob("attempts/*/failure.json"))), 1)


if __name__ == "__main__":
    unittest.main()
