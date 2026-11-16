"""Check the connection to Pepper over NAOqi: python tools/pepper_check.py <PEPPER_IP> [port]"""
import sys
import qi

ip = sys.argv[1]
port = int(sys.argv[2]) if len(sys.argv) > 2 else 9559
app = qi.Application(['pepper_check', f'--qi-url=tcp://{ip}:{port}'])
app.start()
s = app.session
print('Connected to', ip)
print('NAOqi version:', s.service('ALSystem').systemVersion())
print('Robot name   :', s.service('ALSystem').robotName())
print('Battery      :', s.service('ALBattery').getBatteryCharge(), '%')
s.service('ALTextToSpeech').say('Hello, I am connected to the Mac.')
