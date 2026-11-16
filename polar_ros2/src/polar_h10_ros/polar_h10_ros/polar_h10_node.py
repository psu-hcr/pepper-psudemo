"""ROS 2 node that publishes Polar H10 heart rate data.

This file is the ROS half. It declares parameters, creates publishers, and
starts a `PolarBleWorker` (ble_worker.py) that does all Bluetooth work on its
own thread. The worker drops results into a `queue.Queue`; a 50 Hz rclpy timer
drains that queue and publishes. The rclpy spin thread only ever does
non-blocking `get_nowait()` calls, so it can never stall on BLE I/O.

Topics (relative names, so a launch-file namespace still applies):
  polar_h10/heart_rate      std_msgs/Int32             SENSOR_DATA QoS
  polar_h10/rr_intervals    std_msgs/Float32MultiArray SENSOR_DATA QoS (seconds; may be empty)
  polar_h10/sensor_contact  std_msgs/Bool              SENSOR_DATA QoS
  polar_h10/connected       std_msgs/Bool              default reliable QoS,
                            published on every change and re-sent at 1 Hz so
                            subscribers that start late still learn the state.
"""
import queue

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSPresetProfiles
from std_msgs.msg import Bool, Float32MultiArray, Int32

from polar_h10_ros.ble_worker import PolarBleWorker

DRAIN_PERIOD_S = 0.02
CONNECTED_REPUBLISH_PERIOD_S = 1.0


class PolarH10Node(Node):
    def __init__(self):
        super().__init__('polar_h10_node')

        self.declare_parameter('device_address', '')
        self.declare_parameter('device_id', '')
        self.declare_parameter('reconnect_backoff_max_s', 30.0)
        self.declare_parameter('notification_timeout_s', 5.0)
        self.declare_parameter('publish_rr', True)

        device_address = self.get_parameter('device_address').value
        device_id = self.get_parameter('device_id').value
        backoff_max_s = self.get_parameter('reconnect_backoff_max_s').value
        notification_timeout_s = self.get_parameter('notification_timeout_s').value
        self._publish_rr = self.get_parameter('publish_rr').value

        # SENSOR_DATA = best-effort, keep last 5: a late or lost HR sample is
        # better dropped than retransmitted after newer ones.
        sensor_qos = QoSPresetProfiles.SENSOR_DATA.value
        self._hr_pub = self.create_publisher(Int32, 'polar_h10/heart_rate', sensor_qos)
        self._rr_pub = self.create_publisher(Float32MultiArray, 'polar_h10/rr_intervals',
                                             sensor_qos)
        self._contact_pub = self.create_publisher(Bool, 'polar_h10/sensor_contact', sensor_qos)
        self._connected_pub = self.create_publisher(Bool, 'polar_h10/connected', 10)

        self._connected = False
        self._queue = queue.Queue(maxsize=256)
        self.create_timer(DRAIN_PERIOD_S, self._drain_queue)
        self.create_timer(CONNECTED_REPUBLISH_PERIOD_S, self._publish_connected)
        self._publish_connected()

        self.get_logger().info(
            f'[polar_h10] starting: device_address="{device_address or "<scan>"}" device_id="{device_id}" '
            f'notification_timeout_s={notification_timeout_s} '
            f'reconnect_backoff_max_s={backoff_max_s} publish_rr={self._publish_rr}')

        self._worker = PolarBleWorker(
            out_queue=self._queue,
            logger=self.get_logger(),
            device_address=device_address,
            device_id=device_id,
            notification_timeout_s=notification_timeout_s,
            reconnect_backoff_max_s=backoff_max_s,
        )
        self._worker.start()

    def _drain_queue(self) -> None:
        while True:
            try:
                kind, payload = self._queue.get_nowait()
            except queue.Empty:
                return
            if kind == 'sample':
                self._publish_sample(payload)
            elif kind == 'connected':
                self._connected = payload
                self._publish_connected()

    def _publish_sample(self, sample) -> None:
        self._hr_pub.publish(Int32(data=sample.bpm))
        if self._publish_rr:
            self._rr_pub.publish(Float32MultiArray(data=list(sample.rr_intervals_s)))
        if sample.sensor_contact is not None:
            self._contact_pub.publish(Bool(data=sample.sensor_contact))

    def _publish_connected(self) -> None:
        self._connected_pub.publish(Bool(data=self._connected))

    def destroy_node(self):
        self._worker.stop()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = PolarH10Node()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
