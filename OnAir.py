import requests
import time
import argparse

# No need for multiprocessing here; assume LEDcommander is running separately with Flask on port 5055

'''
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Control OnAir display")
    parser.add_argument('--on', action='store_true', help="Turn OnAir on")
    parser.add_argument('--off', action='store_true', help="Turn OnAir off")
    parser.add_argument('--minutes', type=int, default=30, help="Minutes to remain on air (default: 30)")

    args = parser.parse_args()

    if not (args.on or args.off):
        print("Error: Must specify --on or --off")
        parser.print_help()
        exit(1)

    url = "http://ledpie:5055/command"  # Adjust host/port if running remotely

    try:
        if args.on:
            duration = args.minutes * 60  # Convert minutes to seconds
            data = {"Action": "showonair", "duration": duration}
            response = requests.post(url, json=data)
            print(f"[OnAir] Response: {response.json() if response.ok else response.text}")
        elif args.off:
            data = {"Action": "showonair_off"}
            response = requests.post(url, json=data)
            print(f"[OnAir] Response: {response.json() if response.ok else response.text}")
    except requests.exceptions.ConnectionError:
        print("[OnAir] Error: Could not connect to LEDcommander Flask server. Ensure it's running.")
    except Exception as e:
        print(f"[OnAir] Error: {e}")

'''        


import RPi.GPIO as GPIO
import time
import requests

BUTTON_GPIO = 17
SERVER_URL = "http://ledpi1:5055/command"  # Replace <remote_ip> with the actual IP of the computer running LEDcommander

on_air = False  # Initial state: off

def button_callback(channel):
    global on_air
    # Check if button is still pressed (LOW)
    if GPIO.input(BUTTON_GPIO) == GPIO.LOW:
        print("Button was pressed!")
        try:
            if on_air:
                # Turn off
                data = {"Action": "showonair_off"}
                response = requests.post(SERVER_URL, json=data)
                print(f"[Off] Response: {response.json() if response.ok else response.text}")
                on_air = False
            else:
                # Turn on (default 30 minutes, but can adjust duration if needed)
                data = {"Action": "showonair", "duration": 1800}  # 30 minutes in seconds
                response = requests.post(SERVER_URL, json=data)
                print(f"[On] Response: {response.json() if response.ok else response.text}")
                on_air = True
        except requests.exceptions.ConnectionError:
            print("Error: Could not connect to LEDcommander server. Ensure it's running.")
        except Exception as e:
            print(f"Error: {e}")

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Detect FALLING edge (press: HIGH -> LOW)
GPIO.add_event_detect(
    BUTTON_GPIO,
    GPIO.FALLING,
    callback=button_callback,
    bouncetime=30  # 300ms debounce to prevent rapid toggles
)

print("Waiting for button presses... (Ctrl+C to exit)")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting...")

finally:
    GPIO.cleanup()