# Upstream issue drafts

Found while converting the public Blackrock test recording `blackrock_2_1/l101210-001` and checking the NWB output value by value (`scripts/verify_roundtrip.py`). All three reproduce with public files from https://gin.g-node.org/NeuralEnsemble/ephy_testing_data.

Versions: neo 0.14.6, spikeinterface 0.105.4, neuroconv 0.10.2, Python 3.12, Windows 11.

Searched each tracker on 2026-11-05 and found no existing report. **Not filed yet.**

---

## 1. python-neo: `BlackrockRawIO` drops the last sample of every NSx 2.1 file

**Repo:** NeuralEnsemble/python-neo

`_parse_nsx_data_v21` computes

```python
num_samples = int((filesize - bytes_in_headers) / (2 * channels) - 1)
```

The trailing `- 1` always drops the final sample, even when the data section holds a whole number of samples.

**Reproduce** (counts from the file size: header = 32 + 4 × channels bytes, then int16 samples):

| File | Samples in file | Neo reads |
|---|---|---|
| `blackrock_2_1/l101210-001.ns5` (96 ch) | 109,225 | 109,224 |
| `blackrock_2_1/l101210-001.ns2` (6 ch) | 3,641 | 3,640 |
| `version_2_1/spikes/offline_sorted_units/online_sorted_units.ns5` | 9,000 (README says 9,000) | 8,999 |
| same, `.ns2` | 300 (README says 300) | 299 |

```python
from neo.rawio import BlackrockRawIO
io = BlackrockRawIO(filename="blackrock_2_1/l101210-001"); io.parse_header()
io.get_signal_size(0, 0, 1)   # 109224 for the ns5 stream
import os; (os.path.getsize("blackrock_2_1/l101210-001.ns5") - (32 + 4 * 96)) / (2 * 96)   # 109225.0
```

The dropped sample is ordinary signal: no zeros, and its step from the previous sample (mean 5.0 counts across channels) is close to the file's typical step (4.3). Blackrock's own reader reads it. NPMK `openNSx.m` (master, line 825) has `DataPoints = double(f.EOF-f.EOexH)/(channelCount*2)` with no `- 1`.

The MATLAB reference files in the test data (`l101210-001_nev-02_ns5.mat`, 96 × 109,224) also stop one sample short, so a test that compares against them will not catch this.

**Fix:** `num_samples = (filesize - bytes_in_headers) // (2 * channels)`, plus updating the length expectation in any test that compares against the `.mat` export.

**Impact:** one sample (33 µs at 30 kHz) at the end of each 2.1 file. Small, but downstream converters inherit it.

---

## 2. spikeinterface: Blackrock sorting truncates spike times, so about 2% of spikes land one sample early

**Repo:** SpikeInterface/spikeinterface

`NeoSortingSegment.get_unit_spike_train` (extractors/neoextractors/neobaseextractor.py) does, when `neo_returns_frames` is False:

```python
spike_frames = ((spike_times_seconds - t_start) * self._sampling_frequency).astype("int64")
```

Neo turns the integer .nev ticks into seconds, and this line turns them back into frames. Float round-off leaves some products just below an integer (`30936 / 30000 * 30000 == 30935.999…`), and `astype` truncates, so those spikes move one sample earlier.

**Reproduce:** `BlackrockSortingExtractor` on `blackrock_2_1/l101210-001.nev` with `sampling_frequency=30000`. Compare each unit's frames with the raw .nev timestamps for that electrode and unit: 272 of 14,210 spikes (1.9%) are exactly one tick early, spread over 107 of 218 units. Over ticks 0–109,225, 2,517 values (2.3%) truncate this way.

```python
import numpy as np
k = np.arange(109226); ((k / 30000.0) * 30000.0).astype(np.int64) != k   # 2,517 True
```

**Which readers:** the Blackrock and MEArec sorting extractors (the ones with `neo_returns_frames = False`). Plexon, Plexon2, Neuralynx, NeuroExplorer and Spike2 return frames directly and are not affected. NeuroConv's `BlackrockSortingInterface` goes through this path, so NWB units tables written from .nev files by NeuroConv carry the error.

**Fix:** `np.round((spike_times_seconds - t_start) * self._sampling_frequency).astype("int64")`.

---

## 3. spikeinterface: NSx 2.1 recordings get gain = 1 µV/count whatever the .nev says

**Repo:** SpikeInterface/spikeinterface (NeuroConv inherits it)

NSx 2.1 files have no extended headers, so their voltage scaling is only in the .nev digitization factors. Neo builds 2.1 gains from the .nev when it is loaded (`_build_nsx_v21_ext_header`). `BlackrockRecordingExtractor.__init__` always sets `neo_kwargs["load_nev"] = False`, so Neo warns "Cannot rescale to voltage", and the gain falls back to 1.0 (`fill_value = 1.0` in neobaseextractor.py, "should be np.nan"). Nothing downstream sees the warning, and NeuroConv writes `conversion = 1e-6` V per count.

**Reproduce** with `blackrock_2_1/l101210-001`: the .nev gives 1000 nV/count for electrodes 1–128 and 21516 for analog inputs 129–144 (Neo and NPMK map 21516 to 152,592.547 nV, a known Cerebus overflow, giving ±5 V). `BlackrockRecordingExtractor(file_path="…ns2", stream_id="2").get_channel_gains()` returns `[1., 1., …]`, where Neo with the .nev loaded gives 152.592547 µV/count.

For the neural channels in this file 1 µV/count happens to be correct. A 2.1 recording digitized at 250 nV/count would be written 4× too large in volts, with no error.

**Fix options:** load the .nev header (not the spikes) for 2.1 files when it is present, or set gains to NaN instead of 1.0 so the missing scaling is visible.

---

## Checked and already known

- **nwbinspector:** `check_units_table_duration` crashes on files with signed (`int32`) `spike_times_index` (`uint64` concatenated with `int32` promotes to `float64`). Reported in NeurodataWithoutBorders/nwbinspector#740, fixed by #741 (merged 2026-09-09). Not in the latest release (0.7.2, 2026-05-19), so DANDI:000004 files still hit it.
- **DANDI:000004:** `new_old_labels_recog` is described as 0 = old, but the data use 1 = old. Logged in catalystneuro/encore#47 (2026-10-15). `scripts/inspect_dandi_session.py` reaches the same result from image identity: none of the 50 label-0 recognition images were shown during learning, and every recognition image that was shown during learning carries label 1.
