import subprocess
import sys
import time

print(">>> INITIALIZING DUAL-SYSTEM <<<")

# 1. Start the Flask API in the background
print("[*] Starting Flask API (app.py)...")
api_process = subprocess.Popen([sys.executable, "app.py"])

# Give the API a second to boot up
time.sleep(2)

# 2. Start the Telegram Bot
print("[*] Starting Telegram Bot (bot.py)...")
bot_process = subprocess.Popen([sys.executable, "bot.py"])

try:
    # Keep the launcher running so Railway doesn't shut down
    api_process.wait()
    bot_process.wait()
except KeyboardInterrupt:
    print("\n>>> SHUTTING DOWN SYSTEMS <<<")
    api_process.terminate()
    bot_process.terminate()