"""polar_h10_ros - Polar H10 BLE heart rate publisher for ROS 2.

Modules:
  hrm_parser          pure-Python Heart Rate Measurement packet parser (no ROS, no BLE)
  ble_worker          asyncio/bleak connection + reconnect state machine on its own thread (no ROS)
  polar_h10_node      the rclpy node: owns publishers, drains the worker's queue
  mock_polar_h10_node fake sine-wave HR on the same topics, for work without the strap

Keep this file import-free so tests can import the parser without rclpy.
"""
