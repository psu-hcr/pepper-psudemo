import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import String
from naoqi_bridge_msgs.action import Listen

class WeArePennState(Node):
    def __init__(self):
        super().__init__('we_are_penn_state')
        # Publisher to make Pepper speak
        self.speech_pub = self.create_publisher(String, '/speech', 10)
        # Action Client to make Pepper listen
        self.listen_client = ActionClient(self, Listen, '/listen')
        self.send_listen_goal()

    def send_listen_goal(self):
        self.listen_client.wait_for_server()
        goal_msg = Listen.Goal()
        goal_msg.expected = ["we are"]
        goal_msg.language = "en"
        
        self.get_logger().info("Listening for 'we are'...")
        self.send_goal_future = self.listen_client.send_goal_async(goal_msg)
        self.send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            return
        # Wait for the recognized speech result
        self.result_future = goal_handle.get_result_async()
        self.result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        self.get_logger().info("Heard it! Replying...")
        msg = String()
        msg.data = "Penn State!"
        self.speech_pub.publish(msg)
        
        # Loop back to listen again
        self.send_listen_goal()

def main(args=None):
    rclpy.init(args=args)
    node = WeArePennState()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
