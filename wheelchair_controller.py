"""
Eye Blink Sensor Wheelchair Control System
Author: Sai Surya Yeedulapally
Stack: Python · Hardware Simulation · Embedded Systems
Description: Simulates an assistive wheelchair control system that maps eye blink
             signals (single/double/long blink) to wheelchair movement commands.
             In a real deployment, this connects to an EEG/EOG sensor (e.g., EPOC, AD8232)
             or GPIO-based eye blink detector on Raspberry Pi / Arduino.
"""

import time
import logging
import random
from enum import Enum
from datetime import datetime


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─── ENUMS ─────────────────────────────────────────────────────────────────

class BlinkType(Enum):
    SINGLE = "SINGLE"       # One blink
    DOUBLE = "DOUBLE"       # Two blinks within threshold
    LONG   = "LONG"         # Blink held > threshold


class Direction(Enum):
    FORWARD  = "FORWARD"
    BACKWARD = "BACKWARD"
    LEFT     = "LEFT"
    RIGHT    = "RIGHT"
    STOP     = "STOP"


# ─── COMMAND MAPPING ───────────────────────────────────────────────────────

BLINK_TO_COMMAND = {
    # Sequence : Direction
    (BlinkType.SINGLE,)                              : Direction.FORWARD,
    (BlinkType.DOUBLE,)                              : Direction.STOP,
    (BlinkType.LONG,)                                : Direction.BACKWARD,
    (BlinkType.SINGLE, BlinkType.SINGLE, BlinkType.SINGLE): Direction.LEFT,
    (BlinkType.SINGLE, BlinkType.DOUBLE)             : Direction.RIGHT,
}


# ─── SENSOR INTERFACE ──────────────────────────────────────────────────────

class EyeBlinkSensor:
    """
    Abstract sensor interface.
    In production: replace read_raw() with GPIO input or serial data from Arduino/RPi.
    """

    SINGLE_BLINK_MIN_MS = 80
    SINGLE_BLINK_MAX_MS = 300
    LONG_BLINK_MIN_MS   = 600
    DOUBLE_BLINK_GAP_MS = 400

    def __init__(self, simulate=True):
        self.simulate = simulate
        self._last_blink_time = None

    def read_raw(self) -> float:
        """
        Returns blink duration in ms.
        Simulation: returns realistic random durations.
        Real hardware: read ADC/GPIO pin voltage and measure pulse width.
        """
        if self.simulate:
            blink_type = random.choices(
                ["short", "long", "none"],
                weights=[60, 20, 20]
            )[0]
            if blink_type == "short":
                return random.uniform(80, 300)
            elif blink_type == "long":
                return random.uniform(600, 1200)
            else:
                return 0.0
        else:
            # Real hardware placeholder:
            # import RPi.GPIO as GPIO
            # duration = measure_blink_gpio(pin=17)
            # return duration
            raise NotImplementedError("Connect real sensor.")

    def classify(self, duration_ms: float) -> BlinkType | None:
        """Classify raw blink duration into blink type."""
        if duration_ms < self.SINGLE_BLINK_MIN_MS:
            return None  # noise
        elif duration_ms <= self.SINGLE_BLINK_MAX_MS:
            return BlinkType.SINGLE
        elif duration_ms >= self.LONG_BLINK_MIN_MS:
            return BlinkType.LONG
        else:
            return None  # intermediate — ignored


# ─── MOTOR CONTROLLER ──────────────────────────────────────────────────────

