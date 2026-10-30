"""Hilbert space-filling curve used to handle different resolutions.
Run with:  python examples/hilbert_coherence.py
Prints a coherency table and saves plot in docs/coerenza.png
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from sonifica.hilbert import coherence, listening_track


def field(n_rows: int, n_cols: int) -> np.ndarray:
    """Un campo continuo (pendenze + una "macchia") campionato su una griglia n_rows × n_cols."""
    yy, xx = np.meshgrid((np.arange(n_rows) + 0.5) / n_rows, (np.arange(n_cols) + 0.5) / n_cols, indexing="ij")
    f = np.sin(3 * xx) + np.cos(4 * yy) + 0.5 * np.exp(-((xx - 0.7) ** 2 + (yy - 0.3) ** 2) / 0.02)
    return (f - f.min()) / (f.max() - f.min())


BASE = (12, 10)
VARIANTS = [(13, 10), (24, 20), (36, 30), (12, 11), (40, 40)]
SHOWN = [(12, 10), (13, 10), (24, 20)]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]  # palette for color blindness


def main() -> None:
    base = field(*BASE)
    print(f"Coerenza con la matrice {BASE[0]}×{BASE[1]} (1 = suonano uguali)")
    print(f"{'confronto':>12} {'righe':>8} {'Hilbert':>8}")
    for shape in VARIANTS:
        other = field(*shape)
        rows, hilb = coherence(base, other, "rows"), coherence(base, other, "hilbert")
        print(f"{shape[0]:>6}×{shape[1]:<5} {rows:8.3f} {hilb:8.3f}")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True, layout="constrained")
    fig.patch.set_facecolor("#fcfcfb")
    t = (np.arange(4096) + 0.5) / 4096
    for ax, route, title in zip(axes, ["rows", "hilbert"], ["Riga per riga", "Curva di Hilbert"], strict=True):
        ax.set_facecolor("#fcfcfb")
        for shape, color in zip(SHOWN, COLORS, strict=True):
            track = listening_track(field(*shape), route)
            ax.plot(t, track, color=color, lw=2 if shape == BASE else 1.4, label=f"{shape[0]}×{shape[1]}")
        worst = min(coherence(base, field(*s), route) for s in SHOWN[1:])
        ax.set_title(f"{title}: coerenza minima {worst:.2f}".replace(".", ","), loc="left", fontsize=11,
                     color="#0b0b0b")
        ax.set_xlabel("tempo (frazione della durata totale)", color="#52514e")
        ax.grid(axis="y", color="#e6e5e0", lw=0.8)
        ax.tick_params(colors="#52514e", labelsize=8)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#c3c2b7")
        ax.set_xlim(0, 1)
    axes[0].set_ylabel("valore ascoltato (0–1)", color="#52514e")
    for ax in axes:
        ax.legend(title="risoluzione", frameon=False, fontsize=8, title_fontsize=8, loc="lower left")
    fig.suptitle("Lo stesso campo a tre risoluzioni: quello che si sente nel tempo", x=0.01, ha="left",
                 fontsize=12, color="#0b0b0b")

    out = Path(__file__).resolve().parent.parent / "docs" / "coerenza.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=150, facecolor=fig.get_facecolor())
    print(f"\nGrafico salvato in {out}")


if __name__ == "__main__":
    main()
