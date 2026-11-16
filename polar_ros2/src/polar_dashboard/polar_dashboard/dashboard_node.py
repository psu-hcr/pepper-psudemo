"""Web dashboard server for the Polar H10 straps.

Subscribes to /<name>/polar_h10/{heart_rate,rr_intervals,sensor_contact,connected}
for every sensor in config/sensors.yaml and serves:

  GET /            the dashboard page (web/index.html)
  GET /events      Server-Sent Events stream, one JSON snapshot twice a second
  GET /api/state   the same snapshot once (handy for debugging with curl)

Everything is plain HTTP with no third-party packages and no internet access
needed, so a TV browser on the same Wi-Fi just opens http://<laptop-ip>:8765.
Display only: this is not a medical device.
"""
import json
import math
import os
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.qos import QoSPresetProfiles
from std_msgs.msg import Bool, Float32MultiArray, Int32

HISTORY_S = 180          # seconds of heart-rate history sent to the page
STALE_S = 5.0            # no sample for this long -> "no signal"
SNAPSHOT_PERIOD_S = 0.5


class SensorState:
    def __init__(self, name, device_id):
        self.name = name
        self.device_id = device_id
        self.bpm = None
        self.last_t = None
        self.contact = None
        self.connected = False
        self.hist = deque()           # (monotonic time, bpm)
        self.rr = deque(maxlen=40)    # seconds
        self.n = 0
        self.total = 0
        self.lo = None
        self.hi = None

    def add_hr(self, bpm, now):
        self.bpm, self.last_t = bpm, now
        self.hist.append((now, bpm))
        while self.hist and now - self.hist[0][0] > HISTORY_S:
            self.hist.popleft()
        if bpm > 0:
            self.n += 1
            self.total += bpm
            self.lo = bpm if self.lo is None else min(self.lo, bpm)
            self.hi = bpm if self.hi is None else max(self.hi, bpm)

    def rmssd_ms(self):
        rr = list(self.rr)
        if len(rr) < 6:
            return None
        d = [(b - a) * 1000.0 for a, b in zip(rr, rr[1:])]
        return round(math.sqrt(sum(x * x for x in d) / len(d)), 1)

    def snapshot(self, now):
        age = None if self.last_t is None else now - self.last_t
        live = age is not None and age < STALE_S
        return {
            'name': self.name,
            'device_id': self.device_id,
            'bpm': self.bpm if live else None,
            'age_s': None if age is None else round(age, 1),
            'live': live,
            'connected': self.connected,
            'contact': self.contact,
            'avg': round(self.total / self.n) if self.n else None,
            'min': self.lo,
            'max': self.hi,
            'rmssd_ms': self.rmssd_ms() if live else None,
            'history': [[round(t - now, 1), b] for t, b in self.hist if b > 0],
        }


class DashboardNode(Node):
    def __init__(self):
        super().__init__('polar_dashboard')
        self.declare_parameter('port', 8765)
        self.declare_parameter('sensors_file', '')
        self.declare_parameter('title', 'Heart rate')
        self.declare_parameter('elevated_bpm', 110)
        self.declare_parameter('high_bpm', 140)

        sensors_file = self.get_parameter('sensors_file').value or os.path.join(
            get_package_share_directory('polar_h10_ros'), 'config', 'sensors.yaml')
        with open(sensors_file) as f:
            sensors = yaml.safe_load(f)['sensors']

        self._lock = threading.Lock()
        self._states = {s['name']: SensorState(s['name'], s.get('device_id', '')) for s in sensors}
        self._config = {
            'title': self.get_parameter('title').value,
            'elevated_bpm': int(self.get_parameter('elevated_bpm').value),
            'high_bpm': int(self.get_parameter('high_bpm').value),
        }

        qos = QoSPresetProfiles.SENSOR_DATA.value
        for name in self._states:
            self.create_subscription(Int32, f'/{name}/polar_h10/heart_rate',
                                     lambda m, n=name: self._on_hr(n, m), qos)
            self.create_subscription(Float32MultiArray, f'/{name}/polar_h10/rr_intervals',
                                     lambda m, n=name: self._on_rr(n, m), qos)
            self.create_subscription(Bool, f'/{name}/polar_h10/sensor_contact',
                                     lambda m, n=name: self._on_contact(n, m), qos)
            self.create_subscription(Bool, f'/{name}/polar_h10/connected',
                                     lambda m, n=name: self._on_connected(n, m), 10)

        web_dir = os.path.join(get_package_share_directory('polar_dashboard'), 'web')
        port = int(self.get_parameter('port').value)
        self._server = ThreadingHTTPServer(('0.0.0.0', port), self._make_handler(web_dir))
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        self.get_logger().info(
            f'[dashboard] {len(self._states)} sensors: {", ".join(self._states)}. '
            f'Open http://localhost:{port}  (TV: http://<this-laptop-ip>:{port})')

    # ---- ROS callbacks (rclpy thread) ----
    def _on_hr(self, name, msg):
        with self._lock:
            self._states[name].add_hr(int(msg.data), time.monotonic())

    def _on_rr(self, name, msg):
        with self._lock:
            self._states[name].rr.extend(float(x) for x in msg.data)

    def _on_contact(self, name, msg):
        with self._lock:
            self._states[name].contact = bool(msg.data)

    def _on_connected(self, name, msg):
        with self._lock:
            self._states[name].connected = bool(msg.data)

    # ---- HTTP (server threads) ----
    def snapshot(self):
        now = time.monotonic()
        with self._lock:
            sensors = [s.snapshot(now) for s in self._states.values()]
        return {'config': self._config, 'sensors': sensors}

    def _make_handler(self, web_dir):
        node = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, code, ctype, body):
                self.send_response(code)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                path = self.path.split('?')[0]
                if path in ('/', '/index.html'):
                    with open(os.path.join(web_dir, 'index.html'), 'rb') as f:
                        self._send(200, 'text/html; charset=utf-8', f.read())
                elif path == '/api/state':
                    self._send(200, 'application/json', json.dumps(node.snapshot()).encode())
                elif path == '/events':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    try:
                        while True:
                            payload = json.dumps(node.snapshot())
                            self.wfile.write(f'data: {payload}\n\n'.encode())
                            self.wfile.flush()
                            time.sleep(SNAPSHOT_PERIOD_S)
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        return
                else:
                    self._send(404, 'text/plain', b'not found')

        return Handler

    def shutdown(self):
        self._server.shutdown()
        self._server.server_close()


def main():
    rclpy.init()
    node = DashboardNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.shutdown()
    node.destroy_node()
    rclpy.try_shutdown()
