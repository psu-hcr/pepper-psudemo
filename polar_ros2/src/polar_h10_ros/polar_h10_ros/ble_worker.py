"""BLE side of the Polar H10 node: connection, notifications and auto-reconnect.

Why a separate module and thread: `bleak` is built on asyncio and needs a
running event loop, while rclpy runs its own executor loop. Running both in
one thread would let a slow BLE call (a 10 s scan, a hung connect) freeze
every ROS callback. So `PolarBleWorker` owns a private asyncio loop on a
dedicated thread and communicates with the ROS node only through a
thread-safe `queue.Queue`:

    ("sample", HrmSample)   one parsed HRM notification
    ("connected", bool)     link came up / went down

This module does not import rclpy, so the reconnect logic can be tested with
a fake BLE client (see test/test_ble_worker.py).

Reconnect state machine (each transition is logged at INFO as
"[polar_h10][state] OLD -> NEW"):

    IDLE -> SCANNING (only if no device_address; matches device_id if given) -> CONNECTING -> CONNECTED
         -> STREAMING (first notification arrives; backoff resets to 1 s)
         -> DISCONNECTED (BleakError / CancelledError / device disconnect /
                          no notification for notification_timeout_s)
         -> BACKOFF (wait 1, 2, 4 ... s, capped at reconnect_backoff_max_s)
         -> SCANNING or CONNECTING again, forever, until stop() is called.
"""
import asyncio
import queue
import threading
import time
from typing import Optional

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

from polar_h10_ros.hrm_parser import parse_hrm

HR_SERVICE_UUID = '0000180d-0000-1000-8000-00805f9b34fb'
HRM_CHAR_UUID = '00002a37-0000-1000-8000-00805f9b34fb'
DEVICE_NAME_PREFIX = 'Polar H10'

SCAN_TIMEOUT_S = 10.0
CONNECT_TIMEOUT_S = 15.0
WATCHDOG_PERIOD_S = 0.25


class PolarLinkError(Exception):
    """Base class for link problems we detect ourselves (vs. BleakError from bleak)."""


class DeviceNotFound(PolarLinkError):
    pass


class DeviceDisconnected(PolarLinkError):
    pass


class NotificationTimeout(PolarLinkError):
    pass


def is_polar_h10(device, adv) -> bool:
    name = (adv.local_name if adv is not None else None) or device.name or ''
    return name.startswith(DEVICE_NAME_PREFIX)


def make_device_filter(device_id: str = ''):
    """Scan filter: any Polar H10, or only the one whose name ends in `device_id`.

    The advertised name is e.g. "Polar H10 18D51C3F". It is the same on macOS,
    Windows and Linux, unlike the address (MAC vs. CoreBluetooth UUID).
    """
    wanted = device_id.strip().upper()

    def _filter(device, adv) -> bool:
        if not is_polar_h10(device, adv):
            return False
        if not wanted:
            return True
        name = (adv.local_name if adv is not None else None) or device.name or ''
        return name.strip().upper().endswith(wanted)

    return _filter


