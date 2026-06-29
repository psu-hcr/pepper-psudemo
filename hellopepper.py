from naoqi import ALProxy
import time

ROBOT_IP = "192.168.0.101"
PORT= 9559
"""
tts = ALProxy("ALTextToSpeech", robot_ip, port)
tts.say("Hello Aubrey")

"""

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
tts.say("Welcome to the Human-Centered robotics lab at Penn State University.")
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
            print("Heard:", word, confidence)

            if word == "we are" and confidence > 0.45:
                print("Recognized:", word)
                tts.say("Penn State!")
                time.sleep(2)
            elif word == "hug me" and confidence >0.45:
                tts.say("Love you, Aubrey")
                """
                Safe 'hug-like' motion (lean forward slightly)
                """
                motion.setStiffnesses("Body", 1.0)

                # Lean forward gently (safe range)
                motion.moveTorso(0.05, 0.0, 0.0)  # small forward lean

                tts.say("Here is a virtual hug!")

                time.sleep(2)

                # Return to neutral
                motion.moveTorso(0.0, 0.0, 0.0)

        time.sleep(0.2)

except KeyboardInterrupt:
    print("Stopping...")

finally:
    asr.unsubscribe("PennStateDemo")
