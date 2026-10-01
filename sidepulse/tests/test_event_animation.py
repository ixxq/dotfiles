from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import tempfile
import unittest

import objc
import sidepulse
from sidepulse.collector import LiveAgentMonitor
from sidepulse.device_writer import DeviceCandidate, validate_led_text
from sidepulse.led_status import AgentLedController, apply_brightness, program_for_agent_mode
from sidepulse.led_wasm import SdLedWasmController
from sidepulse.models import AgentMode, HookEvent
from sidepulse.service import SidePulseService
from sidepulse.settings import AgentMonitorSettings, LED_DISPLAY_AGENT
from sidepulse.event_animation import AgentEventAnimation, rainbow_program
from sidepulse.status_bar import StatusBarController


ROOT = Path(__file__).resolve().parent
assert Path(sidepulse.__file__).resolve().is_relative_to(ROOT), 'Use the temporary copy'
BASE = datetime.now(timezone.utc) - timedelta(minutes=1)
SETTINGS = AgentMonitorSettings().with_agent_animation(AgentMode.IDLE_READY, 'immediate-off')
NORMAL = SETTINGS.agent_animation(AgentMode.IDLE_READY)


def event(name='SessionStart', *, source='startup', provider='codex', session='startup-test', second=0):
    return HookEvent(
        provider=provider, event_name=name, logged_at=BASE + timedelta(seconds=second),
        session_id=session,
        raw={'hook_event_name': name, 'source': source, 'session_id': session},
    )


def payload(record):
    timestamp = {'logged_at': record.logged_at.isoformat()}
    if record.provider == 'codex':
        return {**timestamp, 'event': record.raw}
    return {**record.raw, **timestamp}


