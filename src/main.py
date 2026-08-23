#!/usr/bin/env python3
import threading
import time
import random
import math
import queue
from Aloha.src.utils.budget_utls import cpu_load,memory_load

# ============================================================
#  Utility: Dummy CPU + Memory Load
# ============================================================

def cpu_load(duration_ms=40):
    """Burn CPU cycles for a fixed duration."""
    end = time.time() + (duration_ms / 1000.0)
    x = 0.0
    while time.time() < end:
        x += math.sin(random.random())
    return x

def memory_load(size_kb=256):
    """Allocate temporary memory to simulate load."""
    return bytearray(size_kb * 1024)


# ============================================================
#  Base Module Class
# ============================================================

class BaseModule(threading.Thread):
    def __init__(self, name, interval=1.0):
        super().__init__(daemon=True)
        self.name = name
        self.interval = interval
        self.running = False
        self.last_output = None

    def run(self):
        self.running = True
        print(f"[{self.name}] started")

        while self.running:
            start = time.time()

            # Simulate CPU + memory usage
            cpu_load(30)
            memory_load(128)

            # Module-specific work
            self.last_output = self.step()

            # Maintain interval
            elapsed = time.time() - start
            sleep_time = max(0.0, self.interval - elapsed)
            time.sleep(sleep_time)

        print(f"[{self.name}] stopped")

    def stop(self):
        self.running = False

    def step(self):
        """Override in subclass."""
        return None


# ============================================================
#  PTF Camera Controller (same as ASC camera)
# ============================================================

class PtfCameraModule(BaseModule):
    def step(self):
        frame = {
            "width": 1920,
            "height": 1080,
            "bit_depth": 12,
            "sensor_id": 1,
            "temperature": random.uniform(-5, 25),
            "gain": random.uniform(0, 20),
            "exposure_us": random.randint(5000, 50000),
            "timestamp": time.time()
        }

        # Simulate RAW frame generation
        cpu_load(50)
        memory_load(1024)

        print(f"[ptf-camera] frame_id={frame['timestamp']}")
        return frame


# ============================================================
#  Pan�Tilt�Focus Controller
# ============================================================

class PtfControlModule(BaseModule):
    def __init__(self, name, interval=0.2):
        super().__init__(name, interval)
        self.target_queue = queue.Queue(maxsize=10)
        self.current_pan = 0.0
        self.current_tilt = 0.0
        self.current_focus = 0.0

    def push_target(self, target):
        """Receive target from s360-core-node."""
        try:
            self.target_queue.put_nowait(target)
        except queue.Full:
            pass

    def step(self):
        if not self.target_queue.empty():
            target = self.target_queue.get()

            # Dummy PTF movement simulation
            cpu_load(20)
            memory_load(128)

            # Move pan/tilt/focus toward target
            self.current_pan += (target["pan"] - self.current_pan) * 0.2
            self.current_tilt += (target["tilt"] - self.current_tilt) * 0.2
            self.current_focus += (target["focus"] - self.current_focus) * 0.2

            status = {
                "pan": self.current_pan,
                "tilt": self.current_tilt,
                "focus": self.current_focus,
                "timestamp": time.time()
            }

            print(f"[ptf-control] pan={status['pan']:.2f} tilt={status['tilt']:.2f}")
            return status

        return None


# ============================================================
#  Target Tracking (EKF placeholder)
# ============================================================

class TrackingModule(BaseModule):
    def __init__(self, name, interval=0.5):
        super().__init__(name, interval)
        self.frame_queue = queue.Queue(maxsize=5)

    def push_frame(self, frame):
        try:
            self.frame_queue.put_nowait(frame)
        except queue.Full:
            pass

    def step(self):
        if self.frame_queue.empty():
            return None

        frame = self.frame_queue.get()

        # Simulate EKF tracking load
        cpu_load(60)
        memory_load(512)

        # Dummy target estimate
        target = {
            "pan": random.uniform(0, 360),
            "tilt": random.uniform(-45, 45),
            "focus": random.uniform(0, 1),
            "confidence": random.uniform(0.5, 0.99),
            "timestamp": time.time()
        }

        print(f"[tracking] target pan={target['pan']:.1f}")
        return target


# ============================================================
#  TinyML Module (NPU inference)
# ============================================================

class TinyMlModule(BaseModule):
    def __init__(self, name, interval=0.5):
        super().__init__(name, interval)
        self.target_queue = queue.Queue(maxsize=10)

    def push_target(self, target):
        try:
            self.target_queue.put_nowait(target)
        except queue.Full:
            pass

    def step(self):
        if self.target_queue.empty():
            return None

        target = self.target_queue.get()

        # Simulate NPU inference load
        cpu_load(20)
        memory_load(256)

        # Dummy classification
        classified = {
            "label": random.choice(["aircraft", "drone", "bird", "unknown"]),
            "confidence": random.uniform(0.5, 0.99),
            "timestamp": time.time()
        }

        print(f"[tinyml] label={classified['label']}")
        return classified


# ============================================================
#  Orchestrator
# ============================================================

class Orchestrator:
    def __init__(self):
        self.ptf_camera = PtfCameraModule("ptf-camera", interval=0.5)
        self.ptf_control = PtfControlModule("ptf-control", interval=0.2)
        self.tracking = TrackingModule("tracking", interval=0.5)
        self.tinyml = TinyMlModule("tinyml", interval=0.5)

        self.modules = [
            self.ptf_camera,
            self.ptf_control,
            self.tracking,
            self.tinyml
        ]

    def start(self):
        print("[orchestrator] starting modules")
        for m in self.modules:
            m.start()

        # Main orchestrator loop
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        while True:
            # Camera ? Tracking
            if self.ptf_camera.last_output:
                self.tracking.push_frame(self.ptf_camera.last_output)

            # Tracking ? PTF control
            if self.tracking.last_output:
                self.ptf_control.push_target(self.tracking.last_output)

            # Tracking ? TinyML
            if self.tracking.last_output:
                self.tinyml.push_target(self.tracking.last_output)

            time.sleep(0.1)

    def stop(self):
        print("[orchestrator] stopping modules")
        for m in self.modules:
            m.stop()

        for m in self.modules:
            m.join()

    def run(self):
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[orchestrator] shutdown requested")
            self.stop()


# ============================================================
#  Main
# ============================================================

if __name__ == "__main__":
    orch = Orchestrator()
    orch.run()
