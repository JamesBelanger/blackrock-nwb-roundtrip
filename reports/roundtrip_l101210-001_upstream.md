# Round-trip check: `l101210-001_upstream.nwb`

Reference: `l101210-001.ns5/.ns2/.nev` read with `scripts/reference_readers.py`.

| Check | Result | Detail |
|---|---|---|
| session_start_time = .nev time origin (UTC) | PASS | 2010-12-10T10:50:10.156000+00:00 vs 2010-12-10T10:50:10.156000+00:00 |
| ElectricalSeries (.ns5): samples bit-identical | **FAIL** | 109,224 of 109,225 samples in the NWB file; the 109,224 present are identical; +1 sample(s) missing at the end |
| ElectricalSeries: rate and start | PASS | rate 30000.0 Hz (file 30000.0), starting_time 0.0 |
| ElectricalSeries: channel order = .ns5 header | PASS | 96 channels, first [1, 2, 3], last [94, 95, 96] |
| ElectricalSeries: volts per count = .nev digitization | PASS | NWB [np.float64(1e-06)] V; .nev [np.float64(1e-06)] V |
| AnalogInputs (.ns2): samples bit-identical | **FAIL** | 3,640 of 3,641 samples in the NWB file; the 3,640 present are identical; +1 sample(s) missing at the end |
| AnalogInputs: volts per count = .nev digitization | PASS | NWB np.float64(0.000152592547) V; .nev factor(s) [21516] nV (21516 = Cerebus overflow for 152592.547) |
| AnalogInputs: rate | PASS | 1000.0 Hz (file 1000.0) |
| units: one row per (electrode, unit class) in the .nev | PASS | 218 rows, 218 pairs in the .nev |
| units: spike times = .nev ticks, exactly | **FAIL** | 111 of 218 units match tick for tick; 14,210 spikes vs 14,210 in the .nev; largest distance from a whole tick 7.3e-12 |
| units: linked to their electrode row | PASS | each unit's electrodes entry names its .nev electrode |
| subject: id, species, sex | PASS | L, Macaca mulatta, F; age P6Y8M25D |

9 of 12 checks passed.
