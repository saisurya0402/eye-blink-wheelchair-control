# Eye Blink Sensor Wheelchair Control

An assistive technology project that controls wheelchair movement using eye blink patterns. Built with clean OOP architecture, it simulates a real hardware pipeline — sensor input → signal classification → motor command execution.

## How It Works

```
Eye Blink Signal
     ↓
[EyeBlinkSensor] — reads & classifies blink duration
     ↓
[BlinkSequenceBuffer] — accumulates blinks, resolves to commands
     ↓
[MotorController] — executes movement commands
```

## Blink Command Mapping

| Blink Pattern | Command |
|---------------|---------|
| Single blink | FORWARD |
| Long blink (>600ms) | BACKWARD |
| Double blink | STOP |
| Single × 3 | LEFT TURN |
| Single + Double | RIGHT TURN |

## Tech Stack
- **Python 3.x** — core logic
- **Hardware (real deployment)**: Raspberry Pi GPIO / Arduino + EEG/EOG sensor (AD8232, Neurosky MindWave)
- **Embedded patterns**: sensor abstraction, signal classification, command buffering

## How to Run (Simulation)

```bash
python wheelchair_controller.py
```

## Real Hardware Integration
Replace `EyeBlinkSensor.read_raw()` with actual GPIO input:
```python
import RPi.GPIO as GPIO
# measure pulse width on blink sensor pin
duration = measure_blink_gpio(pin=17)
```

## Author
Sai Surya Yeedulapally — [GitHub](https://github.com/saisurya0402)
