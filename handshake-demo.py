#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
Pepper Handshake + "We Are" Demo

Pepper's arm stays down and stationary by default.

  - Say "handshake" -- Pepper raises its hand and offers it. Once touched,
    it shakes, says hello, waits, then lowers the arm and goes back to
    waiting.
  - Say "we are" -- Pepper responds "Penn State!" (same behavior as
    hellopepper.py), regardless of whether the hand is currently offered.

NAOqi:
  Pepper NAOqi 2.5.xJ
  Python 2.7
"""

from naoqi import ALProxy
import time
import math
import sys


ROBOT_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.101"
PORT = 9559

TOUCH_KEYS = [
    "HandRightBackTouched",
    "HandRightLeftTouched",
    "HandRightRightTouched"
]

ARM_JOINTS = [
    "RShoulderPitch",
    "RShoulderRoll",
    "RElbowYaw",
    "RElbowRoll",
    "RWristYaw"
]

HANDSHAKE_ANGLES = [1.0, -0.2, 1.5, 0.8, 0.0]
REST_ANGLES = [1.4, -0.1, 1.2, 0.5, 0.0]

VOCABULARY = ["handshake", "we are"]
ASR_NAME = "HandshakeDemoASR"
SOUND_NAME = "HandshakeDemoSound"

CONFIDENCE_THRESHOLD = 0.35


def check_word(memory):
    """Return the newly recognized word (if confidence is high enough),
    or None. Clears WordRecognized either way so the same event doesn't
    keep re-triggering on every loop iteration."""

    data = memory.getData("WordRecognized")

    if not data or len(data) < 2:
        return None

    word = data[0]
    confidence = data[1]

    if not word:
        return None

    memory.insertData("WordRecognized", ["", 0.0])

    if confidence > CONFIDENCE_THRESHOLD:
        return word

    return None


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
        return

    print "Turning body toward sound: %.1f degrees" % math.degrees(azimuth)

    # Rotate the whole body (the wheeled base) to face the sound source,
    # rather than just turning the head. moveTo(x, y, theta) with x=y=0 is
    # a pure in-place rotation by theta radians.
    motion.moveTo(0.0, 0.0, azimuth)

    # Keep the head centered relative to the body's new facing direction.
    motion.setStiffnesses("Head", 1.0)
    motion.angleInterpolationWithSpeed(["HeadYaw"], [0.0], 0.25)


def offer_hand(motion, tts):

    motion.angleInterpolationWithSpeed(ARM_JOINTS, HANDSHAKE_ANGLES, 0.25)
    tts.say("Here is my hand. Go ahead and shake it.")


def shake_hand(motion, tts):

    print "Hand touched -- shaking!"

    motion.angleInterpolation(
        "RElbowRoll",
        [0.65, 0.85, 0.65, 0.85, 0.65],
        [0.3, 0.6, 0.9, 1.2, 1.5],
        True
    )

    tts.say("Nice to meet you!")

    time.sleep(5.0)

    motion.angleInterpolationWithSpeed(ARM_JOINTS, REST_ANGLES, 0.2)


if __name__ == "__main__":

    print "Connecting to Pepper at %s:%d" % (ROBOT_IP, PORT)
    motion = ALProxy("ALMotion", ROBOT_IP, PORT)
    tts = ALProxy("ALTextToSpeech", ROBOT_IP, PORT)
    memory = ALProxy("ALMemory", ROBOT_IP, PORT)
    asr = ALProxy("ALSpeechRecognition", ROBOT_IP, PORT)
    sound = ALProxy("ALSoundLocalization", ROBOT_IP, PORT)
    life = ALProxy("ALAutonomousLife", ROBOT_IP, PORT)
    background_movement = ALProxy("ALBackgroundMovement", ROBOT_IP, PORT)
    tts.say(
                "Hello! I am Pepper. "
                "I am from the Human-Centered Robotics Lab "
                "at Penn State. "
                "Say 'we are', or say 'handshake' to shake my hand."
            )
    if life.getState() != "disabled":
        life.setState("disabled")
    print "ALAutonomousLife state: %s" % life.getState()

    background_movement.setEnabled(False)

    # Basic Awareness can have its own enable flag independent of the
    # Autonomous Life state on some NAOqi versions, and Breathing is a
    # separate idle-sway animation on ALMotion that Autonomous Life doesn't
    # control at all -- turn both off explicitly so the offered hand
    # actually stays put instead of slowly drifting back down.
    try:
        basic_awareness = ALProxy("ALBasicAwareness", ROBOT_IP, PORT)
        basic_awareness.setEnabled(False)
    except Exception as e:
        print "Could not disable Basic Awareness: %s" % e

    try:
        motion.setBreathEnabled("Body", False)
    except Exception as e:
        print "Could not disable breathing: %s" % e

    # Same speech recognition approach as hellopepper.py: setLanguage,
    # setVocabulary, subscribe, then poll WordRecognized. Guard against a
    # leftover subscription and pause first, since NAOqi rejects
    # setLanguage/setVocabulary while the ASR engine is actively subscribed.
    try:
        asr.unsubscribe(ASR_NAME)
    except Exception:
        pass

    asr.pause(True)
    asr.setLanguage("English")
    asr.setVocabulary(VOCABULARY, False)
    asr.pause(False)

    asr.subscribe(ASR_NAME)

    # Sound localization needs to be subscribed to before it publishes
    # ALSoundLocalization/SoundLocated to ALMemory.
    try:
        sound.unsubscribe(SOUND_NAME)
    except Exception:
        pass

    sound.subscribe(SOUND_NAME)

    for key in TOUCH_KEYS:
        try:
            memory.getData(key)
        except Exception:
            memory.insertData(key, 0.0)

    try:
        memory.getData("WordRecognized")
    except Exception:
        memory.insertData("WordRecognized", ["", 0.0])

    # Arm starts down/stationary -- it only moves once "handshake" is heard.
    motion.setStiffnesses("RArm", 1.0)
    motion.angleInterpolationWithSpeed(ARM_JOINTS, REST_ANGLES, 0.2)

    print "Staying stationary."
    print "Say 'handshake' to offer a hand, or 'we are' any time."
    print "Press Ctrl+C to stop."

    hand_offered = False

    try:
        while True:

            word = check_word(memory)

            if word:
                turn_toward_speaker(motion, memory)

            if word == "we are":
                print "Responding to 'we are'"
                tts.say("Penn State!")

            elif word == "handshake" and not hand_offered:
                print "Heard 'handshake' -- offering hand."
                offer_hand(motion, tts)
                hand_offered = True

            if hand_offered:
                for key in TOUCH_KEYS:
                    if memory.getData(key) == 1.0:
                        shake_hand(motion, tts)
                        memory.insertData(key, 0.0)
                        hand_offered = False
                        print "Handshake complete. Staying stationary again."
                        break

            time.sleep(0.2)

    except KeyboardInterrupt:

        print "Demo interrupted by a user via keyboard."

    finally:

        try:
            asr.unsubscribe(ASR_NAME)
        except Exception:
            pass

        try:
            sound.unsubscribe(SOUND_NAME)
        except Exception:
            pass
