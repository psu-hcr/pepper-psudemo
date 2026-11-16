#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
"We are" -> "Penn State!" call-response for Pepper (NAOqi 2.5, Python 2.7).

    python2.7 hellopepper.py [PEPPER_IP]

What changed vs. the first version, and why she seemed not to listen:
  1. WordRecognized is a memory key that KEEPS its last value. The old loop
     read it every 0.2 s, so either it re-fired on stale data or a new result
     was hard to tell apart. Now the key is cleared after every read.
  2. She could hear herself. ASR is now paused while she talks and for a
     short moment after, so her own "Penn State!" is not recognized.
  3. Autonomous Life / ALDialog also use speech recognition. If they hold
     it, setVocabulary fails or our subscription gets nothing. Autonomous
     Life is switched off for the demo (then she is woken up again).
  4. Changing the vocabulary while the engine runs throws an error on 2.5,
     so the engine is paused around setVocabulary.
  5. Word spotting is ON: she reports "we are" even inside a longer phrase
     ("<...> we are <...>"), instead of needing the exact two words alone.
  6. Every result and its confidence is printed, so you can tune
     CONFIDENCE_THRESHOLD in the room.
  7. A beep (audio expression) and blue eyes show when she is listening.
"""
from naoqi import ALProxy
import sys
import time

ROBOT_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.101"
PORT = 9559

ASR_NAME = "PennStateDemo"
PHRASE = "we are"
REPLY = "Penn State!"
CONFIDENCE_THRESHOLD = 0.40   # lower = more forgiving, more false triggers
SENSITIVITY = 0.6             # 0..1 ASR sensitivity to quiet speech (if supported)
AFTER_SPEECH_PAUSE_S = 0.8    # keep ears closed briefly after she talks

tts = ALProxy("ALTextToSpeech", ROBOT_IP, PORT)
asr = ALProxy("ALSpeechRecognition", ROBOT_IP, PORT)
memory = ALProxy("ALMemory", ROBOT_IP, PORT)
motion = ALProxy("ALMotion", ROBOT_IP, PORT)
posture = ALProxy("ALRobotPosture", ROBOT_IP, PORT)


def try_call(label, fn, *args):
    try:
        return fn(*args)
    except Exception as exc:
        print("[warn] %s: %s" % (label, exc))


def clear_word():
    memory.insertData("WordRecognized", ["", 0.0])


def say(text):
    """Speak with the microphones closed so she does not hear herself."""
    try_call("asr.pause(True)", asr.pause, True)
    tts.say(text)
    time.sleep(AFTER_SPEECH_PAUSE_S)
    clear_word()
    try_call("asr.pause(False)", asr.pause, False)


# --- Free the speech engine from Autonomous Life / dialog --------------------
life = None
try:
    life = ALProxy("ALAutonomousLife", ROBOT_IP, PORT)
    if life.getState() != "disabled":
        print("Disabling Autonomous Life for the demo...")
        life.setState("disabled")
except Exception as exc:
    print("[warn] Autonomous Life: %s" % exc)

try_call("stop old subscription", asr.unsubscribe, ASR_NAME)

motion.wakeUp()                      # disabling Life puts her to rest
posture.goToPosture("StandInit", 0.8)

# --- Configure recognition ----------------------------------------------------
try_call("asr.pause(True)", asr.pause, True)
asr.setLanguage("English")
asr.setVocabulary([PHRASE], True)    # True = word spotting
try_call("Sensitivity", asr.setParameter, "Sensitivity", SENSITIVITY)
try_call("audio expression", asr.setAudioExpression, True)   # beep when listening
try_call("visual expression", asr.setVisualExpression, True)  # eye LEDs
try_call("asr.pause(False)", asr.pause, False)

clear_word()
asr.subscribe(ASR_NAME)

say("When you say 'we are', I'll finish the phrase.")
print("Listening for '%s' (threshold %.2f). Ctrl+C to stop." % (PHRASE, CONFIDENCE_THRESHOLD))

try:
    while True:
        data = memory.getData("WordRecognized")
        if data and len(data) >= 2 and data[0]:
            clear_word()
            word, confidence = data[0], data[1]
            print("Heard: %r  confidence=%.2f" % (word, confidence))
            if PHRASE in word and confidence >= CONFIDENCE_THRESHOLD:
                say(REPLY)
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Demo interrupted by a user via keyboard.")

finally:
    print("Stopping speech recognition...")
    try_call("unsubscribe", asr.unsubscribe, ASR_NAME)
    # To give Pepper back her normal behaviour, uncomment:
    # if life is not None: try_call("Life", life.setState, "solitary")
    print("Demo stopped.")
