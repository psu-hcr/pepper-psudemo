import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
import asyncio
from bleak import BleakClient
import threading

# TODO: Replace these placeholders with your 4 Polar Sensor MAC addresses
POLAR_MACS = {
    'polar_1': 'XX:XX:XX:XX:XX:X1',
    'polar_2': 'XX:XX:XX:XX:XX:X2',
    'polar_3': 'XX:XX:XX:XX:XX:X3',
    'polar_4': 'XX:XX:XX:XX:XX:X4',
}

# Standard BLE Heart Rate Measurement Characteristic UUID
HR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

class MultiPolarHRNode(Node):
    def __init__(self):
        super().__init__('multi_polar_hr_node')
        
        # Create a dictionary of publishers for each sensor topic (/polar_1/hr, /polar_2/hr, etc.)
        self.publishers_map = {}
        for sensor_id in POLAR_MACS.keys():
            topic_name = f'/{sensor_id}/hr'
            self.publishers_map[sensor_id] = self.create_publisher(Int32, topic_name, 10)
            self.get_logger().info(f'Initialized topic publisher: {topic_name}')

    def publish_hr(self, sensor_id: str, hr_val: int):
        msg = Int32()
        msg.data = hr_val
        if sensor_id in self.publishers_map:
            self.publishers_map[sensor_id].publish(msg)
            self.get_logger().debug(f'[{sensor_id}] HR: {hr_val} BPM')


def make_hr_callback(sensor_id: str, node: MultiPolarHRNode):
    """Factory function to generate a distinct callback for each sensor."""
    def callback(sender, data: bytearray):
        # Decode standard BLE HR data: byte 0 is flags, byte 1 is HR integer value
        if len(data) > 1:
            hr_val = data[1]
            node.publish_hr(sensor_id, hr_val)
    return callback


async def connect_and_stream_sensor(sensor_id: str, mac_address: str, node: MultiPolarHRNode):
    """Asynchronously maintains connection and notification stream for a single sensor."""
    callback = make_hr_callback(sensor_id, node)
    
    while rclpy.ok():
        try:
            node.get_logger().info(f'[{sensor_id}] Attempting connection to {mac_address}...')
            async with BleakClient(mac_address, timeout=10.0) as client:
                if client.is_connected:
                    node.get_logger().info(f'[{sensor_id}] Connected! Starting HR stream...')
                    await client.start_notify(HR_UUID, callback)
                    
                    # Keep connection active while ROS 2 is running and client stays connected
                    while rclpy.ok() and client.is_connected:
                        await asyncio.sleep(1.0)
                        
                    node.get_logger().warn(f'[{sensor_id}] Connection dropped.')
        except Exception as e:
            node.get_logger().error(f'[{sensor_id}] Connection error: {e}')
            
        # Brief retry delay before attempting reconnection
        if rclpy.ok():
            await asyncio.sleep(5.0)


async def run_ble_loop(node: MultiPolarHRNode):
    """Spawns concurrent task loops for all 4 sensors."""
    tasks = [
        connect_and_stream_sensor(sensor_id, mac, node)
        for sensor_id, mac in POLAR_MACS.items()
    ]
    await asyncio.gather(*tasks)


def main(args=None):
    rclpy.init(args=args)
    ros_node = MultiPolarHRNode()

    # Run the BLE asyncio loop in a separate daemon thread to avoid blocking ROS 2
    def ble_thread_worker():
        asyncio.run(run_ble_loop(ros_node))

    ble_thread = threading.Thread(target=ble_thread_worker, daemon=True)
    ble_thread.start()

    try:
        rclpy.spin(ros_node)
    except KeyboardInterrupt:
        pass
    finally:
        ros_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
