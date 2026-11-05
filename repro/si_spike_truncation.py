"""SpikeInterface's Blackrock sorting puts some spikes one sample early.

Compares each unit's frames from read_blackrock_sorting with the raw .nev
timestamps Neo returns for the same spike channel (ticks at 30 kHz).

Usage: python repro/si_spike_truncation.py <ephy_testing_data>/blackrock/blackrock_2_1
"""
import os
import sys

import numpy as np
from spikeinterface.extractors import read_blackrock_sorting

nev = os.path.join(sys.argv[1], "l101210-001.nev")
sorting = read_blackrock_sorting(file_path=nev, sampling_frequency=30000.0)
neo = sorting.neo_reader

diffs = []
units_off = 0
for i, unit_id in enumerate(sorting.unit_ids):
    ticks = neo.get_spike_timestamps(block_index=0, seg_index=0, spike_channel_index=i).astype(np.int64)
    frames = sorting.get_unit_spike_train(unit_id)
    d = frames - ticks
    diffs.append(d)
    units_off += bool(np.any(d))
d = np.concatenate(diffs)
print(f".nev timestamp resolution: {neo._nev_basic_header['timestamp_resolution']}")
values, counts = np.unique(d, return_counts=True)
print(f"spikes: {d.size}, frame - tick: { {int(v): int(c) for v, c in zip(values, counts)} }")
print(f"units with at least one shifted spike: {units_off} of {len(sorting.unit_ids)}")
print("30936 / 30000 * 30000 =", repr(30936 / 30000 * 30000))
