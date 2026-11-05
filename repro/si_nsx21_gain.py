"""SpikeInterface reports gain 1.0 uV/count for NSx 2.1 channels whatever the .nev says.

Usage: python repro/si_nsx21_gain.py <ephy_testing_data>/blackrock/blackrock_2_1
"""
import os
import sys

from neo.rawio import BlackrockRawIO
from spikeinterface.extractors import read_blackrock

stem = os.path.join(sys.argv[1], "l101210-001")

io = BlackrockRawIO(filename=stem)  # .nev present, so Neo can scale the 2.1 streams
io.parse_header()
ch = io.header["signal_channels"]

for nb in ("5", "2"):
    rec = read_blackrock(file_path=f"{stem}.ns{nb}", stream_id=nb)
    neo_ch = ch[ch["stream_id"] == nb]
    si_gains = sorted({float(g) for g in rec.get_channel_gains().round(6)})
    neo_gains = sorted({float(g) for g in neo_ch["gain"].round(6)})
    print(f"ns{nb}: spikeinterface gain_to_uV {si_gains}, Neo with .nev {neo_gains} {sorted({str(u) for u in neo_ch['units']})}")
