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
  - Runs until Ctrl+C

This polls ALMemory for speech, touch, and sound localization instead of
registering ALBroker/ALModule event callbacks -- those callbacks require
Pepper to open a new connection back into this machine, which doesn't
reliably work in this environment. Polling only makes outbound calls, same
as everything else here.

NAOqi:
  Pepper NAOqi 2.5.x
  Python 2.7
"""

from naoqi import ALProxy
import time
import math
import sys


ROBOT_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.101"
PORT = 9559

RARM_JOINTS = [
    "RShoulderPitch",
    "RShoulderRoll",
    "RElbowYaw",
    "RElbowRoll",
    "RWristYaw"
]

REST_ANGLES = [1.4, -0.1, 1.2, 0.5, 0.0]
HANDSHAKE_ANGLES = [1.0, -0.2, 1.5, 0.8, 0.0]
HIGH_FIVE_ANGLES = [-1.0, -0.25, 1.3, 0.6, 0.0]

TOUCH_KEYS = [
    "HandRightBackTouched",
    "HandRightLeftTouched",
    "HandRightRightTouched"
]

VOCABULARY = ["we are", "high five"]
ASR_NAME = "RADDDemoASR"


# ---------------------------------------------------------------------------
# Introduction
# ---------------------------------------------------------------------------

def introduce(motion, tts, posture):

    print "Pepper is introducing itself..."

    motion.wakeUp()

    try:
        posture.goToPosture("StandInit", 0.8)
    except Exception:
        pass

    motion.setStiffnesses("RArm", 1.0)

    # Start the wave in the background so speech and motion occur
    # simultaneously.
    wave_id = motion.post.angleInterpolation(
        RARM_JOINTS,
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

    tts.say(
        "Hello! I am Pepper. "
        "I am from the Human-Centered Robotics Lab "
        "at Penn State."
    )

    try:
        motion.wait(wave_id, 0)
    except Exception:
        pass

    lower_right_arm(motion)


def lower_right_arm(motion):

    try:
        motion.angleInterpolationWithSpeed(RARM_JOINTS, REST_ANGLES, 0.2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Speech recognition
# ---------------------------------------------------------------------------

def turn_toward_speaker(motion, memory):

    try:
        data = memory.getData("ALSoundLocalization/SoundLocated")
    except Exception:
        return

    try:
        azimuth = data[1][0]
        confidence = data[1][2]
    except Exception:
        return

    if confidence < 0.2:
        print "No recent sound localization available."
        return

    print "Turning head toward speaker: %.1f degrees" % (
        math.degrees(azimuth)
    )

    max_yaw = math.radians(80.0)

    if azimuth > max_yaw:
        azimuth = max_yaw

    if azimuth < -max_yaw:
        azimuth = -max_yaw

    motion.setStiffnesses("Head", 1.0)
    motion.angleInterpolationWithSpeed(["HeadYaw"], [azimuth], 0.25)


# ---------------------------------------------------------------------------
# Right-hand touch / handshake
# ---------------------------------------------------------------------------

def handshake(motion, tts):

    print "Right hand touched -- handshake!"

    motion.setStiffnesses("RArm", 1.0)

    motion.angleInterpolationWithSpeed(RARM_JOINTS, HANDSHAKE_ANGLES, 0.25)

    # Three gentle handshake motions.
    motion.angleInterpolation(
        "RElbowRoll",
        [0.65, 0.85, 0.65, 0.85, 0.65],
        [0.3, 0.6, 0.9, 1.2, 1.5],
        True
    )

    tts.say("Nice to meet you!")

    # Keep the hand held out for a moment so a person actually has time to
    # grab and shake it, instead of retracting immediately.
    time.sleep(3)

    lower_right_arm(motion)


# ---------------------------------------------------------------------------
# High five
# ---------------------------------------------------------------------------

def raise_right_hand(motion, tts):

    print "High five!"

    motion.setStiffnesses("RArm", 1.0)

    motion.angleInterpolationWithSpeed(RARM_JOINTS, HIGH_FIVE_ANGLES, 0.25)

    tts.say("High five!")

    time.sleep(3.0)

    lower_right_arm(motion)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    print "Connecting to Pepper at %s:%d" % (ROBOT_IP, PORT)

    motion = ALProxy("ALMotion", ROBOT_IP, PORT)
    tts = ALProxy("ALTextToSpeech", ROBOT_IP, PORT)
    asr = ALProxy("ALSpeechRecognition", ROBOT_IP, PORT)
    memory = ALProxy("ALMemory", ROBOT_IP, PORT)
    posture = ALProxy("ALRobotPosture", ROBOT_IP, PORT)
    life = ALProxy("ALAutonomousLife", ROBOT_IP, PORT)
    background_movement = ALProxy("ALBackgroundMovement", ROBOT_IP, PORT)

    # Disabled once here and left disabled -- Autonomous Life (Background
    # Movement, Basic Awareness, etc.) otherwise fights any pose we hold
    # manually.
    if life.getState() != "disabled":
        life.setState("disabled")
    print "ALAutonomousLife state: %s" % life.getState()

    background_movement.setEnabled(False)

    # Basic Awareness can have its own enable flag independent of the
    # Autonomous Life state on some NAOqi versions, and Breathing is a
    # separate idle-sway animation on ALMotion that Autonomous Life doesn't
    # control at all -- turn both off explicitly so nothing but sound
    # localization and the gestures below can move the robot.
    try:
        basic_awareness = ALProxy("ALBasicAwareness", ROBOT_IP, PORT)
        basic_awareness.setEnabled(False)
    except Exception as e:
        print "Could not disable Basic Awareness: %s" % e

    try:
        motion.setBreathEnabled("Body", False)
    except Exception as e:
        print "Could not disable breathing: %s" % e

    # Guard against a leftover subscription from a previous run, and pause
    # the ASR engine so setLanguage/setVocabulary are allowed to run (NAOqi
    # rejects those calls while the engine is actively subscribed).
    try:
        asr.unsubscribe(ASR_NAME)
    except Exception:
        pass

    asr.pause(True)
    asr.setLanguage("English")
    asr.setVocabulary(VOCABULARY, False)
    asr.pause(False)

    asr.subscribe(ASR_NAME)

    # Seed the memory keys we poll so getData() never hits one that doesn't
    # exist yet.
    for key in TOUCH_KEYS:
        try:
            memory.getData(key)
        except Exception:
            memory.insertData(key, 0.0)

    try:
        memory.getData("WordRecognized")
    except Exception:
        memory.insertData("WordRecognized", ["", 0.0])

    introduce(motion, tts, posture)

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

    try:
        while True:

            # Check speech recognition.
            data = memory.getData("WordRecognized")

            if data and len(data) >= 2:
                word = data[0]
                confidence = data[1]

                if word:
                    print "Heard: %s (%.2f)" % (word, confidence)

                    if confidence > 0.35:
                        if word == "we are":
                            print "Responding to 'we are'"
                            turn_toward_speaker(motion, memory)
                            tts.say("Penn State")
                        elif word == "high five":
                            raise_right_hand(motion, tts)

                    # Clear it so the same recognition event doesn't keep
                    # re-triggering on every loop iteration.
                    memory.insertData("WordRecognized", ["", 0.0])

            # Check touch.
            for key in TOUCH_KEYS:
                if memory.getData(key) == 1.0:
                    handshake(motion, tts)
                    memory.insertData(key, 0.0)
                    break

            time.sleep(0.2)

    except KeyboardInterrupt:

        print ""
        print "Demo interrupted by a user via keyboard."

    except Exception as e:

        print "An error occurred:"
        print e

    finally:

        try:
            asr.unsubscribe(ASR_NAME)
        except Exception:
            pass

        try:
            motion.killTasks()
        except Exception:
            pass
