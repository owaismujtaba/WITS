import subprocess
import time

command = ["python", "main.py"]

while True:
    process = subprocess.Popen(command)
    time.sleep(30*60)
    process.terminate()
    time.sleep(5)
    process.wait()
    print("Process terminated. Restarting...")
