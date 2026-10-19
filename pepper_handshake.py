import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32
from naoqi_bridge_msgs.msg import JointAnglesWithSpeed
import time

class PepperHandshake(Node):
    def __init__(self):
        super().__init__('pepper_handshake')
        
        # ROS 2 Topics
        self.speech_pub = self.create_publisher(String, '/speech', 10)
        self.joint_pub = self.create_publisher(JointAnglesWithSpeed, '/joint_angles', 10)
        self.stiffness_pub = self.create_publisher(Float32, '/stiffness', 10)
        
        self.get_logger().info("Pepper Handshake Node initialized.")

    def enable_stiffness(self):
        """Enforces full power to joints so Pepper holds positions against gravity."""
        stiff_msg = Float32()
        stiff_msg.data = 1.0
        for _ in range(5):
            self.stiffness_pub.publish(stiff_msg)
            time.sleep(0.05)

    def speak(self, text):
        """Waits for subscriber discovery before publishing speech to prevent message loss."""
        timeout = 5.0
        start = time.time()
        while self.speech_pub.get_subscription_count() == 0 and (time.time() - start) < timeout:
            time.sleep(0.1)
        
        msg = String()
        msg.data = text
        self.speech_pub.publish(msg)
        self.get_logger().info(f"Pepper speaking: '{text}'")

    def move_arm(self, open_hand=True):
        """Commands right arm posture for handshake posture."""
        cmd = JointAnglesWithSpeed()
        cmd.joint_names = [
            'RShoulderPitch',
            'RShoulderRoll',
            'RElbowYaw',
            'RElbowRoll',
            'RWristYaw',
            'RHand'
        ]
        # Handshake pose: arm forward, elbow angled, hand open (1.0)
        cmd.joint_angles = [
            0.2,   # Shoulder Pitch (Forward)
            -0.1,  # Shoulder Roll
            1.2,   # Elbow Yaw
            0.8,   # Elbow Roll
            0.0,   # Wrist Yaw
            1.0 if open_hand else 0.2  # Hand Open/Grasp
        ]
        cmd.speed = 0.15
        cmd.relative = 0
        self.joint_pub.publish(cmd)

    def rest_arm(self):
        """Returns right arm to resting position by body."""
        cmd = JointAnglesWithSpeed()
        cmd.joint_names = [
            'RShoulderPitch',
            'RShoulderRoll',
            'RElbowYaw',
            'RElbowRoll',
            'RWristYaw',
            'RHand'
        ]
        cmd.joint_angles = [1.5, -0.1, 1.2, 0.5, 0.0, 0.0]
        cmd.speed = 0.15
        cmd.relative = 0
        self.joint_pub.publish(cmd)

def main(args=None):
    rclpy.init(args=args)
    node = PepperHandshake()
    
    # 1. Enable Motor Stiffness
    node.enable_stiffness()
    time.sleep(0.5)
    
    # 2. Speak greeting
    node.speak("Hello! Nice to meet you. Let's shake hands.")
    time.sleep(1.0)
    
    # 3. Extend arm and keep re-publishing joint angles for 10 seconds
    node.get_logger().info("Holding handshake pose for 10 seconds...")
    hold_duration = 10.0
    start_time = time.time()
    
    while (time.time() - start_time) < hold_duration:
        node.move_arm(open_hand=True)
        time.sleep(0.2)  # Re-publish stream prevents Autonomous Life override
        
    # 4. Closing reaction
    node.speak("Thanks for the handshake!")
    node.move_arm(open_hand=False)
    time.sleep(1.5)
    
    # 5. Return arm to rest position
    node.get_logger().info("Returning arm to rest posture.")
    for _ in range(5):
        node.rest_arm()
        time.sleep(0.1)
        
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
