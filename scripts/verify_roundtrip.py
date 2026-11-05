"""Check an NWB file from convert_to_nwb.py against the original Blackrock files.

The reference side uses only reference_readers.py (written from Blackrock's
file spec) and pynwb to open the NWB file: nothing from NeuroConv,
SpikeInterface or Neo, the code that did the conversion.

Every check is exact. Correlations and tolerances can hide off-by-one and
scaling errors, so samples are compared as integers, spike times as clock
ticks, and conversion factors against the digitization factors in the .nev.

Usage:
  python scripts/verify_roundtrip.py data/nwb/l101210-001.nwb
Writes reports/roundtrip_<file stem>.md and exits 1 if any check fails.
"""
from __future__ import annotations

import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pynwb import NWBHDF5IO

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reference_readers import read_nev_spikes, read_nsx21  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STEM = ROOT / "data" / "raw" / "blackrock" / "l101210-001"
# Cerebus firmware bug: a digitization factor of 21516 nV stands for
# 152592.547 nV (+-5 V analog inputs). Same correction as Blackrock's NPMK
# (openNEV.m) and Neo.
CEREBUS_OVERFLOW = {21516: 152592.547}

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    results.append((name, bool(ok), detail))


def ragged(table, column):
    """Return a column of a pynwb ragged (indexed) column as a list of arrays."""
    index = table[column]
    flat = np.asarray(index.target.data[:])
    ends = np.asarray(index.data[:])
    starts = np.concatenate([[0], ends[:-1]])
    return [flat[s:e] for s, e in zip(starts, ends)]


def nev_time_origin(path: Path) -> datetime:
    y, mo, _dow, d, h, mi, s, ms = struct.unpack_from("<8H", path.read_bytes()[:336], 28)
    return datetime(y, mo, d, h, mi, s, ms * 1000, tzinfo=timezone.utc)


def compare_samples(name: str, nwb_data: np.ndarray, ref: np.ndarray) -> None:
    n_nwb, n_ref = nwb_data.shape[0], ref.shape[0]
    overlap = min(n_nwb, n_ref)
    same_overlap = nwb_data.shape[1] == ref.shape[1] and np.array_equal(nwb_data[:overlap], ref[:overlap])
    check(
        f"{name}: samples bit-identical",
        same_overlap and n_nwb == n_ref,
        f"{n_nwb:,} of {n_ref:,} samples in the NWB file; the {overlap:,} present are "
        + ("identical" if same_overlap else "NOT identical")
        + ("" if n_nwb == n_ref else f"; {n_ref - n_nwb:+,} sample(s) missing at the end"),
    )


