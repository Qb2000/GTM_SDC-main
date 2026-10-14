
# .tra to GTM Science CSV

- Requires Python 3. Run: `python convert_tra_to_science.py input.tra -o output.csv` (`.tra.gz` is also supported).
- Add `--include-sensor-columns` to show detector names; use `--help` to list options.
- Units: X/Y/Z = meters; Q1-Q4 = dimensionless quaternions; Temperature = degrees Celsius; Energy = keV.
- Time: Day of Year = day number; Hour = hours; Minute = minutes; Second/Subsecond/Relative Time = seconds. Relative Time uses TI by default.
- GTM ID:  0 &rarr; Master module, 1 &rarr; Slave module
- CITIROC: 0, 1 ; Channel: 0~31
- GTM Sensor: 
    - M1 &rarr;(GTM ID 0, CITIROC 1, Channel 16~31)
    - M2 &rarr;(GTM ID 0, CITIROC 1, Channel 0~15)
    - M3 &rarr;(GTM ID 0, CITIROC 0, Channel 16~31)
    - M4 &rarr;(GTM ID 0, CITIROC 0, Channel 0~15)
    - S1 &rarr;(GTM ID 1, CITIROC 1, Channel 16~31)
    - S2 &rarr;(GTM ID 1, CITIROC 1, Channel 0~15)
    - S3 &rarr;(GTM ID 1, CITIROC 0, Channel 16~31)
    - S4 &rarr;(GTM ID 1, CITIROC 0, Channel 0~15)
- Each hit produces one row; hits in the same event share time. Spacecraft telemetry and within-detector channels are synthetic.
