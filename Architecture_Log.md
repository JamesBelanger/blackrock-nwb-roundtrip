---
last_updated: 2026-11-05
tags: [pipeline, nwb, blackrock]
---

# Architecture Log: blackrock-nwb-roundtrip

## Purpose
Converts a public Blackrock 2.1 recording to NWB with NeuroConv, verifies the output exactly against an independent spec-based reader, and inspects one published DANDI session. Public data only.

## Layout
| Path | Role |
|---|---|
| `scripts/fetch_data.py` | Stdlib-only downloader. Blackrock `blackrock_2_1` set from G-Node GIN plus DANDI:000004 asset `5b2d5087…` (sub-P19HMH). Writes `data/raw/MANIFEST.json` with SHA-256 hashes. |
| `scripts/reference_readers.py` | `read_nsx21` (NSx 2.1, `NEURALSG`) and `read_nev_spikes` (NEV 2.x spike packets plus NEUEVWAV digitization), written from Blackrock's spec. numpy only. |
| `scripts/convert_to_nwb.py` | NeuroConv `ConverterPipe(Recording=ns5, Sorting=nev)`, then `AnalogInputs` TimeSeries from ns2, then `configure_and_write_nwbfile`. Default output `data/nwb/l101210-001.nwb`; `--upstream` writes `_upstream.nwb`. |
| `scripts/verify_roundtrip.py` | 12 exact checks (samples, rates, channel order, volts per count, unit set, spike ticks, unit-electrode links, subject, start time). Writes `reports/roundtrip_<stem>.md`; exits 1 on any failure. |
| `scripts/inspect_dandi_session.py` | NWB Inspector (dandi config) plus a new/old label vs image-identity check. Writes `reports/dandi000004_<subject>.md`. |
| `UPSTREAM_ISSUES.md` | Three unfiled issue drafts (Neo, SpikeInterface ×2) and two already-known items. |

## Design decisions
- **Independent reference.** The check never imports NeuroConv, SpikeInterface or Neo. The MATLAB `.mat` exports in the test data were rejected as the reference because they share Neo's off-by-one (96 × 109,224).
- **Exact comparisons only.** Integer equality for samples, tick equality for spikes, `rtol=1e-12` for conversion factors. The spike error is invisible to a "times are whole ticks" check (largest distance 7e-12); only tick-for-tick comparison catches it.
- **Runtime patches, not forks.** The Neo sample count and the SpikeInterface spike rounding are monkeypatched in `convert_to_nwb.py` and imported after patching. `--upstream` reproduces stock behaviour for comparison.
- **Gains from Neo with the .nev loaded** (`nev_gains_uv`), because `BlackrockRecordingExtractor` hard-codes `load_nev=False`.
- **Metadata only from sources:** Brochier et al. 2018 Methods (sex, date of birth 2004-03-15, implant 2010-09-15, INT Marseille) and file headers. No experimenter is named, so the field is empty.
- **NeuroConv dict-based metadata format** (`Devices`, `Ecephys/ElectrodeGroups` with `device_metadata_key`). The old list format is deprecated, with removal from Aug 2027.

## Dependencies
Managed by uv (`pyproject.toml`, `uv.lock`, `.python-version` 3.12). Tested with neuroconv 0.10.2, pynwb 4.2.0, hdmf 6.2.0, spikeinterface 0.105.4, neo 0.14.6, nwbinspector 0.7.2, dandi 0.82.0, numpy 2.5.4.

## Known limitations
- The session start time is treated as UTC. The NEV header has no timezone field, and the UTC reading still has to be confirmed against Blackrock's spec PDF.
- The readers cover only NSx 2.1 and NEV 2.x spike packets, not 2.2+ data blocks, PTP timestamps or digital events.
- The patches target private Neo/SpikeInterface methods and may break on upgrade. Drop them once upstream fixes land.
- NEV waveforms are not written to NWB.
- The DANDI check covers one session. catalystneuro/encore#47 has the dataset-wide audit.

## Changelog
- **2026-11-05:** Initial build. Conversion, round-trip check (12/12 with patches, 9/12 stock), NWB Inspector clean apart from the experimenter suggestion, DANDI:000004 inspection, three upstream issue drafts.
