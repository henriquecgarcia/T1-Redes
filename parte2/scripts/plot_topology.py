from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
fig, ax = plt.subplots(figsize=(13, 3.7))
ax.set_xlim(-1, 13)
ax.set_ylim(-1.1, 2.8)
ax.axis("off")
for x, width, label, color in [
	(-0.8, 4.0, "Acesso clientes: 10.10.0.0/24", "#E8F3FA"),
	(3.3, 5.5, "Nucleo: 10.20.0.0/24", "#FFF2D8"),
	(8.9, 3.9, "Acesso servidor: 10.30.0.0/24", "#E9F6ED"),
]:
	ax.add_patch(Rectangle((x, -0.65), width, 2.95, fc=color, ec="#bbb"))
	ax.text(x + width / 2, 2.05, label, ha="center", fontsize=10, weight="bold")
nodes = [
	(0, "8 clientes\n.10 a .17"),
	(2, "Switch\nacesso"),
	(4, "Roteador 1\n.1 / .1"),
	(6, "Switch\nnucleo"),
	(8, "Roteador 2\n.2 / .1"),
	(10, "Switch\nacesso"),
	(12, "Servidor\n.10:8080"),
]
for (x, _), (y, _) in zip(nodes, nodes[1:]):
	ax.plot([x, y], [0.8, 0.8], c="#555", lw=2)
for x, label in nodes:
	ax.add_patch(
		FancyBboxPatch(
			(x - 0.68, 0.3),
			1.36,
			1,
			boxstyle="round,pad=0.05",
			fc="white",
			ec="#24536E",
			lw=1.5,
			zorder=2,
		)
	)
	ax.text(x, 0.8, label, ha="center", va="center", fontsize=9)
for x, label in [(4.9, "saida eth1"), (7.1, "saida eth0")]:
	ax.annotate(
		"HTB + netem\n" + label,
		xy=(x, 0.75),
		xytext=(x, -0.35),
		ha="center",
		fontsize=9,
		arrowprops={"arrowstyle": "->", "color": "#b45f06"},
	)
ax.text(
	6,
	2.63,
	"Topologia CORE executada: 8 clientes, 2 roteadores, 1 servidor e 3 switches",
	ha="center",
	fontsize=12,
	weight="bold",
)
ax.text(
	6,
	-0.95,
	"A: 100 Mbps / 5 ms por sentido  |  B: 20 Mbps / 30 ms por sentido  |  Sem perda artificial",
	ha="center",
	fontsize=10,
)
fig.tight_layout()
for ext in ["png", "pdf"]:
	fig.savefig(ROOT / f"graficos/topologia.{ext}", dpi=180, bbox_inches="tight")
