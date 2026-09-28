"""Estilo único para as figuras do projeto (PNG para documento e slides)."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from config import PASTA_FIGURAS  # noqa: E402

# Paleta categórica validada (ordem fixa, nunca reciclada).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
CORES_ANO = {2022: SERIES[0], 2023: SERIES[1], 2024: SERIES[2]}
# Rampa ordinal (azul) para categorias ordenadas, como as Pedras.
ORDINAL = ["#86b6ef", "#3987e5", "#256abf", "#104281"]
NEUTRO = "#898781"

TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
SUPERFICIE = "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE,
    "axes.facecolor": SUPERFICIE,
    "savefig.facecolor": SUPERFICIE,
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "text.color": TINTA,
    "axes.labelcolor": TINTA_SECUNDARIA,
    "axes.edgecolor": EIXO,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": GRADE,
    "grid.linewidth": 0.6,
    "axes.axisbelow": True,
    "xtick.color": TINTA_SECUNDARIA,
    "ytick.color": TINTA_SECUNDARIA,
    "xtick.major.size": 0,
    "ytick.major.size": 0,
    "legend.frameon": False,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "lines.linewidth": 2,
})


def nova_figura(largura=7.5, altura=4.0, **kwargs):
    return plt.subplots(figsize=(largura, altura), **kwargs)


def salvar(fig, nome):
    PASTA_FIGURAS.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_FIGURAS / f"{nome}.png"
    fig.tight_layout()
    fig.savefig(caminho, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return caminho


def fmt_br(valor, casas=1):
    """Número no padrão brasileiro (vírgula decimal)."""
    return f"{valor:.{casas}f}".replace(".", ",")
