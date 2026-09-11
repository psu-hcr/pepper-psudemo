#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
Pepper Human-Centered Robotics Lab Demo

Pepper:
  - Introduces itself while waving
  - Says it is from the Human-Centered Robotics Lab at Penn State
  - Recognizes "we are" and responds "Penn State"
  - Turns its head toward the person who says "we are"
  - Responds to a touch on its right hand with a handshake motion
  - Recognizes "high five" and raises its right hand
  - Safely stops and releases stiffness on Ctrl+C

NAOqi:
  Pepper NAOqi 2.5.x
  Python 2.7
"""

from naoqi import ALProxy, ALModule, ALBroker
import time
import math
import sys


# ---------------------------------------------------------------------------
# Robot configuration
# ---------------------------------------------------------------------------

ROBOT_IP = "192.168.0.101"
PORT = 9559


# ---------------------------------------------------------------------------
# Demo module
# ---------------------------------------------------------------------------

class PepperDemo(ALModule):

    def __init__(self, name):
        ALModule.__init__(self, name)

        self.motion = ALProxy("ALMotion", ROBOT_IP, PORT)
        self.tts = ALProxy("ALTextToSpeech", ROBOT_IP, PORT)
        self.asr = ALProxy("ALSpeechRecognition", ROBOT_IP, PORT)
        self.memory = ALProxy("ALMemory", ROBOT_IP, PORT)
        self.sound = ALProxy("ALSoundLocalization", ROBOT_IP, PORT)
        self.posture = ALProxy("ALRobotPosture", ROBOT_IP, PORT)

        self.last_sound_azimuth = 0.0
        self.last_sound_time = 0.0

        # Subscribe to speech recognition.
        self.memory.subscribeToEvent(
            "WordRecognized",
            name,
            "onWordRecognized"
        )

        # Subscribe to right-hand touch events.
        self.memory.subscribeToEvent(
            "HandRightBackTouched",
            name,
            "onRightHandTouched"
        )

        self.memory.subscribeToEvent(
            "HandRightLeftTouched",
            name,
            "onRightHandTouched"
        )

        self.memory.subscribeToEvent(
            "HandRightRightTouched",
            name,
            "onRightHandTouched"
        )

        # Subscribe to sound localization.
        self.memory.subscribeToEvent(
            "ALSoundLocalization/SoundLocated",
            name,
            "onSoundLocated"
        )

        # Set up speech vocabulary.
        self.asr.setLanguage("English")

        vocabulary = [
            "we are",
            "high five"
        ]

        self.asr.setVocabulary(vocabulary, False)

    # -----------------------------------------------------------------------
    # Introduction
    # -----------------------------------------------------------------------

    def introduce(self):

        print "Pepper is introducing itself..."

        # Wake up and prepare Pepper.
        self.motion.wakeUp()

        try:
            self.posture.goToPosture("StandInit", 0.8)
        except Exception:
            pass

        # Start with the right arm down.
        self.motion.setStiffnesses("RArm", 1.0)

        # Start the wave in the background so speech and motion occur
        # simultaneously.
        wave_id = self.motion.post.angleInterpolation(
            ["RShoulderPitch",
             "RShoulderRoll",
             "RElbowYaw",
             "RElbowRoll",
             "RWristYaw"],

            [
                [1.4, 1.1, 1.1, 1.1, 1.4],
                [-0.2, -0.4, -0.4, -0.4, -0.2],
                [1.2, 1.2, 1.2, 1.2, 1.2],
                [0.7, 0.9, 0.7, 0.9, 0.7],
                [0.0, 0.5, -0.5, 0.5, 0.0]
            ],

            [
                [0.8, 1.2, 1.6, 2.0, 2.4],
                [0.8, 1.2, 1.6, 2.0, 2.4],
                [0.8, 1.2, 1.6, 2.0, 2.4],
                [0.8, 1.2, 1.6, 2.0, 2.4],
                [0.8, 1.2, 1.6, 2.0, 2.4]
            ],

            True
        )

        # Speech occurs while the wave is happening.
        self.tts.say(
            "Hello! I am Pepper. "
            "I am from the Human-Centered Robotics Lab "
            "at Penn State."
        )

        # Wait for the wave to finish.
        try:
            self.motion.wait(wave_id, 0)
        except Exception:
            pass

        # Return right arm to a comfortable position.
        self.lower_right_arm()

    # -----------------------------------------------------------------------
    # Speech recognition
    # -----------------------------------------------------------------------

    def start_speech_recognition(self):
        print "Starting speech recognition..."

        self.asr.subscribe("PepperDemoASR")

    def stop_speech_recognition(self):
        try:
            self.asr.unsubscribe("PepperDemoASR")
        except Exception:
            pass

    def onWordRecognized(self, event_name, value, subscriber_identifier):

        if not value:
            return

        try:
            word = value[0]
            confidence = value[1]
        except Exception:
            return

        word = word.lower()

        print "Recognized: %s (confidence %.2f)" % (
            word,
            confidence
        )

        # Ignore low-confidence recognition.
        if confidence < 0.35:
            return

        if word == "we are":

            print "Responding to 'we are'"

            # First turn toward the person who spoke.
            self.turn_toward_speaker()

            # Then complete the phrase.
            self.tts.say("Penn State")

        elif word == "high five":

            print "High five!"

            self.raise_right_hand()

    # -----------------------------------------------------------------------
    # Sound localization
    # -----------------------------------------------------------------------

    def onSoundLocated(self, event_name, value, subscriber_identifier):

        try:
            # SoundLocated format:
            #
            # [
            #   [time_sec, time_usec],
            #   [azimuth, elevation, confidence],
            #   [head position in torso frame],
            #   [head position in robot frame]
            # ]
            #
            # Azimuth is in radians.

            azimuth = value[1][0]
            confidence = value[1][2]

            if confidence > 0.2:
                self.last_sound_azimuth = azimuth
                self.last_sound_time = time.time()

        except Exception:
            pass

    def turn_toward_speaker(self):

        # Only use a recently localized sound.
        if time.time() - self.last_sound_time > 2.0:
            print "No recent sound localization available."
            return

        azimuth = self.last_sound_azimuth

        print "Turning head toward speaker: %.1f degrees" % (
            math.degrees(azimuth)
        )

        # Limit the motion to a reasonable range.
        max_yaw = math.radians(80.0)

        if azimuth > max_yaw:
            azimuth = max_yaw

        if azimuth < -max_yaw:
            azimuth = -max_yaw

        self.motion.setStiffnesses("Head", 1.0)

        self.motion.angleInterpolationWithSpeed(
            ["HeadYaw"],
            [azimuth],
            0.25
        )

    # -----------------------------------------------------------------------
    # Right-hand touch / handshake
    # -----------------------------------------------------------------------

    def onRightHandTouched(
            self,
            event_name,
            value,
            subscriber_identifier):

        # Only respond when the hand becomes touched.
        if value != 1.0:
            return

        print "Right hand touched -- handshake!"

        self.handshake()

    def handshake(self):

        self.motion.setStiffnesses("RArm", 1.0)

        # Move the arm into a handshake position.
        self.motion.angleInterpolationWithSpeed(
            [
                "RShoulderPitch",
                "RShoulderRoll",
                "RElbowYaw",
                "RElbowRoll",
                "RWristYaw"
            ],
            [
                1.0,
                -0.2,
                1.5,
                0.8,
                0.0
            ],
            0.25
        )

        # Three gentle handshake motions.
        self.motion.angleInterpolation(
            "RElbowRoll",
            [0.65, 0.85, 0.65, 0.85, 0.65],
            [0.3, 0.6, 0.9, 1.2, 1.5],
            True
        )

        self.lower_right_arm()

    # -----------------------------------------------------------------------
    # High five
    # -----------------------------------------------------------------------

    def raise_right_hand(self):

        self.motion.setStiffnesses("RArm", 1.0)

        # Raise right hand above shoulder height.
        self.motion.angleInterpolationWithSpeed(
            [
                "RShoulderPitch",
                "RShoulderRoll",
                "RElbowYaw",
                "RElbowRoll",
                "RWristYaw"
            ],
            [
                -1.0,
                -0.25,
                1.3,
                0.6,
                0.0
            ],
            0.25
        )

        # Keep hand raised for a moment.
        time.sleep(2.0)

        self.lower_right_arm()

    # -----------------------------------------------------------------------
    # Arm reset
    # -----------------------------------------------------------------------

    def lower_right_arm(self):

        try:
            self.motion.angleInterpolationWithSpeed(
                [
                    "RShoulderPitch",
                    "RShoulderRoll",
                    "RElbowYaw",
                    "RElbowRoll",
                    "RWristYaw"
                ],
                [
                    1.4,
                    -0.1,
                    1.2,
                    0.5,
                    0.0
                ],
                0.2
            )
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Safe shutdown
    # -----------------------------------------------------------------------

    def safe_shutdown(self):

        print "Stopping Pepper demo..."

        try:
            self.stop_speech_recognition()
        except Exception:
            pass

        try:
            self.memory.unsubscribeToEvent(
                "WordRecognized",
                self.getName()
            )
        except Exception:
            pass

        try:
            self.memory.unsubscribeToEvent(
                "HandRightBackTouched",
                self.getName()
            )
        except Exception:
            pass

        try:
            self.memory.unsubscribeToEvent(
                "HandRightLeftTouched",
                self.getName()
            )
        except Exception:
            pass

        try:
            self.memory.unsubscribeToEvent(
                "HandRightRightTouched",
                self.getName()
            )
        except Exception:
            pass

        try:
            self.memory.unsubscribeToEvent(
                "ALSoundLocalization/SoundLocated",
                self.getName()
            )
        except Exception:
            pass

        # Stop any outstanding motion tasks.
        try:
            self.motion.killTasks()
        except Exception:
            pass

        # Release stiffness so Pepper's motors enter a safe/rest state.
        try:
            self.motion.rest()
        except Exception:
            try:
                self.motion.setStiffnesses("Body", 0.0)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    broker = None
    demo = None

    try:

        print "Connecting to Pepper at %s:%d" % (ROBOT_IP, PORT)

        # Create a local broker so that Pepper can send event callbacks
        # to this Python process.
        broker = ALBroker(
            "PepperDemoBroker",
            "0.0.0.0",
            0,
            ROBOT_IP,
            PORT
        )

        demo = PepperDemo("PepperDemo")

        demo.introduce()

        demo.start_speech_recognition()

        print ""
        print "----------------------------------------"
        print "Pepper demo is running."
        print ""
        print 'Say "we are" for Pepper to respond: "Penn State".'
        print 'Say "high five" to raise Pepper\'s right hand.'
        print "Touch Pepper's right hand for a handshake."
        print ""
        print "Press Ctrl+C to stop the demo."
        print "----------------------------------------"
        print ""

        # Keep the program alive so that event callbacks can run.
        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:

        print ""
        print "Demo interrupted by a user via keyboard."

        if demo is not None:
            demo.safe_shutdown()

    except Exception as e:

        print "An error occurred:"
        print e

        if demo is not None:
            demo.safe_shutdown()

    finally:

        if broker is not None:
            try:
                broker.shutdown()
            except Exception:
                pass
