#!/usr/bin/env python3
"""Pepper handshake over ROS 2 (needs naoqi_driver2 running and connected).

    ros2 launch naoqi_driver naoqi_driver.launch.py nao_ip:=<PEPPER_IP>
    python3 pepper_handshake.py

Sequence:
  1. "Hi, I am Pepper."                     (arm stays down)
  2. "Nice to meet you!" + arm comes up      (starts together)
  3. Arm stays up, hand open, until a handshake is detected:
       - a touch on the right hand  (/hand_touch), or
       - someone moving the arm     (/joint_states differs from the pose)
  4. Hand closes, "Thanks for the handshake!", arm goes back down.

Fixes vs. the first version:
  - It published to /stiffness, which naoqi_driver2 does not have, so that did
    nothing. The robot must be awake instead (wakeUp, see README).
  - /speech is fire-and-forget: the driver starts speaking and returns at once,
    with no "done" signal. The old code waited 1 s and raised the arm while
    the sentence (and TTS start-up delay) was still running, so the arm came
    first. Speech is now split and timed per word.
  - It held for a fixed 10 s and never looked for a handshake.
  - It re-sent the arm pose every 0.2 s, which fights the person shaking it.
    Now the pose is sent once and only refreshed every few seconds.
  - It waited for /speech discovery but not /joint_angles, so the first arm
    command could be lost.
"""
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from naoqi_bridge_msgs.msg import HandTouch, JointAnglesWithSpeed

ARM_JOINTS = ['RShoulderPitch', 'RShoulderRoll', 'RElbowYaw', 'RElbowRoll', 'RWristYaw']
OFFER_POSE = [0.2, -0.1, 1.2, 0.8, 0.0]    # arm forward, elbow bent
REST_POSE = [1.5, -0.1, 1.2, 0.5, 0.0]
ARM_SPEED = 0.15                           # fraction of max speed

# Tuning
SECONDS_PER_WORD = 0.40      # rough TTS pace, used to know when a phrase ends
TTS_START_DELAY_S = 0.6      # time between publishing /speech and sound starting
SETTLE_S = 3.0               # time for the arm to reach the pose before watching it
PUSH_THRESHOLD_RAD = 0.12    # how far someone must move the arm to count
PUSH_HOLD_S = 0.2            # ... for at least this long
REFRESH_POSE_S = 3.0         # re-send the pose this often while waiting
MAX_WAIT_S = 120.0           # safety: lower the arm after this long (0 = never)

RIGHT_HAND_SENSORS = (HandTouch.RIGHT_BACK, HandTouch.RIGHT_LEFT, HandTouch.RIGHT_RIGHT)


class PepperHandshake(Node):
    def __init__(self):
        super().__init__('pepper_handshake')
        self.speech_pub = self.create_publisher(String, '/speech', 10)
        self.joint_pub = self.create_publisher(JointAnglesWithSpeed, '/joint_angles', 10)
        self.create_subscription(HandTouch, '/hand_touch', self._on_touch, 10)
        self.create_subscription(JointState, '/joint_states', self._on_joints,
                                 qos_profile_sensor_data)
        self.touched = False
        self.joints = {}

    # ---- inputs ---------------------------------------------------------------
    def _on_touch(self, msg):
        if msg.hand in RIGHT_HAND_SENSORS and msg.state == HandTouch.STATE_PRESSED:
            self.touched = True

    def _on_joints(self, msg):
        self.joints = dict(zip(msg.name, msg.position))

    def wait(self, seconds):
        """Sleep while still processing incoming messages."""
        end = time.time() + seconds
        while rclpy.ok() and time.time() < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    def wait_for_driver(self, timeout_s=10.0):
        end = time.time() + timeout_s
        while time.time() < end:
            rclpy.spin_once(self, timeout_sec=0.1)
            if (self.speech_pub.get_subscription_count() and
                    self.joint_pub.get_subscription_count() and self.joints):
                return True
        return False

    # ---- outputs --------------------------------------------------------------
    def speak(self, text):
        """Start speaking; return the estimated seconds until the phrase ends."""
        self.speech_pub.publish(String(data=text))
        self.get_logger().info(f'Pepper says: "{text}"')
        return TTS_START_DELAY_S + SECONDS_PER_WORD * len(text.split())

    def arm(self, pose, hand_open):
        cmd = JointAnglesWithSpeed()
        cmd.joint_names = ARM_JOINTS + ['RHand']
        cmd.joint_angles = list(pose) + [1.0 if hand_open else 0.2]
        cmd.speed = ARM_SPEED
        cmd.relative = 0
        self.joint_pub.publish(cmd)

    # ---- handshake detection ---------------------------------------------------
    def arm_pushed(self):
        """True if someone is holding/moving the arm away from the offer pose."""
        for name, target in zip(ARM_JOINTS[:2] + ARM_JOINTS[3:4],
                                [OFFER_POSE[0], OFFER_POSE[1], OFFER_POSE[3]]):
            if name in self.joints and abs(self.joints[name] - target) > PUSH_THRESHOLD_RAD:
                return True
        return False

    def wait_for_handshake(self):
        self.touched = False
        self.wait(SETTLE_S)
        self.touched = False           # ignore anything during the raise
        start = last_refresh = time.time()
        pushed_since = None
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)
            now = time.time()
            if self.touched:
                self.get_logger().info('Handshake: hand touched')
                return True
            if self.arm_pushed():
                pushed_since = pushed_since or now
                if now - pushed_since >= PUSH_HOLD_S:
                    self.get_logger().info('Handshake: arm moved by a person')
                    return True
            else:
                pushed_since = None
                if now - last_refresh > REFRESH_POSE_S:   # hold against Autonomous Life
                    self.arm(OFFER_POSE, hand_open=True)
                    last_refresh = now
            if MAX_WAIT_S and now - start > MAX_WAIT_S:
                self.get_logger().info('No handshake; lowering arm')
                return False
        return False


def main(args=None):
    rclpy.init(args=args)
    node = PepperHandshake()

    if not node.wait_for_driver():
        node.get_logger().error('naoqi_driver not found (no /speech, /joint_angles '
                                'or /joint_states). Is the driver running?')
        node.destroy_node()
        rclpy.shutdown()
        return

    try:
        node.wait(node.speak('Hi, I am Pepper.'))
        node.speak('Nice to meet you!')
        node.arm(OFFER_POSE, hand_open=True)       # arm rises while she says it

        shook = node.wait_for_handshake()

        if shook:
            node.arm(OFFER_POSE, hand_open=False)  # close hand around theirs
            node.wait(node.speak('Thanks for the handshake!'))
            node.arm(OFFER_POSE, hand_open=True)   # let go
            node.wait(0.8)
        node.arm(REST_POSE, hand_open=False)
        node.wait(2.0)
    except KeyboardInterrupt:
        node.arm(REST_POSE, hand_open=False)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