def main(nwb_path: Path) -> int:
    ns5 = read_nsx21(STEM.with_suffix(".ns5"))
    ns2 = read_nsx21(STEM.with_suffix(".ns2"))
    nev = read_nev_spikes(STEM.with_suffix(".nev"))

    with NWBHDF5IO(str(nwb_path), "r") as io:
        f = io.read()

        # --- session -----------------------------------------------------
        origin = nev_time_origin(STEM.with_suffix(".nev"))
        check("session_start_time = .nev time origin (UTC)", f.session_start_time == origin,
              f"{f.session_start_time.isoformat()} vs {origin.isoformat()}")

        # --- raw 30 kHz electrodes -----------------------------------------
        es = f.acquisition["ElectricalSeries"]
        compare_samples("ElectricalSeries (.ns5)", np.asarray(es.data[:]), ns5.data)
        check("ElectricalSeries: rate and start", es.rate == ns5.sampling_rate and (es.starting_time or 0.0) == 0.0,
              f"rate {es.rate} Hz (file {ns5.sampling_rate}), starting_time {es.starting_time}")
        rows = np.asarray(es.electrodes.data[:])
        row_ids = np.asarray(f.electrodes["blackrock_electrode_id"].data[:]).astype(int)
        es_ids = [int(row_ids[r]) for r in rows]
        check("ElectricalSeries: channel order = .ns5 header", es_ids == ns5.channel_ids.tolist(),
              f"{len(es_ids)} channels, first {es_ids[:3]}, last {es_ids[-3:]}")
        per_ch = (np.asarray(es.channel_conversion[:]) if es.channel_conversion is not None
                  else np.ones(len(es_ids))) * es.conversion
        expected = np.array([nev.digitization_nv[c] * 1e-9 for c in es_ids])
        check("ElectricalSeries: volts per count = .nev digitization", np.allclose(per_ch, expected, rtol=1e-12, atol=0),
              f"NWB {sorted(set(np.round(per_ch, 15)))} V; .nev {sorted(set(np.round(expected, 15)))} V")

        # --- analog inputs -------------------------------------------------
        ai = f.acquisition["AnalogInputs"]
        compare_samples("AnalogInputs (.ns2)", np.asarray(ai.data[:]), ns2.data)
        dig = {nev.digitization_nv[int(c)] for c in ns2.channel_ids}
        exp_ai = {CEREBUS_OVERFLOW.get(d, d) * 1e-9 for d in dig}
        check("AnalogInputs: volts per count = .nev digitization", len(exp_ai) == 1 and np.isclose(ai.conversion, exp_ai.pop(), rtol=1e-12),
              f"NWB {ai.conversion!r} V; .nev factor(s) {sorted(dig)} nV (21516 = Cerebus overflow for 152592.547)")
        check("AnalogInputs: rate", ai.rate == ns2.sampling_rate, f"{ai.rate} Hz (file {ns2.sampling_rate})")

        # --- units -----------------------------------------------------------
        u = f.units
        el_ids = np.asarray(u["blackrock_electrode_id"].data[:]).astype(int)
        classes = np.asarray(u["blackrock_unit_class"].data[:]).astype(int)
        spikes = ragged(u, "spike_times")
        linked = ragged(u, "electrodes")
        pairs = sorted(set(zip(nev.electrodes.tolist(), nev.units.tolist())))
        check("units: one row per (electrode, unit class) in the .nev",
              sorted(zip(el_ids.tolist(), classes.tolist())) == pairs, f"{len(u)} rows, {len(pairs)} pairs in the .nev")

        res = nev.timestamp_resolution
        n_exact = 0
        worst_frac = 0.0
        for e, c, t in zip(el_ids, classes, spikes):
            ticks = np.asarray(t) * res
            worst_frac = max(worst_frac, float(np.max(np.abs(ticks - np.round(ticks)))) if len(t) else 0.0)
            ref = nev.timestamps[(nev.electrodes == e) & (nev.units == c)].astype(np.int64)
            n_exact += np.array_equal(np.round(ticks).astype(np.int64), ref)
        check("units: spike times = .nev ticks, exactly", n_exact == len(u),
              f"{n_exact} of {len(u)} units match tick for tick; "
              f"{sum(len(t) for t in spikes):,} spikes vs {len(nev.timestamps):,} in the .nev; "
              f"largest distance from a whole tick {worst_frac:.1e}")
        link_ok = all(len(r) == 1 and int(row_ids[r[0]]) == e for r, e in zip(linked, el_ids))
        check("units: linked to their electrode row", link_ok, "each unit's electrodes entry names its .nev electrode")

        # --- subject ---------------------------------------------------------
        s = f.subject
        check("subject: id, species, sex", bool(s and s.subject_id and s.species and s.sex),
              f"{s.subject_id}, {s.species}, {s.sex}; age {s.age or 'not given (not in the source)'}")

    lines = [f"# Round-trip check: `{nwb_path.name}`", "",
             f"Reference: `{STEM.name}.ns5/.ns2/.nev` read with `scripts/reference_readers.py`.", "",
             "| Check | Result | Detail |", "|---|---|---|"]
    lines += [f"| {n} | {'PASS' if ok else '**FAIL**'} | {d} |" for n, ok, d in results]
    n_pass = sum(ok for _, ok, _ in results)
    lines += ["", f"{n_pass} of {len(results)} checks passed."]
    report = "\n".join(lines) + "\n"
    out = ROOT / "reports" / f"roundtrip_{nwb_path.stem}.md"
    out.write_text(report, encoding="utf-8")
    print(report)
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(Path(sys.argv[1]).resolve()))
