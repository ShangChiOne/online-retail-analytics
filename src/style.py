"""One chart style for every figure: thin marks, recessive grid, fixed categorical order."""
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e6e5e0"
MUTED = "#b9b8b1"

# Categorical slots in fixed order (blue, orange, aqua) - validated CVD-safe as a set.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SEQ_BLUES = LinearSegmentedColormap.from_list(
    "seq_blue", ["#f3f8fe", "#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]
)


def apply() -> None:
    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans",
        "font.size": 10.5,
        "text.color": TEXT,
        "axes.labelcolor": TEXT_2,
        "axes.edgecolor": GRID,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.7,
        "xtick.color": TEXT_2,
        "ytick.color": TEXT_2,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 26,
        "legend.frameon": False,
        "lines.linewidth": 2,
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
    })


def subtitle(ax, text: str) -> None:
    """Grey one-line takeaway under the bold title."""
    ax.text(0, 1.02, text, transform=ax.transAxes, color=TEXT_2, fontsize=10, va="bottom")


def gbp(x, _pos=None) -> str:
    if abs(x) >= 1e6:
        return f"£{x / 1e6:.1f}M"
    if abs(x) >= 1e3:
        return f"£{x / 1e3:.0f}k"
    return f"£{x:.0f}"


def save(fig, path) -> None:
    fig.savefig(path)
    plt.close(fig)
    print(f"  figure -> {path.name}")