class MotorController:
    """
    Simulates wheelchair motor control.
    Real deployment: replace execute() with GPIO PWM signals or serial to motor driver.
    """

    SPEED = 50  # % of max speed (PWM duty cycle in real use)

    def __init__(self):
        self.current_direction = Direction.STOP
        self.odometer = 0.0  # simulated distance in cm
        self.session_log = []

    def execute(self, direction: Direction):
        """Apply a movement command."""
        if direction == self.current_direction:
            return

        self.current_direction = direction
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if direction == Direction.FORWARD:
            log.info(f"  🟢 MOTOR → FORWARD  (speed={self.SPEED}%)")
        elif direction == Direction.BACKWARD:
            log.info(f"  🔵 MOTOR → BACKWARD (speed={self.SPEED}%)")
        elif direction == Direction.LEFT:
            log.info(f"  🟡 MOTOR → LEFT TURN")
        elif direction == Direction.RIGHT:
            log.info(f"  🟠 MOTOR → RIGHT TURN")
        elif direction == Direction.STOP:
            log.info(f"  🔴 MOTOR → STOP")

        self.session_log.append({"time": ts, "command": direction.value})

    def update_odometer(self, seconds_elapsed: float):
        """Simulate distance tracking."""
        if self.current_direction in (Direction.FORWARD, Direction.BACKWARD):
            speed_cm_per_sec = 30  # ~10.8 km/h at max, adjust per motor
            self.odometer += speed_cm_per_sec * seconds_elapsed

    def print_session_summary(self):
        log.info("\n── SESSION SUMMARY ──────────────────────────────")
        log.info(f"  Total commands    : {len(self.session_log)}")
        log.info(f"  Distance traveled : {self.odometer:.1f} cm")
        log.info("  Command history   :")
        for entry in self.session_log:
            log.info(f"    [{entry['time']}] {entry['command']}")


# ─── BLINK SEQUENCE BUFFER ─────────────────────────────────────────────────

class BlinkSequenceBuffer:
    """
    Accumulates blink events and resolves them to commands.
    Handles timing windows for double-blink detection.
    """

    SEQUENCE_TIMEOUT_SEC = 1.5

    def __init__(self):
        self._buffer = []
        self._last_blink_ts = None

    def push(self, blink: BlinkType):
        now = time.time()
        if self._last_blink_ts and (now - self._last_blink_ts) > self.SEQUENCE_TIMEOUT_SEC:
            self._buffer.clear()
        self._buffer.append(blink)
        self._last_blink_ts = now

    def resolve(self) -> Direction | None:
        """Try to match buffer against known command sequences."""
        key = tuple(self._buffer)
        if key in BLINK_TO_COMMAND:
            direction = BLINK_TO_COMMAND[key]
            self._buffer.clear()
            return direction
        # Check partial match — flush if no possible match
        max_seq = max(len(k) for k in BLINK_TO_COMMAND)
        if len(self._buffer) > max_seq:
            self._buffer.clear()
        return None

    def clear(self):
        self._buffer.clear()


# ─── MAIN CONTROL LOOP ─────────────────────────────────────────────────────

class WheelchairControlSystem:
    """Main controller orchestrating sensor → classifier → motor pipeline."""

    POLL_INTERVAL_SEC = 0.5
    MAX_CYCLES = 20  # Stop after N cycles in simulation

    def __init__(self):
        self.sensor = EyeBlinkSensor(simulate=True)
        self.motor = MotorController()
        self.buffer = BlinkSequenceBuffer()
        self._running = False
        self._cycle = 0

    def start(self):
        log.info("=" * 55)
        log.info("  EYE BLINK WHEELCHAIR CONTROL SYSTEM")
        log.info("  Author: Sai Surya Yeedulapally")
        log.info("=" * 55)
        log.info("  Blink codes:")
        log.info("    Single blink              → FORWARD")
        log.info("    Long blink                → BACKWARD")
        log.info("    Double blink              → STOP")
        log.info("    Single × 3               → LEFT")
        log.info("    Single + Double           → RIGHT")
        log.info("=" * 55)

        self._running = True
        self.motor.execute(Direction.STOP)

        while self._running and self._cycle < self.MAX_CYCLES:
            self._cycle += 1
            time.sleep(self.POLL_INTERVAL_SEC)

            raw_duration = self.sensor.read_raw()
            blink = self.sensor.classify(raw_duration)

            if blink:
                log.info(f"[Sensor] Blink detected: {blink.value} ({raw_duration:.0f}ms)")
                self.buffer.push(blink)

                command = self.buffer.resolve()
                if command:
                    log.info(f"[Command] Resolved: {command.value}")
                    self.motor.execute(command)

            self.motor.update_odometer(self.POLL_INTERVAL_SEC)

        self._running = False
        self.motor.print_session_summary()
        log.info("\n  System stopped.\n")


# ─── ENTRY POINT ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    system = WheelchairControlSystem()
    system.start()
