# LEDweb.py - Backward-compatible shim.
# Web control lives in LEDcommander.serve_web_control().
from LEDcommander import serve_web_control

__all__ = ["serve_web_control"]

if __name__ == "__main__":
    from multiprocessing import Queue

    command_queue = Queue()
    serve_web_control(command_queue, port=5055)