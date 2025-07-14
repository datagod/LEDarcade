import requests
import time
import argparse

# No need for multiprocessing here; assume LEDcommander is running separately with Flask on port 5055

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

    url = "http://localhost:5055/command"  # Adjust host/port if running remotely

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