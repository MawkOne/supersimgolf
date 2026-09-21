# SuperSimGolf

Prototype bridge for turning M5Stack AtomS3R golf-trainer swing data into virtual shots in GolfForge.

## V0 goal

AtomS3R swing -> SuperSimGolf bridge -> GSPro Open Connect -> GolfForge

GolfForge is pinned as a git submodule under `vendor/golfforge`.

## Quick test

1. Clone with submodules.
2. Launch GolfForge and open Practice Range.
3. Select GSPro Connect. GolfForge listens on `127.0.0.1:921`.
4. Run `python3 bridge.py --csv swing_007.csv` or `python3 bridge.py --peak-gyro 1400`.

V0 intentionally uses a simple Wii-style power mapping. Later versions will use full six-axis swing analysis, player calibration, phone video, ADXL375 impact sensing, and FSR grip pressure.
