"""Quick shared-memory smoke test: python -m ledsim._test_shared"""
import os
import sys

# repo root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multiprocessing import Process, set_start_method


def publish_test():
    os.environ["LEDARCADE_DISPLAY"] = "sim"
    import ledsim.rgbmatrix_compat as rm

    opts = rm.RGBMatrixOptions()
    opts.cols = 64
    opts.rows = 32
    m = rm.RGBMatrix(options=opts)
    c = m.CreateFrameCanvas()
    for x in range(64):
        c.SetPixel(x, 16, 255, 128, 0)
    m.SwapOnVSync(c)
    print("child published ok")


def main():
    try:
        set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    from ledsim import shared

    shm, name, w, h = shared.create_shared_buffer(64, 32)
    print("shm", name, "env", os.environ.get("LEDARCADE_SIM_SHM"))
    p = Process(target=publish_test)
    p.start()
    p.join(10)
    print("exitcode", p.exitcode)
    counter, data = shared.read_frame()
    i = (16 * 64 + 32) * 3
    print("counter", counter, "pixel", data[i], data[i + 1], data[i + 2])
    shm.close()
    shm.unlink()
    assert p.exitcode == 0, "child failed"
    assert counter > 0, "no frame published"
    assert data[i] == 255 and data[i + 1] == 128, "pixel color mismatch"
    print("PASS")


if __name__ == "__main__":
    main()
