import json
import tempfile
import tomllib
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import sidepulse
from sidepulse.collector import AgentMonitor, LiveAgentMonitor, SourceSpec, status_from_event
from sidepulse.install import codex_hook_block
from sidepulse.led_status import program_for_agent_mode
from sidepulse.models import AgentMode, HookEvent
from sidepulse.providers import CODEX_EVENTS
from sidepulse.settings import AgentMonitorSettings


ROOT = Path(__file__).resolve().parent
assert Path(sidepulse.__file__).resolve().is_relative_to(ROOT), "Use the temporary copy"
BASE = datetime.now(timezone.utc) - timedelta(minutes=1)


def event(name, provider="codex", session="test-session", *, agent=None, second=0):
    payload = {"hook_event_name": name, "session_id": session, "last_assistant_message": "Done."}
    if agent:
        payload["agent_id"] = agent
    return HookEvent(
        provider=provider, logged_at=BASE + timedelta(seconds=second),
        event_name=name, raw=payload, session_id=session, agent_id=agent,
    )


def write_events(path, records):
    rows = []
    for record in records:
        timestamp = record.logged_at.isoformat()
        row = ({"logged_at": timestamp, "event": record.raw} if record.provider == "codex"
               else {**record.raw, "logged_at": timestamp})
        rows.append(json.dumps(row))
    path.write_text("\n".join(rows) + "\n")


