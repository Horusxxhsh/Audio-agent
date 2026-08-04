# Per-Parameter Error Distribution Analysis

## Module-Level Summary (Raw)

| Module | Mean | Median | Std | Max | N |
|--------|------|--------|-----|-----|---|
| ChorusOff | 0.0113 | 0.0000 | 0.0772 | 0.9900 | 320 |
| ChorusOn | 0.1445 | 0.0529 | 0.1848 | 0.6727 | 712 |
| CompressorOff | 1.0516 | 0.0000 | 4.4551 | 24.0000 | 306 |
| CompressorOn | 0.8950 | 0.0988 | 2.8085 | 26.2210 | 1068 |
| DelayOff | 2.4534 | 0.0000 | 29.1387 | 350.9000 | 144 |
| DelayOn | 14.8921 | 0.1534 | 57.5761 | 484.0000 | 561 |
| DriverOff | 9.1159 | 0.0000 | 22.3631 | 64.0000 | 302 |
| DriverOn | 2.6248 | 0.5635 | 3.8286 | 18.0000 | 190 |
| EqualiserOn | 0.2236 | 0.1164 | 0.3456 | 3.2100 | 1632 |
| FlangerOff | 0.0093 | 0.0000 | 0.0497 | 1.0000 | 770 |
| FlangerOn | 0.2092 | 0.1204 | 0.2422 | 0.9917 | 510 |
| PhaserOff | 3.6954 | 0.0000 | 13.0444 | 50.0000 | 648 |
| PhaserOn | 132.8669 | 0.2930 | 346.5101 | 1842.0000 | 328 |
| ReverbOff | 0.2767 | 0.1370 | 0.2517 | 0.9969 | 48 |
| ReverbOn | 0.1435 | 0.1032 | 0.1435 | 1.0000 | 804 |
| ScreamerOff | 4.0006 | 0.0000 | 15.4801 | 64.8242 | 468 |
| ScreamerOn | 1.4410 | 0.2110 | 2.5807 | 11.7000 | 204 |

## Module-Level Summary (Normalized)

| Module | Mean | Median | Std | Max | N |
|--------|------|--------|-----|-----|---|
| ChorusOff | 0.0113 | 0.0000 | 0.0772 | 0.9900 | 320 |
| ChorusOn | 0.1445 | 0.0529 | 0.1848 | 0.6727 | 712 |
| CompressorOff | 1.0516 | 0.0000 | 4.4551 | 24.0000 | 306 |
| CompressorOn | 0.0855 | 0.0244 | 0.1522 | 0.9110 | 1068 |
| DelayOff | 0.0167 | 0.0000 | 0.0892 | 1.0000 | 144 |
| DelayOn | 0.1170 | 0.0379 | 0.1483 | 0.6606 | 561 |
| DriverOff | 0.0508 | 0.0000 | 0.1287 | 1.0000 | 302 |
| DriverOn | 0.1650 | 0.0439 | 0.2200 | 0.8855 | 190 |
| EqualiserOn | 0.0093 | 0.0049 | 0.0144 | 0.1338 | 1632 |
| FlangerOff | 0.0093 | 0.0000 | 0.0497 | 1.0000 | 770 |
| FlangerOn | 0.2092 | 0.1204 | 0.2422 | 0.9917 | 510 |
| PhaserOff | 0.0409 | 0.0000 | 0.1356 | 1.0000 | 648 |
| PhaserOn | 1.5108 | 0.2702 | 3.4001 | 18.4200 | 328 |
| ReverbOff | 0.2767 | 0.1370 | 0.2517 | 0.9969 | 48 |
| ReverbOn | 0.1435 | 0.1032 | 0.1435 | 1.0000 | 804 |
| ScreamerOff | 0.0414 | 0.0000 | 0.1265 | 1.0000 | 468 |
| ScreamerOn | 0.1557 | 0.0444 | 0.2025 | 0.8247 | 204 |

## Top-10 Hardest Parameters (by Normalized Mean Error)

| Parameter | Mean (norm) | Mean (raw) | N |
|-----------|-------------|------------|---|
| CompressorOff.Threshold | 5.4510 | 5.4510 | 51 |
| PhaserOn.Width | 5.3073 | 530.7317 | 82 |
| CompressorOff.Ratio | 0.7255 | 0.7255 | 51 |
| ReverbOff.Damping | 0.4135 | 0.4135 | 12 |
| ReverbOff.Width | 0.4033 | 0.4033 | 12 |
| FlangerOn.Frequency | 0.3249 | 0.3249 | 102 |
| FlangerOn.Depth | 0.3180 | 0.3180 | 102 |
| DriverOn.Distortion | 0.3042 | 0.3042 | 95 |
| PhaserOn.Depth | 0.2761 | 0.2761 | 82 |
| PhaserOn.Frequency | 0.2484 | 0.2484 | 82 |

## Top-10 Easiest Parameters (by Normalized Mean Error)

| Parameter | Mean (norm) | Mean (raw) | N |
|-----------|-------------|------------|---|
| FlangerOn.Delay | 0.0053 | 0.0053 | 102 |
| EqualiserOn.800hz | 0.0050 | 0.1191 | 204 |
| EqualiserOn.Level | 0.0046 | 0.1104 | 204 |
| DelayOn.Delay | 0.0044 | 44.3297 | 187 |
| FlangerOff.Width | 0.0039 | 0.0039 | 154 |
| CompressorOff.Mix | 0.0035 | 0.0035 | 51 |
| ChorusOff.Width | 0.0031 | 0.0031 | 80 |
| DelayOff.Delay | 0.0007 | 7.3108 | 48 |
| PhaserOff.Depth | 0.0000 | 0.0000 | 162 |
| ChorusOff.Depth | 0.0000 | 0.0000 | 80 |
