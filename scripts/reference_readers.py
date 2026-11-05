"""Minimal Blackrock readers written straight from the file specification.

They exist only to check NeuroConv's output against something that shares no
code with it (NeuroConv reads Blackrock through SpikeInterface -> Neo). They
cover just what the round-trip check needs:

  * NSx 2.1 ("NEURALSG"): continuous int16 samples and channel IDs.
  * NEV 2.x ("NEURALEV"): spike packets (timestamp, electrode, unit) and the
    per-electrode digitization factor from the NEUEVWAV extended headers.

Spec: Blackrock Microsystems, "NEV and NSx File Specification".
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class NSx21:
    label: str
    period: int  # in ticks of the 30 kHz master clock
    channel_ids: np.ndarray  # uint32, shape (n_channels,)
    data: np.ndarray  # int16, shape (n_samples, n_channels); raw ADC counts

    @property
    def sampling_rate(self) -> float:
        return 30000.0 / self.period


def read_nsx21(path: str | Path) -> NSx21:
    """NSx 2.1: 8-byte ID, 16-byte label, uint32 period, uint32 channel count,
    uint32 channel IDs, then interleaved int16 samples to the end of the file."""
    raw = Path(path).read_bytes()
    if raw[:8] != b"NEURALSG":
        raise ValueError(f"{path}: not an NSx 2.1 file (id={raw[:8]!r})")
    label = raw[8:24].split(b"\x00", 1)[0].decode("latin-1")
    period, n_ch = struct.unpack_from("<II", raw, 24)
    channel_ids = np.frombuffer(raw, dtype="<u4", count=n_ch, offset=32).copy()
    header_bytes = 32 + 4 * n_ch
    body = len(raw) - header_bytes
    if body % (2 * n_ch):
        raise ValueError(f"{path}: {body} data bytes is not a whole number of samples")
    data = np.frombuffer(raw, dtype="<i2", offset=header_bytes).reshape(-1, n_ch).copy()
    return NSx21(label=label, period=period, channel_ids=channel_ids, data=data)


@dataclass
class NEVSpikes:
    spec: str
    timestamp_resolution: int  # ticks per second
    timestamps: np.ndarray  # uint32 ticks
    electrodes: np.ndarray  # uint16 packet IDs (electrode IDs)
    units: np.ndarray  # uint8 unit classification (0 = unsorted, 255 = noise)
    digitization_nv: dict[int, int]  # electrode ID -> nV per bit (NEUEVWAV)


def read_nev_spikes(path: str | Path) -> NEVSpikes:
    """NEV 2.x: 336-byte basic header, 32-byte extended headers, then fixed-size
    data packets. Spike packets have packet ID 1..2048 (electrode); ID 0 is
    digital/serial input, which is skipped here."""
    raw = Path(path).read_bytes()
    if raw[:8] != b"NEURALEV":
        raise ValueError(f"{path}: not a NEV file (id={raw[:8]!r})")
    major, minor = raw[8], raw[9]
    bytes_headers, bytes_packet, ts_res = struct.unpack_from("<III", raw, 12)
    (n_ext,) = struct.unpack_from("<I", raw, 332)

    digitization: dict[int, int] = {}
    for i in range(n_ext):
        off = 336 + 32 * i
        if raw[off : off + 8] == b"NEUEVWAV":
            electrode, _fe_id, _fe_pin, dig_nv = struct.unpack_from("<HBBH", raw, off + 8)
            digitization[electrode] = dig_nv

    n_packets = (len(raw) - bytes_headers) // bytes_packet
    packets = np.frombuffer(
        raw,
        dtype=np.dtype(
            [("ts", "<u4"), ("pid", "<u2"), ("unit", "u1"), ("_r", "u1"), ("_w", f"V{bytes_packet - 8}")]
        ),
        count=n_packets,
        offset=bytes_headers,
    )
    spikes = packets[(packets["pid"] >= 1) & (packets["pid"] <= 2048)]
    return NEVSpikes(
        spec=f"{major}.{minor}",
        timestamp_resolution=ts_res,
        timestamps=spikes["ts"].copy(),
        electrodes=spikes["pid"].copy(),
        units=spikes["unit"].copy(),
        digitization_nv=digitization,
    )
