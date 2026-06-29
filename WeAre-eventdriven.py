from naoqi import ALProxy
import time

ROBOT_IP = "192.168.0.101"
PORT= 9559

tts = ALProxy("ALTextToSpeech", ROBOT_IP, PORT)
asr = ALProxy("ALSpeechRecognition", ROBOT_IP, PORT)
memory = ALProxy("ALMemory", ROBOT_IP, PORT)
# -----------------------
# Setup ASR
# -----------------------

try:
    asr.unsubscribe("WeAreDemo")
except:
    pass

# -----------------------
# Setup ASR
# -----------------------
asr.setLanguage("English")
asr.setVocabulary(["we are"], False)
asr.subscribe("WeAreDemo")

# -----------------------
# Callback (MUST be global)
# -----------------------
def on_word_recognized(value):
    if not value or len(value) < 2:
        return

    word = value[0]
    confidence = value[1]

    print("Heard:", word, confidence)

    if word == "we are" and confidence > 0.4:
        tts.say("Penn State!")

# -----------------------
# Correct subscription
# -----------------------
memory.subscribeToEvent(
    "WordRecognized",
    "WeAreDemo",
    "on_word_recognized"
)

tts.say("I am listening for 'we are'")

print("Listening...")

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    pass

finally:
    # SAFE cleanup (avoid double-unsubscribe crash)
    try:
        memory.unsubscribeToEvent("WordRecognized", "WeAreDemo")
    except:
        pass

    try:
        asr.unsubscribe("WeAreDemo")
    except:
        pass