class PolarBleWorker:
    def __init__(self, out_queue: queue.Queue, logger, device_address: str = '', device_id: str = '',
                 notification_timeout_s: float = 5.0, reconnect_backoff_max_s: float = 30.0,
                 reconnect_backoff_initial_s: float = 1.0, scan_timeout_s: float = SCAN_TIMEOUT_S,
                 client_factory=BleakClient, scanner=BleakScanner):
        self._queue = out_queue
        self._log = logger
        self._device_address = device_address
        self._device_id = device_id
        self._notification_timeout_s = notification_timeout_s
        self._backoff_initial_s = reconnect_backoff_initial_s
        self._backoff_max_s = reconnect_backoff_max_s
        self._scan_timeout_s = scan_timeout_s
        self._client_factory = client_factory
        self._scanner = scanner

        self._state = 'IDLE'
        self._backoff_s = reconnect_backoff_initial_s
        self._last_notify = 0.0
        self._streaming = False
        self._link_lost = False

        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop: Optional[asyncio.Event] = None
        self._ready = threading.Event()

    # ---- called from the ROS thread -------------------------------------------------

    def start(self) -> None:
        self._thread = threading.Thread(target=self._thread_main, name='polar_h10_ble',
                                        daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 5.0) -> None:
        """Ask the BLE loop to disconnect cleanly and wait for the thread to exit."""
        if self._thread is None:
            return
        if self._ready.wait(timeout=1.0):
            try:
                self._loop.call_soon_threadsafe(self._stop.set)
            except RuntimeError:
                pass  # loop already closed
        self._thread.join(timeout=timeout_s)
        if self._thread.is_alive():
            self._log.warning('[polar_h10][ble] worker thread did not exit within '
                              f'{timeout_s:.0f}s; abandoning it (daemon thread)')

    # ---- everything below runs on the BLE thread ------------------------------------

    def _thread_main(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop = asyncio.Event()
        self._ready.set()
        try:
            self._loop.run_until_complete(self._run())
        finally:
            self._loop.close()

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                await self._connect_and_stream()
            except asyncio.CancelledError:
                # bleak can surface a dropped link as CancelledError. We never cancel
                # this task to shut down (we use self._stop), so treat it as a drop.
                self._log.warning('[polar_h10][ble] link cancelled (CancelledError)')
            except (BleakError, PolarLinkError, asyncio.TimeoutError, OSError) as exc:
                self._log.warning(f'[polar_h10][ble] {type(exc).__name__}: {exc}')
            except Exception as exc:  # never let the BLE thread die silently
                self._log.error(f'[polar_h10][ble] unexpected {type(exc).__name__}: {exc}')

            if self._stop.is_set():
                break
            wait_s = self._backoff_s
            self._set_state('BACKOFF', f'retrying in {wait_s:g}s')
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=wait_s)
            except asyncio.TimeoutError:
                pass
            self._backoff_s = min(self._backoff_s * 2, self._backoff_max_s)
        self._set_state('STOPPED')

    async def _connect_and_stream(self) -> None:
        target = self._device_address
        label = target
        if not target:
            what = (f'"{DEVICE_NAME_PREFIX} {self._device_id}"' if self._device_id
                    else f'"{DEVICE_NAME_PREFIX}*"')
            self._set_state('SCANNING', f'up to {self._scan_timeout_s:.0f}s for {what}')
            device = await self._scanner.find_device_by_filter(
                make_device_filter(self._device_id), timeout=self._scan_timeout_s)
            if device is None:
                raise DeviceNotFound(f'no device named {what} found '
                                     '(is the strap worn and not paired to a phone app?)')
            target = device
            label = f'{device.name} [{device.address}]'

        self._set_state('CONNECTING', label)
        self._link_lost = False
        self._streaming = False
        client = self._client_factory(target, disconnected_callback=self._on_disconnect,
                                      timeout=CONNECT_TIMEOUT_S)
        async with client:  # connects on enter, disconnects on exit
            await client.start_notify(HRM_CHAR_UUID, self._on_notify)
            self._last_notify = time.monotonic()
            self._set_state('CONNECTED', label)
            self._emit(('connected', True))
            try:
                await self._watchdog()
                try:
                    await client.stop_notify(HRM_CHAR_UUID)
                except (BleakError, OSError):
                    pass
            finally:
                self._emit(('connected', False))
                self._set_state('DISCONNECTED')

    async def _watchdog(self) -> None:
        """Return when stop is requested; raise when the link is dead."""
        while not self._stop.is_set():
            await asyncio.sleep(WATCHDOG_PERIOD_S)
            if self._link_lost:
                raise DeviceDisconnected('device reported disconnect')
            silence_s = time.monotonic() - self._last_notify
            if silence_s > self._notification_timeout_s:
                raise NotificationTimeout(f'no HR notification for {silence_s:.1f}s '
                                          f'(limit {self._notification_timeout_s:.1f}s)')

    def _on_notify(self, _sender, data: bytearray) -> None:
        self._last_notify = time.monotonic()
        try:
            sample = parse_hrm(data)
        except ValueError as exc:
            self._log.warning(f'[polar_h10][ble] dropping malformed packet: {exc}')
            return
        if not self._streaming:
            self._streaming = True
            self._backoff_s = self._backoff_initial_s  # healthy link -> reset backoff
            self._set_state('STREAMING')
        self._emit(('sample', sample))

    def _on_disconnect(self, _client) -> None:
        # Just set a flag; the watchdog notices within WATCHDOG_PERIOD_S and raises.
        self._link_lost = True

    def _emit(self, item) -> None:
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            self._log.warning('[polar_h10][ble] output queue full; dropping item '
                              '(is the ROS node spinning?)')

    def _set_state(self, new_state: str, detail: str = '') -> None:
        old, self._state = self._state, new_state
        suffix = f' ({detail})' if detail else ''
        self._log.info(f'[polar_h10][state] {old} -> {new_state}{suffix}')
