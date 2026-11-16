"""Tests for the reconnect state machine in ble_worker, using a fake BLE client.

No Bluetooth hardware or ROS needed (bleak must be installed, since the module
imports it). The fake client stands in for BleakClient and scripts what the
strap does: send notifications, disconnect, or go silent.
"""
import asyncio
import queue
import time

import pytest

from polar_h10_ros.ble_worker import PolarBleWorker

PACKET_72_BPM = bytes([0x16, 0x48, 0x55, 0x03])


class ListLogger:
    def __init__(self):
        self.lines = []

    def info(self, msg):
        self.lines.append(msg)

    warning = error = info


class FakeClient:
    """Each instance = one connection attempt. `script` is a list of (delay_s, action)."""

    instances = []
    script = []

    def __init__(self, target, disconnected_callback, timeout):
        self.target = target
        self._on_disconnect = disconnected_callback
        FakeClient.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def start_notify(self, _uuid, callback):
        loop = asyncio.get_running_loop()
        for delay_s, action in FakeClient.script:
            if action == 'notify':
                loop.call_later(delay_s, callback, None, bytearray(PACKET_72_BPM))
            elif action == 'disconnect':
                loop.call_later(delay_s, self._on_disconnect, self)

    async def stop_notify(self, _uuid):
        pass


@pytest.fixture(autouse=True)
def reset_fake():
    FakeClient.instances = []
    FakeClient.script = []


def drain(q):
    items = []
    while True:
        try:
            items.append(q.get_nowait())
        except queue.Empty:
            return items


def wait_until(pred, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.02)
    return False


def make_worker(q, log, **kw):
    return PolarBleWorker(q, log, device_address='AA:BB:CC:DD:EE:FF',
                          reconnect_backoff_initial_s=0.1, client_factory=FakeClient, **kw)


def test_streams_then_reconnects_after_disconnect():
    FakeClient.script = [(0.05, 'notify'), (0.10, 'notify'), (0.30, 'disconnect')]
    q, log = queue.Queue(), ListLogger()
    worker = make_worker(q, log, reconnect_backoff_max_s=1.0)
    worker.start()
    try:
        assert wait_until(lambda: len(FakeClient.instances) >= 2), log.lines
    finally:
        worker.stop()

    items = drain(q)
    kinds = [k for k, _ in items]
    # first session: up, two samples, down
    assert kinds[:4] == ['connected', 'sample', 'sample', 'connected']
    assert items[0][1] is True and items[3][1] is False
    assert items[1][1].bpm == 72
    assert any('DeviceDisconnected' in line for line in log.lines)
    assert any('-> BACKOFF' in line for line in log.lines)
    assert log.lines[-1].endswith('-> STOPPED')


def test_notification_timeout_drops_link():
    FakeClient.script = []  # connects but never notifies
    q, log = queue.Queue(), ListLogger()
    worker = make_worker(q, log, notification_timeout_s=0.3)
    worker.start()
    try:
        assert wait_until(lambda: any('NotificationTimeout' in s for s in log.lines)), log.lines
    finally:
        worker.stop()
    kinds_vals = drain(q)
    assert kinds_vals[:2] == [('connected', True), ('connected', False)]


def test_backoff_doubles_and_caps():
    class AlwaysFails(FakeClient):
        async def __aenter__(self):
            from bleak.exc import BleakError
            raise BleakError('connect failed')

    q, log = queue.Queue(), ListLogger()
    worker = PolarBleWorker(q, log, device_address='AA', reconnect_backoff_initial_s=0.05,
                            reconnect_backoff_max_s=0.2, client_factory=AlwaysFails)
    worker.start()
    try:
        assert wait_until(lambda: sum('-> BACKOFF' in s for s in log.lines) >= 5), log.lines
    finally:
        worker.stop()
    waits = [s.split('retrying in ')[1] for s in log.lines if '-> BACKOFF' in s][:5]
    assert waits == ['0.05s)', '0.1s)', '0.2s)', '0.2s)', '0.2s)']


def test_device_filter_matches_by_id():
    from types import SimpleNamespace as NS
    from polar_h10_ros.ble_worker import make_device_filter
    dev = NS(name='Polar H10 18D51C3F', address='x')
    other = NS(name='Polar H10 18D5793E', address='y')
    assert make_device_filter('18d51c3f')(dev, None)
    assert not make_device_filter('18D51C3F')(other, None)
    assert make_device_filter('')(other, None)
    assert not make_device_filter('')(NS(name='Other', address='z'), None)
