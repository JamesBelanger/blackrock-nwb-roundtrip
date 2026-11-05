"""Inspect one published session of DANDI:000004 (Chandravadia et al. 2020).

Two checks on a file someone else converted:
  1. NWB Inspector with DANDI's configuration: what today's validator says.
  2. Do the new/old labels agree with the data? A recognition-phase image is
     "old" exactly when it was shown in the learning phase, so the labels can
     be checked against image identity instead of being taken on trust.

Usage:
  python scripts/inspect_dandi_session.py data/raw/dandi_000004/<file>.nwb
Writes reports/dandi000004_<subject>.md.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from nwbinspector import inspect_nwbfile, load_config
from pynwb import NWBHDF5IO

ROOT = Path(__file__).resolve().parents[1]


def main(path: Path) -> int:
    messages = list(inspect_nwbfile(nwbfile_path=str(path), config=load_config("dandi")))
    by_level = Counter(m.importance.name for m in messages)

    with NWBHDF5IO(str(path), "r") as io:
        f = io.read()
        subject = f.subject.subject_id
        nwb_version = io._file.attrs.get("nwb_version")
        trials = f.trials.to_dataframe()
        label_desc = " ".join(f.trials["new_old_labels_recog"].description.split())
        n_units = len(f.units)

    img = trials.external_image_file.str.replace("\\", "/", regex=False).str.split("/").str[-2:].str.join("/")
    learned = set(img[trials.stim_phase == "learn"])
    recog = trials[trials.stim_phase == "recog"].assign(shown_in_learning=img.isin(learned))
    table = recog.groupby(["new_old_labels_recog", "shown_in_learning"]).size()

    lines = [
        f"# DANDI:000004 session `{path.name}`",
        "",
        f"Subject {subject}; NWB schema {nwb_version}; {n_units} units; {len(trials)} trials.",
        "",
        "## NWB Inspector (config: dandi)",
        "",
        "| Level | Count |",
        "|---|---|",
        *[f"| {lvl} | {n} |" for lvl, n in sorted(by_level.items())],
        "",
        "| Level | Check | Location | Message |",
        "|---|---|---|---|",
    ]
    for m in sorted(messages, key=lambda m: -m.importance.value):
        msg = " ".join(str(m.message).split())[:160]
        lines.append(f"| {m.importance.name} | {m.check_function_name} | {m.location or ''} | {msg} |")
    lines += [
        "",
        "## New/old labels against the images",
        "",
        f"Column description in the file: \"{label_desc}\"",
        "",
        "| new_old_labels_recog | image shown in learning phase | trials |",
        "|---|---|---|",
        *[f"| {lab} | {shown} | {n} |" for (lab, shown), n in table.items()],
        "",
    ]
    out = ROOT / "reports" / f"dandi000004_{subject}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(Path(sys.argv[1]).resolve()))