class ExitBehavior(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        home = patch.object(Path, "home", return_value=self.directory)
        home.start()
        self.addCleanup(home.stop)

    def test_response_stays_completed_until_exit(self):
        for provider in ("codex", "claude"):
            with self.subTest(provider=provider):
                monitor = LiveAgentMonitor(idle_visible_seconds=600)
                monitor.ingest_record(event("Stop", provider))
                self.assertEqual(monitor.snapshot().aggregate.mode, AgentMode.COMPLETED)
                monitor.ingest_record(event("SessionEnd", provider, second=1))
                self.assertEqual(monitor.snapshot().aggregate.mode, AgentMode.IDLE_READY)
                self.assertEqual(monitor.snapshot().statuses, ())

    def test_other_sessions_and_providers_keep_their_display(self):
        monitor = LiveAgentMonitor()
        monitor.ingest_record(event("PreToolUse", "codex", "shared-id"))
        monitor.ingest_record(event("Stop", "codex", "other-codex", second=1))
        monitor.ingest_record(event("PermissionRequest", "claude", "shared-id", second=2))
        monitor.ingest_record(event("SessionEnd", "codex", "shared-id", second=3))
        self.assertEqual(monitor.snapshot().aggregate.mode, AgentMode.WAITING_FOR_INPUT)
        monitor.ingest_record(event("SessionEnd", "claude", "shared-id", second=4))
        self.assertEqual(monitor.snapshot().aggregate.mode, AgentMode.COMPLETED)
        self.assertEqual(monitor.snapshot().statuses[0].session_id, "other-codex")
        monitor.ingest_record(event("SessionEnd", "codex", "other-codex", second=5))
        self.assertEqual(monitor.snapshot().statuses, ())

    def test_children_do_not_return_after_restart_or_resume(self):
        for provider in ("codex", "claude"):
            with self.subTest(provider=provider):
                state = self.directory / f"{provider}-latest.json"
                log = self.directory / f"{provider}.jsonl"
                old_child = event("PreToolUse", provider, agent="child", second=1)
                write_events(log, [old_child])
                monitor = LiveAgentMonitor(latest_state_path=state)
                monitor.ingest_record(event("UserPromptSubmit", provider))
                monitor.ingest_record(old_child)
                monitor.ingest_record(event("SessionEnd", provider, second=2))
                self.assertEqual(monitor.snapshot().statuses, ())
                restarted = LiveAgentMonitor(latest_state_path=state, recovery_sources=[SourceSpec(provider, log)])
                self.assertEqual(restarted.snapshot().statuses, ())
                restarted.ingest_record(event("SessionStart", provider, second=3))
                restarted.ingest_record(event("UserPromptSubmit", provider, second=4))
                self.assertEqual(restarted.snapshot().aggregate.mode, AgentMode.WORKING)
                self.assertEqual(len(restarted.snapshot().statuses), 1)
                restarted.ingest_record(event("PreToolUse", provider, agent="new-child", second=5))
                self.assertEqual(restarted.snapshot().aggregate.mode, AgentMode.TOOL_RUNNING)

    def test_late_events_do_not_reopen_a_closed_session(self):
        for provider in ("codex", "claude"):
            with self.subTest(provider=provider):
                monitor = LiveAgentMonitor()
                monitor.ingest_record(event("SessionEnd", provider, second=5))
                for name in ("Stop", "Notification", "PostToolUse"):
                    monitor.ingest_record(event(name, provider, second=6))
                monitor.ingest_record(event("PreToolUse", provider, agent="late-child", second=7))
                monitor.ingest_record(event("SessionStart", provider, agent="late-child", second=8))
                self.assertEqual(monitor.snapshot().statuses, ())
                monitor.ingest_record(event("SessionStart", provider, second=2))
                self.assertEqual(monitor.snapshot().statuses, ())
                monitor.ingest_record(event("UserPromptSubmit", provider, second=10))
                self.assertEqual(monitor.snapshot().aggregate.mode, AgentMode.WORKING)
                monitor.ingest_record(event("SessionEnd", provider, second=5))
                self.assertEqual(monitor.snapshot().aggregate.mode, AgentMode.WORKING)

    def test_exit_during_monitor_downtime_closes_saved_children(self):
        state = self.directory / "latest.json"
        log = self.directory / "codex.jsonl"
        monitor = LiveAgentMonitor(latest_state_path=state)
        monitor.ingest_record(event("PreToolUse"))
        monitor.ingest_record(event("PreToolUse", agent="child", second=1))
        write_events(log, [event("SessionEnd", second=2)])
        restarted = LiveAgentMonitor(latest_state_path=state, recovery_sources=[SourceSpec("codex", log)])
        self.assertEqual(restarted.snapshot().statuses, ())
        restarted.ingest_record(event("SessionStart", second=3))
        restarted.ingest_record(event("UserPromptSubmit", second=4))
        self.assertEqual(len(restarted.snapshot().statuses), 1)

    def test_previous_version_saved_exit_cannot_restore_a_child(self):
        state = self.directory / "legacy-latest.json"
        child = status_from_event(event("PreToolUse", agent="child", second=1))
        ended = status_from_event(event("SessionEnd", second=2))
        self.assertIsNotNone(child)
        self.assertIsNotNone(ended)
        state.write_text(json.dumps({"statuses": [replace(ended, mode=AgentMode.COMPLETED).to_dict(), child.to_dict()]}))
        monitor = LiveAgentMonitor(latest_state_path=state)
        self.assertEqual(monitor.snapshot().statuses, ())
        monitor.ingest_record(event("UserPromptSubmit", second=3))
        self.assertEqual(len(monitor.snapshot().statuses), 1)

    def test_log_replay_and_live_events_agree(self):
        for provider in ("codex", "claude"):
            with self.subTest(provider=provider):
                log = self.directory / f"replay-{provider}.jsonl"
                live = LiveAgentMonitor(idle_visible_seconds=600)
                records = [event("UserPromptSubmit", provider),
                           event("PreToolUse", provider, agent="child", second=1),
                           event("SessionEnd", provider, second=2),
                           event("Stop", provider, agent="child", second=3),
                           event("SessionStart", provider, second=4),
                           event("Stop", provider, second=5)]
                for index, record in enumerate(records):
                    live.ingest_record(record)
                    write_events(log, records[:index + 1])
                    replay = AgentMonitor(sources=[SourceSpec(provider, log)], idle_visible_seconds=600)
                    actual, expected = replay.snapshot(), live.snapshot()
                    self.assertEqual(actual.aggregate.mode, expected.aggregate.mode)
                    self.assertEqual({item.agent_id for item in actual.statuses}, {item.agent_id for item in expected.statuses})
                    if record.event_name == "SessionEnd":
                        self.assertEqual(actual.statuses, ())
                self.assertEqual(len(live.snapshot().statuses), 1)

    def test_exit_overrides_embedded_display_hint(self):
        record = event("SessionEnd")
        monitor = LiveAgentMonitor()
        monitor.ingest_record(replace(record, raw={**record.raw, "sidepulse_mode": "working"}))
        self.assertEqual(monitor.snapshot().statuses, ())

    def test_child_exit_keeps_parent_and_sibling_active(self):
        monitor = LiveAgentMonitor()
        monitor.ingest_record(event("UserPromptSubmit"))
        monitor.ingest_record(event("PreToolUse", agent="child", second=1))
        monitor.ingest_record(event("PreToolUse", agent="sibling", second=2))
        monitor.ingest_record(event("SessionEnd", agent="child", second=3))
        self.assertEqual(
            {status.agent_id for status in monitor.snapshot().statuses},
            {"codex:session:test-session", "codex:agent:sibling"},
        )

    def test_parent_exit_closes_a_late_child_event(self):
        monitor = LiveAgentMonitor()
        monitor.ingest_record(event("UserPromptSubmit"))
        monitor.ingest_record(event("PreToolUse", agent="child", second=3))
        monitor.ingest_record(event("SessionEnd", second=2))
        self.assertEqual(monitor.snapshot().statuses, ())

    def test_codex_exit_hook_and_existing_immediate_off_animation(self):
        block = tomllib.loads(codex_hook_block(self.directory / "codex.jsonl"))
        self.assertIn("SessionEnd", CODEX_EVENTS)
        self.assertEqual(block["hooks"]["SessionEnd"][0]["hooks"][0]["timeout"], 3)
        before = AgentMonitorSettings()
        after = before.with_agent_animation(AgentMode.IDLE_READY, style="immediate-off")
        self.assertEqual(program_for_agent_mode(AgentMode.IDLE_READY, animation_style=after.agent_animation_id(AgentMode.IDLE_READY)), "off")
        for mode in (AgentMode.COMPLETED, AgentMode.WORKING, AgentMode.WAITING_FOR_INPUT):
            self.assertEqual(before.agent_animation(mode), after.agent_animation(mode))


if __name__ == "__main__":
    unittest.main(verbosity=2)
