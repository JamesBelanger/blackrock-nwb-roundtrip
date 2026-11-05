# Session Log: blackrock-nwb-roundtrip

## 2026-11-05
- Built the repo from scratch: uv env (Python 3.12), `fetch_data.py`, spec-based `reference_readers.py`, `convert_to_nwb.py`, `verify_roundtrip.py`, `inspect_dandi_session.py`.
- Conversion of `l101210-001` passes 12/12 exact checks with the two runtime patches. The stock toolchain passes 9/12; its three failures map to upstream bugs (Neo NSx 2.1 last sample; SpikeInterface spike truncation; plus the gain fallback, which the converter works around).
- NWB Inspector (dandi): 0 critical, 0 violations, 1 suggestion (experimenter).
- DANDI:000004 sub-P19HMH: 17 Inspector issues. New/old label reversal confirmed from image identity (already in catalystneuro/encore#47).
- Decisions: the reference shares no code with the converter; exact equality only; metadata only from the paper and headers; NeuroConv dict metadata format.
- Open: the UTC reading of the NEV time origin is not yet confirmed against Blackrock's spec PDF.
- Added `repro/`: three standalone scripts, one per upstream bug, run against the public test data.
