"""Publish the Mac webcam as sensor_msgs/Image on /camera/image_raw.

Parameters: device (int, 0 = built-in, 1 = iPhone via Continuity Camera, ...),
fps, width, height, frame_id.
First run: macOS asks for Camera permission for the app running the terminal.
"""
import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image


class MacCamera(Node):
    def __init__(self):
        super().__init__('mac_camera')
        self.declare_parameter('device', 0)
        self.declare_parameter('fps', 30.0)
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('frame_id', 'camera')
        dev = self.get_parameter('device').value
        self.cap = cv2.VideoCapture(dev, cv2.CAP_AVFOUNDATION)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.get_parameter('width').value)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.get_parameter('height').value)
        if not self.cap.isOpened():
            self.get_logger().error(
                f'Cannot open camera {dev}. Allow Camera access for your terminal '
                'in System Settings > Privacy & Security > Camera.')
        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, 'camera/image_raw', 10)
        self.create_timer(1.0 / self.get_parameter('fps').value, self.tick)

    def tick(self):
        ok, frame = self.cap.read()
        if not ok:
            return
        msg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.get_parameter('frame_id').value
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = MacCamera()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.cap.release()
    node.destroy_node()
    rclpy.try_shutdown()