class StartupCheck(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory(dir=ROOT))
        self.directory = Path(directory)
        self.enterContext(patch.object(Path, 'home', return_value=self.directory))
        self.clock = self.enterContext(patch('sidepulse.event_animation.time.monotonic', return_value=100.0))

    def test_firmware_colors_center_out_fade_and_no_repeat(self):
        for count in (2, 8):
            program = rainbow_program(count)
            validate_led_text(program)
            self.assertNotIn('repeat', program)
            engine = SdLedWasmController(count)
            self.assertTrue(engine.parse(program, 0).ok)
            frames = {ms: engine.step(ms) for ms in range(0, 1501, 10)}
            self.assertTrue(all(color == (0, 0, 0) for color in frames[1300]))
            self.assertEqual(frames[1300], frames[1500])
            compact = program_for_agent_mode(AgentMode.WORKING, led_count=count, animation_style='purple-attention')
            self.assertTrue(engine.parse(compact, 0).ok)
            purple_frames = [engine.step(ms) for ms in range(0, 3401, 20)]
            levels = [sum(map(sum, frame)) for frame in purple_frames]
            self.assertGreater(max(levels), min(levels))
            self.assertGreater(max(levels[90:]), 0)
            self.assertTrue(all(red == blue and green == 0 for frame in purple_frames for red, green, blue in frame))
            if count == 8:
                for ms, indexes in ((100, {3, 4}), (300, {2, 3, 4, 5}), (500, set(range(1, 7))), (700, set(range(8)))):
                    self.assertEqual({i for i, color in enumerate(frames[ms]) if max(color) > 0}, indexes)
                self.assertEqual(len(set(frames[800])), 8)
                self.assertLess(sum(map(sum, frames[1100])), sum(map(sum, frames[900])))
                dim = SdLedWasmController(count)
                self.assertTrue(dim.parse(apply_brightness(program, 128), 0).ok)
                dim_frames = {ms: dim.step(ms) for ms in range(0, 801, 10)}
                self.assertLess(sum(map(sum, dim_frames[800])), sum(map(sum, frames[800])) * 0.6)

    def test_only_live_codex_starts_and_resumes_trigger(self):
        for source in ('startup', 'resume', 'clear'):
            intro = AgentEventAnimation()
            intro.observe(event(source=source))
            self.assertEqual(intro.select(AgentMode.IDLE_READY, NORMAL).style, 'custom')
        for record in (event(source='compact'), event(source='unknown'), event(provider='claude'), replace(event(), agent_id='child'), event('Stop')):
            intro = AgentEventAnimation()
            intro.observe(record)
            self.assertIs(intro.select(AgentMode.IDLE_READY, NORMAL), NORMAL)

    def test_duration_from_first_render_restore_and_resume(self):
        intro = AgentEventAnimation()
        intro.observe(event())
        self.clock.return_value = 100.8
        self.assertEqual(intro.select(AgentMode.IDLE_READY, NORMAL).style, 'custom')
        self.clock.return_value = 101.9
        self.assertEqual(intro.select(AgentMode.WORKING, NORMAL).style, 'custom')
        self.clock.return_value = 102.1
        self.assertIs(intro.select(AgentMode.WORKING, NORMAL), NORMAL)
        intro.observe(event())
        self.assertIs(intro.select(AgentMode.IDLE_READY, NORMAL), NORMAL)
        intro.observe(event(source='resume', second=3))
        self.assertEqual(intro.select(AgentMode.IDLE_READY, NORMAL).style, 'custom')

    def test_exit_interrupt_and_attention_restore_immediately(self):
        for name in ('SessionEnd', 'Interrupt'):
            intro = AgentEventAnimation()
            intro.observe(event())
            intro.select(AgentMode.IDLE_READY, NORMAL)
            intro.observe(event(name, second=1))
            self.assertIs(intro.select(AgentMode.IDLE_READY, NORMAL), NORMAL)
        for mode in (AgentMode.WAITING_FOR_INPUT, AgentMode.BLOCKED_ERROR):
            intro = AgentEventAnimation()
            intro.observe(event())
            self.assertIs(intro.select(mode, NORMAL), NORMAL)
            self.assertIs(intro.select(AgentMode.IDLE_READY, NORMAL), NORMAL)
        intro = AgentEventAnimation()
        intro.observe(event(second=5))
        intro.observe(event('SessionEnd', second=1))
        intro.observe(event('SessionEnd', session='other', second=6))
        self.assertEqual(intro.select(AgentMode.IDLE_READY, NORMAL).style, 'custom')

    def test_no_delayed_or_recovered_intro_and_bursts_are_finite(self):
        intro = AgentEventAnimation()
        intro.observe(event())
        self.clock.return_value = 103
        self.assertIs(intro.select(AgentMode.IDLE_READY, NORMAL), NORMAL)
        intro.observe(event(second=3))
        intro.select(AgentMode.IDLE_READY, NORMAL)
        self.clock.return_value = 104
        intro.observe(event(session='other', second=4))
        self.clock.return_value = 104.3
        self.assertIs(intro.select(AgentMode.IDLE_READY, NORMAL), NORMAL)
        latest = self.directory / 'latest.json'
        monitor = LiveAgentMonitor(latest_state_path=latest)
        monitor.ingest_record(event())
        restarted = LiveAgentMonitor(latest_state_path=latest, recovery_sources=[])
        self.assertIs(AgentEventAnimation().select(restarted.snapshot().aggregate.mode, NORMAL), NORMAL)

    def test_compact_lifecycle_priority_recovery_and_parallel_sessions(self):
        for provider in ('codex', 'claude'):
            for ending in ('PostCompact', 'SessionStart', 'SessionEnd', 'Interrupt', 'Stop', 'PreToolUse'):
                with self.subTest(provider=provider, ending=ending):
                    monitor = LiveAgentMonitor()
                    animation = AgentEventAnimation()
                    animation.observe(event())
                    monitor.ingest_record(event('PreCompact', provider=provider))
                    snapshot = monitor.snapshot()
                    self.assertEqual(animation.select(snapshot.aggregate.mode, NORMAL, statuses=snapshot.statuses).style, 'purple-attention')
                    monitor.ingest_record(event(ending, provider=provider, source='compact', second=1))
                    snapshot = monitor.snapshot()
                    self.assertIs(animation.select(snapshot.aggregate.mode, NORMAL, statuses=snapshot.statuses), NORMAL)

        latest = self.directory / 'compact-latest.json'
        monitor = LiveAgentMonitor(latest_state_path=latest)
        monitor.ingest_record(event('PreCompact'))
        monitor.ingest_record(event('PreCompact', provider='claude'))
        monitor = LiveAgentMonitor(latest_state_path=latest)
        animation = AgentEventAnimation()

        def selected():
            snapshot = monitor.snapshot()
            return animation.select(snapshot.aggregate.mode, NORMAL, statuses=snapshot.statuses)

        self.assertEqual(selected().style, 'purple-attention')
        for name in ('PermissionRequest', 'StopFailure'):
            monitor.ingest_record(event(name, session=name, second=1))
            self.assertIs(selected(), NORMAL)
            monitor.ingest_record(event('SessionEnd', session=name, second=2))
            self.assertEqual(selected().style, 'purple-attention')
        monitor.ingest_record(event('PostCompact', second=3))
        self.assertEqual(selected().style, 'purple-attention')
        monitor.ingest_record(event('SessionEnd', provider='claude', second=4))
        self.assertIs(selected(), NORMAL)
        monitor.ingest_record(event('PreCompact', provider='claude', second=2))
        self.assertIs(selected(), NORMAL)
        monitor = LiveAgentMonitor()
        monitor.ingest_record(replace(event('PreCompact'), logged_at=BASE - timedelta(hours=2)))
        self.assertIs(selected(), NORMAL)

    def test_service_event_to_device_output_and_exit(self):
        service = SidePulseService.__new__(SidePulseService)
        service.monitor = LiveAgentMonitor()
        service.event_animation = AgentEventAnimation()
        service.last_program_by_target = {}
        target = self.directory / 'LEDS.LED'
        for name, value in {
            'status_bar_monitor_available': False, 'load_settings': SETTINGS,
            'read_battery_snapshot': None, 'load_ios_links': [],
            'discover_devices': [DeviceCandidate(self.directory, target, 'test')],
        }.items():
            self.enterContext(patch('sidepulse.service.' + name, return_value=value))
        writer = self.enterContext(patch('sidepulse.service.write_led_program'))
        service.ingest_event('codex', payload(event()))
        service.sync_outputs()
        self.assertEqual(writer.call_args.args[0].strip(), rainbow_program())
        service.sync_outputs()
        self.assertEqual(writer.call_count, 1)
        service.ingest_event('codex', payload(event('UserPromptSubmit', second=1)))
        self.clock.return_value = 101.3
        service.sync_outputs()
        regular = SETTINGS.agent_animation(AgentMode.WORKING)
        self.assertEqual(writer.call_args.args[0], program_for_agent_mode(AgentMode.WORKING, animation_style=regular.style))
        service.ingest_event('codex', payload(event('PreCompact', second=2)))
        service.sync_outputs()
        self.assertEqual(writer.call_args.args[0], program_for_agent_mode(AgentMode.WORKING, animation_style='purple-attention'))
        service.ingest_event('codex', payload(event('PostCompact', second=3)))
        service.sync_outputs()
        self.assertEqual(writer.call_args.args[0], program_for_agent_mode(AgentMode.WORKING, animation_style=regular.style))
        service.ingest_event('codex', payload(event('SessionStart', source='compact', second=4)))
        service.sync_outputs()
        self.assertEqual(writer.call_args.args[0], 'off')
        service.ingest_event('codex', payload(event('SessionEnd', second=5)))
        service.sync_outputs()
        self.assertEqual(writer.call_args.args[0], 'off')
        self.assertFalse(target.exists())

    def test_menu_bar_event_to_device_output_and_exit(self):
        log = self.enterContext(patch('sidepulse.status_bar.log_status_bar'))
        allocated = StatusBarController.alloc()
        controller = objc.super(StatusBarController, allocated).init()
        controller.monitor = LiveAgentMonitor()
        controller.event_animation = AgentEventAnimation()
        controller.settings = SETTINGS
        controller.last_snapshot = None
        controller.schedule_event_refresh = Mock()
        device = SimpleNamespace(device_id='test', connected=True, target=self.directory / 'LEDS.LED', name='Test', remote_link=None, brightness=128)
        controller.status_bar_devices = Mock(return_value=[device])
        controller.active_led_display_kind_for_device = Mock(return_value=LED_DISPLAY_AGENT)
        controller.last_led_display_kind_by_device = {'test': LED_DISPLAY_AGENT}
        controller.device_errors = {}
        led = AgentLedController(device_path=device.target, dry_run=True, brightness=device.brightness)
        controller.agent_controller_for_device = Mock(return_value=led)
        controller.handle_hook_event_message('codex', payload(event()))
        self.assertEqual(controller.schedule_event_refresh.call_count, 1)
        controller.sync_leds_now(AgentMode.IDLE_READY, None, LED_DISPLAY_AGENT)
        self.assertEqual(led.last_program.strip(), apply_brightness(rainbow_program(), 128).strip())
        controller.handle_hook_event_message('claude', payload(event('PreCompact', provider='claude', second=1)))
        controller.last_snapshot = controller.monitor.snapshot()
        controller.sync_leds_now(controller.last_snapshot.aggregate.mode, None, LED_DISPLAY_AGENT)
        self.assertEqual(led.last_program, program_for_agent_mode(AgentMode.WORKING, brightness=128, animation_style='purple-attention'))
        controller.handle_hook_event_message('claude', payload(event('PostCompact', provider='claude', second=2)))
        controller.last_snapshot = controller.monitor.snapshot()
        controller.sync_leds_now(controller.last_snapshot.aggregate.mode, None, LED_DISPLAY_AGENT)
        regular = SETTINGS.agent_animation(AgentMode.WORKING)
        self.assertEqual(led.last_program, program_for_agent_mode(AgentMode.WORKING, brightness=128, animation_style=regular.style))
        controller.handle_hook_event_message('claude', payload(event('SessionEnd', provider='claude', second=3)))
        controller.handle_hook_event_message('codex', payload(event('SessionEnd', second=4)))
        controller.last_snapshot = controller.monitor.snapshot()
        controller.sync_leds_now(AgentMode.IDLE_READY, None, LED_DISPLAY_AGENT)
        self.assertEqual(led.last_program.strip(), apply_brightness('off', 128).strip())
        self.assertEqual(controller.device_errors, {})
        self.assertFalse(any('error' in call.args[0].lower() for call in log.call_args_list))
        self.assertFalse(device.target.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
