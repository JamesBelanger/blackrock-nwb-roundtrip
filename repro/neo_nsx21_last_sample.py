"""Neo's BlackrockRawIO reads one sample fewer than an NSx 2.1 file holds.

Usage: python repro/neo_nsx21_last_sample.py <ephy_testing_data>/blackrock/blackrock_2_1
"""
import os
import sys

from neo.rawio import BlackrockRawIO

stem = os.path.join(sys.argv[1], "l101210-001")
io = BlackrockRawIO(filename=stem)
io.parse_header()
for i, stream in enumerate(io.header["signal_streams"]):
    nb = int(stream["name"][-1])
    n_ch = io.signal_channels_count(i)
    # NSx 2.1: 32-byte header + 4 bytes per channel ID, then int16 samples
    in_file = (os.path.getsize(f"{stem}.ns{nb}") - (32 + 4 * n_ch)) / (2 * n_ch)
    print(f"{stream['name']}: neo reads {io.get_signal_size(0, 0, i)} samples, file holds {in_file}")
