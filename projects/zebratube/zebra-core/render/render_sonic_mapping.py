#!/usr/bin/env python3
"""render_sonic_mapping.py — visualise the acoustic arc of the text.

Plots tempo, intensity, and harmonic position across narrative time.
Also outputs a minimal MIDI file if pretty_midi is available.

Usage:
    python3 render/render_sonic_mapping.py data/projections/essay/sonic_mapping.json
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

OUT_PNG  = Path("data/videos/sonic_mapping.png")
OUT_MIDI = Path("data/videos/sonic_mapping.mid")


HARMONIC_VALUES = {"I": 0, "II": 1, "III": 2, "IV": 3,
                   "V": 4, "VI": 5, "VII": 6}


def main() -> None:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)

    segments = data.get("segments", [])
    if not segments:
        print("WARNING: no segments to render")
        return

    xs = list(range(len(segments)))
    tempos     = [s["tempo_bpm"]  for s in segments]
    intensities= [s["intensity"]  for s in segments]
    harmonics  = [HARMONIC_VALUES.get(s.get("harmonic_position", "I"), 0) for s in segments]
    labels     = [s["event"][:20] for s in segments]

    fig = plt.figure(figsize=(14, 8), facecolor="#0d0d1a")
    gs  = gridspec.GridSpec(3, 1, hspace=0.45)

    def style_ax(ax, title, ylabel, color):
        ax.set_facecolor("#12122a")
        ax.spines[:].set_color("#334")
        ax.tick_params(colors="white", labelsize=7)
        ax.yaxis.label.set_color("white")
        ax.xaxis.label.set_color("white")
        ax.set_ylabel(ylabel, fontsize=8)
        ax.set_title(title, color=color, fontsize=9, loc="left")

    # Tempo
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(xs, tempos, color="#FFDD44", linewidth=1.5)
    ax1.fill_between(xs, tempos, alpha=0.2, color="#FFDD44")
    style_ax(ax1, "Tempo", "BPM", "#FFDD44")
    ax1.set_xticks([])

    # Intensity / tension
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(xs, intensities, color="#FF6666", linewidth=1.5)
    ax2.fill_between(xs, intensities, alpha=0.2, color="#FF6666")
    style_ax(ax2, "Tension / Intensity", "0–1", "#FF6666")
    ax2.set_xticks([])

    # Harmonic position
    ax3 = fig.add_subplot(gs[2])
    ax3.plot(xs, harmonics, color="#88BBFF", linewidth=1.5, marker="o", markersize=4)
    style_ax(ax3, "Harmonic Position", "degree", "#88BBFF")
    ax3.set_yticks(list(HARMONIC_VALUES.values()))
    ax3.set_yticklabels(list(HARMONIC_VALUES.keys()), color="white", fontsize=7)
    ax3.set_xticks(xs)
    ax3.set_xticklabels(labels, rotation=45, ha="right", color="white", fontsize=6)

    arc   = data.get("arc_shape", "")
    instr = data.get("suggested_instrumentation", "")
    fig.suptitle(
        f"Sonic Mapping  |  arc: {arc}  |  {instr}",
        color="white", fontsize=10, y=0.98,
    )

    plt.savefig(OUT_PNG, dpi=130, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close()
    print(f"Saved: {OUT_PNG}")

    # Optional MIDI export
    try:
        import pretty_midi
        midi = pretty_midi.PrettyMIDI()
        inst = pretty_midi.Instrument(program=48)  # strings
        t = 0.0
        for seg in segments:
            bpm   = max(40, seg["tempo_bpm"])
            dur   = 60.0 / bpm
            pitch = 48 + HARMONIC_VALUES.get(seg.get("harmonic_position", "I"), 0) * 2
            vel   = min(127, int(40 + seg["intensity"] * 80))
            note  = pretty_midi.Note(velocity=vel, pitch=pitch, start=t, end=t + dur * 0.9)
            inst.notes.append(note)
            t += dur
        midi.instruments.append(inst)
        midi.write(str(OUT_MIDI))
        print(f"Saved MIDI: {OUT_MIDI}")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
