"""Mock Polar H10: publishes fake heart rate on the same topics as the real node.

Use it to build and test downstream nodes (e.g. the Pepper over-exertion
node) or rqt_plot / Foxglove layouts without wearing the strap. HR follows a
slow sine wave between 60 and 120 BPM. RR is derived from HR (60 / BPM
seconds). Contact and connected are always true. Topic names, message types
and QoS match polar_h10_node exactly, so subscribers can't tell the two apart.

Parameters:
  period_s       sine period in seconds (default 60.0)
  publish_rate_hz  samples per second (default 1.0, like the real strap)
"""
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSPresetProfiles
from std_msgs.msg import Bool, Float32MultiArray, Int32

HR_MIN_BPM = 60.0
HR_MAX_BPM = 120.0


class MockPolarH10Node(Node):
    def __init__(self):
        super().__init__('mock_polar_h10_node')
        self.declare_parameter('period_s', 60.0)
        self.declare_parameter('publish_rate_hz', 1.0)
        self.declare_parameter('publish_rr', True)
        self._period_s = self.get_parameter('period_s').value
        self._publish_rr = self.get_parameter('publish_rr').value
        rate_hz = self.get_parameter('publish_rate_hz').value

        sensor_qos = QoSPresetProfiles.SENSOR_DATA.value
        self._hr_pub = self.create_publisher(Int32, 'polar_h10/heart_rate', sensor_qos)
        self._rr_pub = self.create_publisher(Float32MultiArray, 'polar_h10/rr_intervals',
                                             sensor_qos)
        self._contact_pub = self.create_publisher(Bool, 'polar_h10/sensor_contact', sensor_qos)
        self._connected_pub = self.create_publisher(Bool, 'polar_h10/connected', 10)

        self._t0 = self.get_clock().now()
        self.create_timer(1.0 / rate_hz, self._tick)
        self.get_logger().info(
            f'[polar_h10][mock] SYNTHETIC data: {HR_MIN_BPM:.0f}-{HR_MAX_BPM:.0f} BPM sine, '
            f'period {self._period_s:.0f}s, {rate_hz:.1f} Hz')

    def _tick(self) -> None:
        t = (self.get_clock().now() - self._t0).nanoseconds * 1e-9
        mid = (HR_MIN_BPM + HR_MAX_BPM) / 2
        amp = (HR_MAX_BPM - HR_MIN_BPM) / 2
        bpm = int(round(mid + amp * math.sin(2 * math.pi * t / self._period_s)))

        self._hr_pub.publish(Int32(data=bpm))
        if self._publish_rr:
            self._rr_pub.publish(Float32MultiArray(data=[60.0 / bpm]))
        self._contact_pub.publish(Bool(data=True))
        self._connected_pub.publish(Bool(data=True))


def main(args=None):
    rclpy.init(args=args)
    node = MockPolarH10Node()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
