from naoqi import ALProxy

robot_ip = "192.168.0.101"
port = 9559

tts = ALProxy("ALTextToSpeech", robot_ip, port)
tts.say("Hello Aubrey")

"""
from naoqi import ALProxy
import time

ROBOT_IP = "192.168.1.100"   # Replace with your Pepper's IP
PORT = 9559

tts = ALProxy("ALTextToSpeech", ROBOT_IP, PORT)
asr = ALProxy("ALSpeechRecognition", ROBOT_IP, PORT)
memory = ALProxy("ALMemory", ROBOT_IP, PORT)

# English recognition
asr.setLanguage("English")

# Vocabulary to recognize
vocabulary = ["we are"]

# Disable word spotting so Pepper listens for the whole phrase
asr.setVocabulary(vocabulary, False)

# Introduce herself
tts.say("Hello! My name is Pepper.")
tts.say("I'm a humanoid robot developed to interact with people.")
tts.say("When you say 'we are', I'll finish the phrase.")

# Start speech recognition
asr.subscribe("PennStateDemo")

print("Listening...")

try:
    while True:
        data = memory.getData("WordRecognized")

        if data and len(data) >= 2:
            word = data[0]
            confidence = data[1]

            if word == "we are" and confidence > 0.45:
                print("Recognized:", word)
                tts.say("Penn State!")
                time.sleep(2)

        time.sleep(0.2)

except KeyboardInterrupt:
    print("Stopping...")

finally:
    asr.unsubscribe("PennStateDemo")
"""