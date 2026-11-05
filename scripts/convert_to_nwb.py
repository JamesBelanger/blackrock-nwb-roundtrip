"""Convert the public Blackrock 2.1 recording l101210-001 to NWB with NeuroConv.

What goes in:
  * .ns5  -> acquisition/ElectricalSeries: 96 channels, 30 kHz, raw int16 counts
             with the volts conversion stored alongside (no rescaling of data).
  * .nev  -> units: one row per (electrode, Blackrock unit class), linked to its
             electrode row, with the electrode ID and unit class kept as columns.
  * .ns2  -> acquisition/AnalogInputs: the 6 analog-input channels (1 kHz) as a
             plain TimeSeries. They are not brain electrodes, so they do not go
             in the electrodes table.

Five things the stock toolchain (NeuroConv 0.10.2, SpikeInterface 0.105.4,
Neo 0.14.6) gets wrong or leaves out for this file, handled below:
  1. Units lose their origin. SpikeInterface renumbers Blackrock units 0..N-1
     and drops which electrode and unit class each came from. We restore both
     from Neo's spike-channel names ("ch12#2" = electrode 12, unit class 2) and
     pass the unit-to-electrode links.
  2. Volts scaling is guessed. NSx 2.1 files carry no scaling; it lives in the
     .nev digitization factors. SpikeInterface opens Blackrock files with
     load_nev=False, so Neo cannot scale and SpikeInterface fills gain = 1 uV
     per count. That is right for these neural channels (1000 nV/count) by
     coincidence and wrong for the analog inputs. We take the gains from Neo
     with the .nev loaded.
  3. Wrong timezone. The .nev time origin has no timezone field, and pynwb
     stamps the converting computer's local zone on it. We set UTC explicitly.
  4. Neo drops the last sample of every NSx 2.1 file.
  5. SpikeInterface truncates (instead of rounding) when it turns Neo spike
     times back into sample frames, so about 2% of spikes land one sample early.
  Fixes 4 and 5 are one-line corrections patched in at runtime. --upstream
  skips both, so the round-trip check can show what they change.

Usage:
  python scripts/convert_to_nwb.py              # -> data/nwb/l101210-001.nwb
  python scripts/convert_to_nwb.py --upstream   # -> data/nwb/l101210-001_upstream.nwb
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "blackrock"
OUT = ROOT / "data" / "nwb"
STEM = RAW / "l101210-001"

SOURCE = (
    "Brochier T, Zehl L, Hao Y, et al. Massively parallel recordings in macaque motor "
    "cortex during an instructed delayed reach-to-grasp task. Sci Data 5, 180055 (2018). "
    "Raw data: G-Node GIN doi:10.12751/g-node.f83565 (CC BY 4.0). This file converts the "
    "3.6 s excerpt of session l101210-001 that Neo and NeuroConv use as test data "
    "(gin.g-node.org/NeuralEnsemble/ephy_testing_data, blackrock/blackrock_2_1)."
)


def patch_neo_v21_sample_count() -> None:
    """Make Neo read every complete sample of an NSx 2.1 file.

    neo/rawio/blackrockrawio.py::_parse_nsx_data_v21 computes
        num_samples = int((filesize - bytes_in_headers) / (2 * channels) - 1)
    The trailing "- 1" drops the final sample even when the file holds a whole
    number of samples. Blackrock's own reader (NPMK openNSx.m) has no "- 1".
    """
    from neo.rawio import blackrockrawio

    original = blackrockrawio.BlackrockRawIO._parse_nsx_data_v21

    def fixed(self, nsx_nb):
        blocks = original(self, nsx_nb)
        kw = blocks[0]["memmap_kwargs"]
        channels = int(self._nsx_basic_header[nsx_nb]["channel_count"])
        kw["num_samples"] = int((self._get_file_size(kw["filename"]) - kw["offset"]) // (2 * channels))
        return blocks

    blackrockrawio.BlackrockRawIO._parse_nsx_data_v21 = fixed


def patch_spikeinterface_spike_rounding() -> None:
    """Round, not truncate, when SpikeInterface turns Neo spike times into frames.

    spikeinterface/extractors/neoextractors/neobaseextractor.py,
    NeoSortingSegment.get_unit_spike_train, does
        spike_frames = ((spike_times_seconds - t_start) * fs).astype("int64")
    Float round-off puts some exact ticks just below an integer
    (30936 / 30000 * 30000 = 30935.999...), and astype truncates, so those
    spikes land one sample early. Same method with np.round.
    """
    from spikeinterface.extractors.neoextractors.neobaseextractor import NeoSortingSegment

    def get_unit_spike_train(self, unit_id, start_frame, end_frame):
        idx = self.map_from_unit_id_to_spike_channel_index(unit_id)
        ts = self.neo_reader.get_spike_timestamps(
            block_index=self.block_index, seg_index=self.segment_index, spike_channel_index=idx
        )
        if self.neo_returns_frames:
            frames = ts
        else:
            seconds = self.neo_reader.rescale_spike_timestamp(ts, dtype="float64")
            t_start = 0 if self._t_start is None else self._t_start
            frames = np.round((seconds - t_start) * self._sampling_frequency).astype("int64")
        if start_frame is not None:
            frames = frames[frames >= start_frame]
        if end_frame is not None:
            frames = frames[frames <= end_frame]
        return frames

    NeoSortingSegment.get_unit_spike_train = get_unit_spike_train


def nev_gains_uv(stream_id: str) -> dict[str, float]:
    """Per-channel gain (uV per count) for one NSx stream, read by Neo with the
    .nev loaded, since NSx 2.1 keeps its digitization factors there."""
    from neo.rawio import BlackrockRawIO

    io = BlackrockRawIO(filename=str(STEM))
    io.parse_header()
    chans = io.header["signal_channels"]
    chans = chans[chans["stream_id"] == stream_id]
    if not len(chans) or set(chans["units"]) != {"uV"}:
        raise ValueError(f"stream {stream_id}: no voltage scaling available (units={set(chans['units'])})")
    return {str(c["id"]): float(c["gain"]) for c in chans}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--upstream", action="store_true",
                    help="skip both runtime patches (Neo sample count, SpikeInterface spike rounding)")
    args = ap.parse_args()

    if not args.upstream:
        patch_neo_v21_sample_count()
        patch_spikeinterface_spike_rounding()

    # Import after the optional patch so every reader picks it up.
    from neuroconv import ConverterPipe
    from neuroconv.datainterfaces import BlackrockRecordingInterface, BlackrockSortingInterface
    from neuroconv.tools.nwb_helpers import configure_and_write_nwbfile
    from pynwb import TimeSeries
    from spikeinterface.extractors.neoextractors.blackrock import BlackrockRecordingExtractor

    recording = BlackrockRecordingInterface(file_path=STEM.with_suffix(".ns5"))
    sorting = BlackrockSortingInterface(file_path=STEM.with_suffix(".nev"), sampling_frequency=30000.0)

    # --- 1. restore electrode ID and unit class for every unit -------------
    names = sorting.sorting_extractor.neo_reader.header["spike_channels"]["name"]
    parsed = [re.fullmatch(r"ch(\d+)#(\d+)", str(n)) for n in names]
    if not all(parsed):
        raise ValueError(f"unexpected Neo spike-channel names: {names[:5]}")
    electrode_ids = np.array([int(m.group(1)) for m in parsed])
    unit_classes = np.array([int(m.group(2)) for m in parsed])
    sorting.sorting_extractor.set_property("blackrock_electrode_id", electrode_ids)
    sorting.sorting_extractor.set_property("blackrock_unit_class", unit_classes)

    channel_ids = [int(c) for c in recording.recording_extractor.get_channel_ids()]
    row_of_channel = {cid: row for row, cid in enumerate(channel_ids)}
    unit_electrode_indices = [[row_of_channel[e]] for e in electrode_ids]

    # --- 2. volts scaling from the .nev --------------------------------------
    rec = recording.recording_extractor
    ns5_gain = nev_gains_uv("5")
    gains = np.array([ns5_gain[c] for c in rec.get_channel_ids()])
    rec.set_channel_gains(gains)
    rec.set_property("gain_to_physical_unit", gains)
    rec.set_channel_groups(["0"] * len(channel_ids))
    rec.set_property("blackrock_electrode_id", np.array(channel_ids))

    converter = ConverterPipe(data_interfaces=dict(Recording=recording, Sorting=sorting))

    # --- 3. metadata: only what the source documents ------------------------
    md = converter.get_metadata()
    # The .nev stores its time origin with no timezone field. Treated here as
    # UTC (to confirm against Blackrock's spec PDF); left naive, pynwb would
    # stamp the converting computer's zone on a recording made in Marseille.
    start = md["NWBFile"]["session_start_time"]
    start = start if isinstance(start, datetime) else datetime.fromisoformat(str(start))
    md["NWBFile"]["session_start_time"] = start.replace(tzinfo=timezone.utc)
    md["NWBFile"].update(
        session_description=(
            "3.6 s excerpt of a Utah-array recording from macaque motor cortex during an "
            "instructed delayed reach-to-grasp task (session l101210-001, monkey L)."
        ),
        experiment_description=SOURCE,
        related_publications=["doi:10.1038/sdata.2018.55"],
        session_id="l101210-001",
        institution="Institut de Neurosciences de la Timone (INT), CNRS-Aix Marseille Universite, Marseille, France",
        keywords=["Blackrock", "Utah array", "motor cortex", "reach-to-grasp", "NWB conversion test"],
    )
    # No experimenter is named in the source, so that field stays empty.
    # Subject facts are from Brochier et al. 2018 (Methods, "Subjects"):
    # born 2004-03-15; array implanted 2010-09-15; recorded 2010-12-10.
    md["Subject"] = dict(
        subject_id="L",
        species="Macaca mulatta",
        sex="F",
        date_of_birth=datetime(2004, 3, 15, tzinfo=timezone.utc),
        age="P6Y8M25D",
        description=(
            "Rhesus macaque trained on an instructed delayed reach-to-grasp task. Utah array implanted "
            "2010-09-15 in the motor cortex contralateral to the working hand."
        ),
    )
    md.setdefault("Devices", {})["UtahArray"] = dict(
        name="UtahArray",
        description="10x10 Utah array (96 recording electrodes) recorded with a Blackrock Cerebus system.",
        manufacturer="Blackrock Microsystems",
    )
    md["Ecephys"]["ElectrodeGroups"] = {
        "0": dict(
            name="0",
            description="All 96 Utah-array electrodes.",
            location="motor cortex",
            device_metadata_key="UtahArray",
        )
    }
    md["Ecephys"]["Electrodes"] = [
        dict(name="blackrock_electrode_id", description="Blackrock electrode ID (NSx channel ID = NEV packet ID)."),
    ]
    md["Ecephys"]["UnitProperties"] = [
        dict(name="blackrock_electrode_id", description="Electrode (NEV packet ID) the unit was recorded on."),
        dict(
            name="blackrock_unit_class",
            description="Blackrock unit classification from the .nev file: 0 = unsorted threshold crossings, 1-16 = sorted units, 255 = noise.",
        ),
    ]

    conversion_options = dict(
        Recording=dict(iterator_options=dict(display_progress=False)),
        Sorting=dict(
            units_description="Online-sorted spikes from the .nev file, one row per (electrode, unit class).",
            unit_electrode_indices=unit_electrode_indices,
        ),
    )
    nwbfile = converter.create_nwbfile(metadata=md, conversion_options=conversion_options)

    # --- 4. analog inputs as a TimeSeries, not as electrodes ----------------
    ns2 = BlackrockRecordingExtractor(file_path=str(STEM.with_suffix(".ns2")), stream_id="2")
    ns2_gain = nev_gains_uv("2")
    gains_uv = np.array([ns2_gain[c] for c in ns2.get_channel_ids()])
    if not np.allclose(gains_uv, gains_uv[0]):
        raise ValueError("analog inputs have different gains; write one TimeSeries per gain")
    nwbfile.add_acquisition(
        TimeSeries(
            name="AnalogInputs",
            description=(
                "Blackrock analog inputs (.ns2, channel IDs "
                + ", ".join(ns2.get_channel_ids())
                + "): behavioral signals from the task's control system, fed to the Blackrock "
                "analog input port. Raw int16 counts; multiply by conversion for volts."
            ),
            data=ns2.get_traces(return_in_uV=False),
            unit="volts",
            conversion=float(gains_uv[0]) * 1e-6,
            rate=float(ns2.get_sampling_frequency()),
            starting_time=0.0,
        )
    )

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / ("l101210-001_upstream.nwb" if args.upstream else "l101210-001.nwb")
    configure_and_write_nwbfile(nwbfile=nwbfile, nwbfile_path=out, backend="hdf5")
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
