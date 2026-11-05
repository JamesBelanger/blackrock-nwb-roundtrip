# blackrock-nwb-roundtrip

Convert a public Blackrock recording to NWB with NeuroConv, then prove the NWB file matches the original files exactly.

The input is a 3.6 s excerpt of session `l101210-001` (monkey L, Utah array in motor cortex, reach-to-grasp task; Brochier et al. 2018, *Sci Data* 5:180055), which Neo and NeuroConv use as test data. The check side reads the Blackrock files with a ~100-line reader written from Blackrock's file specification (`scripts/reference_readers.py`), so it shares no code with the converter.

## Result

| | Stock toolchain | This repo |
|---|---|---|
| Raw 30 kHz samples (.ns5) | 109,224 of 109,225, last one dropped | 109,225 of 109,225, bit-identical |
| Analog inputs (.ns2) | 3,640 of 3,641 | 3,641 of 3,641, bit-identical |
| Spike times vs .nev ticks | 272 of 14,210 spikes one tick early | all 14,210 exact |
| Analog-input volts per count | 1 µV (a fallback value) | 152.59 µV, from the .nev |
| Units linked to electrodes | no (renumbered 0–217) | yes, plus electrode ID and unit class |
| Session start timezone | the converting computer's | UTC |
| Round-trip checks passed | 9 of 12 | 12 of 12 |
| NWB Inspector, DANDI config | | 0 critical, 0 violations, 1 suggestion (no experimenter is named in the source) |

Full reports: `reports/roundtrip_l101210-001.md` and `reports/roundtrip_l101210-001_upstream.md`. Three of the stock problems come from upstream libraries. They are written up in `UPSTREAM_ISSUES.md`, and each has a standalone script in `repro/` that runs against the public test data:

```bash
uv run python repro/neo_nsx21_last_sample.py data/raw/blackrock
uv run python repro/si_spike_truncation.py data/raw/blackrock
uv run python repro/si_nsx21_gain.py data/raw/blackrock
```

## What the conversion does

`scripts/convert_to_nwb.py`

- `.ns5` → `acquisition/ElectricalSeries`: 96 channels of raw int16 counts, with volts per count taken from the .nev digitization factors.
- `.nev` → `units`: one row per (electrode, Blackrock unit class), linked to its electrode, with `blackrock_electrode_id` and `blackrock_unit_class` columns.
- `.ns2` → `acquisition/AnalogInputs`: a plain `TimeSeries`. These are behavioral signals, not brain electrodes, so they stay out of the electrodes table.
- Metadata comes only from the paper and the file headers: species, sex, date of birth, implant date, institution. The experimenter field is empty because no experimenter is named.
- Two one-line upstream fixes (Neo sample count, SpikeInterface spike rounding) are patched in at runtime. `--upstream` turns them off.

## Also: one published dataset

`scripts/inspect_dandi_session.py` runs NWB Inspector on one session of DANDI:000004 (human MTL single neurons, Chandravadia et al. 2020) and checks its new/old labels against the images actually shown. Today's validator finds 17 issues in this 2021-era file, mostly schema drift: an age of `34` instead of `P34Y`, species `Human`, int32 index columns, and one validator crash that is already fixed upstream. The labels are reversed relative to their description, as catalystneuro/encore#47 also found. Report: `reports/dandi000004_P19HMH.md`.

## Run it

```bash
uv sync
uv run python scripts/fetch_data.py        # ~92 MB from G-Node GIN and DANDI, with SHA-256 manifest
uv run python scripts/convert_to_nwb.py
uv run python scripts/convert_to_nwb.py --upstream
uv run python scripts/verify_roundtrip.py data/nwb/l101210-001.nwb
uv run python scripts/verify_roundtrip.py data/nwb/l101210-001_upstream.nwb
uv run nwbinspector data/nwb/l101210-001.nwb --config dandi
uv run python scripts/inspect_dandi_session.py "data/raw/dandi_000004/sub-P19HMH_ses-20080601_obj-uw5up9_ecephys+image.nwb"
```

Tested with neuroconv 0.10.2, pynwb 4.2.0, spikeinterface 0.105.4, neo 0.14.6 and nwbinspector 0.7.2 on Python 3.12.

## Data and credit

- Blackrock files: https://gin.g-node.org/NeuralEnsemble/ephy_testing_data (`blackrock/blackrock_2_1`), an excerpt of the reach-to-grasp dataset at doi:10.12751/g-node.f83565 (CC BY 4.0).
- DANDI:000004 version 0.220126.1852, https://dandiarchive.org/dandiset/000004.

Data files are downloaded, not committed.
