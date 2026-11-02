"""Simulaciones del tutor de trading de Futuresia.

Cada orden imprime un resumen en texto y guarda una gráfica PNG en ./academia_graficas/ (o en --salida).
Todo es sintético: no hace falta ningún dato de mercado.

    python sim.py esperanza   --acierto 0.40 --ratio 2 --coste 0.05
    python sim.py ley         --acierto 0.55 --ops 1000
    python sim.py rachas      --acierto 0.55 --ops 250
    python sim.py cuentas     --acierto 0.40 --ratio 1.7 --riesgo 0.02 --ops 300
    python sim.py ruina       --acierto 0.40 --ratio 1.7 --ops 300
    python sim.py tamano      --acierto 0.40 --ratio 1.7 --ops 300
    python sim.py monos       --acierto 0.52 --ratio 1.1 --ops 200
    python sim.py sobreajuste --variantes 200
    python sim.py montecarlo  --archivo mis_operaciones.csv      (una columna con el resultado de cada operación)
    python sim.py tstat       --archivo mis_operaciones.csv  [--variantes 50]
    python sim.py vela        [--apertura 100 --maximo 108 --minimo 97 --cierre 99]

Tramo 5 (matemáticas del trading; casi todas aceptan --archivo con las operaciones del alumno en vez del sistema sintético):

    python sim.py colas        [--archivo ops.csv]               distribución real frente a la campana
    python sim.py bootstrap    [--archivo ops.csv]               intervalo de confianza de la esperanza
    python sim.py metricas     [--archivo ops.csv]               Sharpe, Sortino, PF, SQN... y cuánto bailan
    python sim.py muestra      --acierto 0.40 --ratio 1.7        cuántas operaciones hacen falta para demostrar la ventaja
    python sim.py kelly        --acierto 0.40 --ratio 1.7 --muestra 100     Kelly cuando no conoces tu acierto real
    python sim.py fondeo       --objetivo 3000 --dd 2500 --riesgo-usd 250 [--trailing] [--archivo ops_en_dolares.csv]
    python sim.py cartera      --correlacion 0.3                 dos estrategias juntas: cuánto baja la caída
    python sim.py aleatoriedad [--archivo ops.csv]               test de rachas y autocorrelación
    python sim.py bayes        --previa 0.6 --acierto 0.45 --ops 20 --ganadas 5
    python sim.py cusum        --acierto 0.45 --ratio 1.5 --cambio 300      detectar que la ventaja se ha ido
    python sim.py mae          [--archivo trades_ninjatrader.csv]   dónde poner el stop según MAE/MFE

Las cantidades se expresan en «R»: 1 R = lo que pierdes cuando salta el stop. Ganar 2 R = ganar el doble de lo que arriesgas.
"""
import argparse
import math
import os
import sys

import numpy as np

AQUA, TEAL, ACERO, CAL, CASCO, CORAL = "#35E3C4", "#0FA896", "#6E8794", "#F0F4F4", "#0F1518", "#F07C6C"
RNG = np.random.default_rng()


# ── utilidades ──────────────────────────────────────────────────────────────────────────────────────────────────────────

def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import logging
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    hay = {f.name for f in font_manager.fontManager.ttflist}
    fuente = next((f for f in ("Inter", "Segoe UI", "Helvetica", "Arial") if f in hay), "DejaVu Sans")
    plt.rcParams.update({
        "figure.facecolor": CASCO, "axes.facecolor": CASCO, "savefig.facecolor": CASCO,
        "axes.edgecolor": "#2C383F", "axes.labelcolor": CAL, "text.color": CAL,
        "xtick.color": ACERO, "ytick.color": ACERO, "grid.color": "#1E2A30", "axes.grid": True,
        "font.family": fuente, "font.size": 11,
        "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 14,
    })
    return plt


def _logo(fig):
    """Lockup oscuro de Futuresia abajo a la derecha (assets/futuresia-logo.png); si falta, el nombre en texto."""
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "futuresia-logo.png")
    try:
        import matplotlib.image as mpimg
        img = mpimg.imread(ruta)
    except Exception:
        fig.text(0.99, 0.01, "FUTURESIA", ha="right", va="bottom", fontsize=8, color=ACERO)
        return
    alto_in = 0.13
    ancho, alto = alto_in * img.shape[1] / img.shape[0] / fig.get_figwidth(), alto_in / fig.get_figheight()
    ax = fig.add_axes([0.99 - ancho, 0.012, ancho, alto])
    ax.imshow(img, alpha=0.85)
    ax.axis("off")


def marca(fig):
    """Para dibujos hechos a mano (una vela, un stop, una tendencia): pon el logo real de Futuresia en la figura.
    Uso:  import sys; sys.path.insert(0, "<carpeta del skill>/scripts"); from sim import estilo, marca
          plt = estilo(); fig, ax = plt.subplots(...); ...; fig.tight_layout(); marca(fig); fig.savefig(...)"""
    _logo(fig)


def estilo():
    """matplotlib con la paleta y la tipografía de Futuresia (devuelve pyplot)."""
    return _plt()


def _guardar(plt, fig, nombre, args):
    carpeta = args.salida or "academia_graficas"
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f"{nombre}.png")
    fig.tight_layout()
    _logo(fig)
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    print(f"\nGráfica: {os.path.abspath(ruta)}")


def _operaciones(acierto, ratio, n, coste=0.0, size=None):
    """Matriz de resultados en R: +ratio con probabilidad acierto, −1 si no; menos el coste (en R) de cada operación."""
    shape = (size, n) if size else n
    gana = RNG.random(shape) < acierto
    return np.where(gana, ratio, -1.0) - coste


def _caida_max(curva):
    curva = np.asarray(curva, float)
    pico = np.maximum.accumulate(np.concatenate([[0.0], curva]))
    return float((pico - np.concatenate([[0.0], curva])).max())


def _racha_max(perdidas):
    mejor = actual = 0
    for p in perdidas:
        actual = actual + 1 if p else 0
        mejor = max(mejor, actual)
    return mejor


def _leer(archivo):
    import csv
    vals = []
    with open(archivo, encoding="utf-8-sig") as f:
        for fila in csv.reader(f):
            for celda in fila:
                celda = celda.strip().replace("$", "").replace(" ", "")
                if celda.count(",") == 1 and "." not in celda:
                    celda = celda.replace(",", ".")
                try:
                    vals.append(float(celda)); break
                except ValueError:
                    continue
    if len(vals) < 10:
        sys.exit("Hacen falta al menos 10 operaciones con un número por fila.")
    return np.array(vals)


def _t(x):
    x = np.asarray(x, float)
    s = x.std(ddof=1)
    return float(x.mean() / s * math.sqrt(len(x))) if s > 0 else 0.0


def _p_una_cola(t):
    return 0.5 * math.erfc(t / math.sqrt(2))


def _z(p):
    """Cuantil de la normal estándar (inversa de Φ), sin scipy."""
    from statistics import NormalDist
    return NormalDist().inv_cdf(p)


def _realistas(acierto, ratio, n, coste=0.0, size=None):
    """Operaciones con forma real: las pérdidas son −1 R salvo algún hueco que salta el stop (3 %, de −1,5 a −3 R) y las
    ganancias tienen cola larga (Pareto) con media = ratio. Así las métricas y las colas se parecen a las de un trader."""
    shape = (size, n) if size else n
    gana = RNG.random(shape) < acierto
    ganancia = ratio * (RNG.pareto(2.5, shape) + 1) / (2.5 / 1.5)
    perdida = np.where(RNG.random(shape) < 0.03, -RNG.uniform(1.5, 3, shape), -1.0)
    return np.where(gana, ganancia, perdida) - coste


def _serie(a):
    """Las operaciones del alumno (--archivo) o, si no hay, un sistema sintético realista con --acierto/--ratio/--ops."""
    if a.archivo:
        return _leer(a.archivo), "tus operaciones"
    return _realistas(a.acierto, a.ratio, a.ops, a.coste), f"sistema sintético (acierto {a.acierto:.0%}, ratio {a.ratio}, {a.ops} ops)"


def _metricas(x):
    g, p = x[x > 0].sum(), -x[x < 0].sum()
    s, abajo = x.std(ddof=1), np.sqrt(np.mean(np.minimum(x, 0) ** 2))
    dd = _caida_max(np.cumsum(x))
    return {
        "esperanza": x.mean(),
        "Sharpe por operación": x.mean() / s if s else 0.0,
        "Sortino por operación": x.mean() / abajo if abajo else 0.0,
        "profit factor": g / p if p else float("inf"),
        "SQN": x.mean() / s * math.sqrt(min(len(x), 100)) if s else 0.0,
        "beneficio / caída máx.": x.sum() / dd if dd else float("inf"),
    }


# ── lecciones ───────────────────────────────────────────────────────────────────────────────────────────────────────────

def esperanza(a):
    e = a.acierto * a.ratio - (1 - a.acierto) - a.coste
    equilibrio = (1 + a.coste) / (1 + a.ratio)
    print(f"Acierto {a.acierto:.0%} · ratio {a.ratio} · coste {a.coste} R por operación")
    print(f"Esperanza por operación: {a.acierto:.2f}×{a.ratio} − {1 - a.acierto:.2f}×1 − {a.coste} = {e:+.3f} R")
    print(f"Acierto mínimo para no perder con ese ratio: {equilibrio:.1%}")
    print("En 100 operaciones arriesgando 100 $ cada una, lo esperado es " f"{e * 100 * 100:+,.0f} $ (la realidad oscila alrededor).")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    r = np.linspace(0.3, 4, 200)
    for c, col, txt in ((0, AQUA, "sin coste"), (a.coste, CORAL, f"con coste {a.coste} R")) if a.coste else ((0, AQUA, "sin coste"),):
        ax.plot(r, (1 + c) / (1 + r) * 100, color=col, lw=2.2, label=f"acierto mínimo ({txt})")
    ax.scatter([a.ratio], [a.acierto * 100], s=90, color=CAL, zorder=5, label="tu sistema")
    ax.fill_between(r, (1 + a.coste) / (1 + r) * 100, 100, color=TEAL, alpha=.08)
    ax.text(3.2, 80, "zona que gana", color=AQUA, fontsize=10)
    ax.text(3.2, 8, "zona que pierde", color=CORAL, fontsize=10)
    ax.set(xlabel="Ratio beneficio / riesgo (R)", ylabel="Acierto (%)", ylim=(0, 100), title="¿Gana tu sistema? Acierto frente a ratio")
    ax.legend(frameon=False, loc="upper center")
    _guardar(plt, fig, "esperanza", a)


def ley(a):
    x = (RNG.random((5, a.ops)) < a.acierto).astype(float)
    medias = x.cumsum(axis=1) / np.arange(1, a.ops + 1)
    print(f"Acierto real {a.acierto:.0%}. Cinco traders con EXACTAMENTE el mismo sistema, {a.ops} operaciones cada uno:")
    for n in (10, 30, 100, a.ops):
        if n <= a.ops:
            vals = ", ".join(f"{v:.0%}" for v in medias[:, n - 1])
            print(f"  tras {n:4d} operaciones su acierto observado: {vals}")
    print(f"Margen típico (±2 errores estándar) con 30 ops: ±{2 * math.sqrt(a.acierto * (1 - a.acierto) / 30):.0%}; "
          f"con {a.ops}: ±{2 * math.sqrt(a.acierto * (1 - a.acierto) / a.ops):.0%}")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    n = np.arange(1, a.ops + 1)
    banda = 2 * np.sqrt(a.acierto * (1 - a.acierto) / n)
    ax.fill_between(n, (a.acierto - banda) * 100, (a.acierto + banda) * 100, color=TEAL, alpha=.12, label="lo normal por azar (±2 σ)")
    for i in range(5):
        ax.plot(n, medias[i] * 100, lw=1.4, color=[AQUA, ACERO, CAL, TEAL, CORAL][i], alpha=.9)
    ax.axhline(a.acierto * 100, color=CAL, ls="--", lw=1)
    ax.set(xscale="log", ylim=(0, 100), xlabel="Número de operaciones (escala log)", ylabel="Acierto observado (%)",
           title="Con pocas operaciones, el acierto que ves miente")
    ax.legend(frameon=False)
    _guardar(plt, fig, "ley_grandes_numeros", a)


def rachas(a):
    sims = RNG.random((10000, a.ops)) >= a.acierto
    r = np.array([_racha_max(s) for s in sims])
    print(f"Acierto {a.acierto:.0%}, {a.ops} operaciones, 10.000 simulaciones:")
    print(f"  racha perdedora más larga · mediana {np.median(r):.0f} · el 10 % de las veces ≥ {np.percentile(r, 90):.0f} · "
          f"peor caso visto {r.max()}")
    print(f"  Probabilidad de ver al menos 5 pérdidas seguidas: {(r >= 5).mean():.0%}; al menos 8: {(r >= 8).mean():.0%}")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    bins = np.arange(r.min(), r.max() + 2) - 0.5
    ax.hist(r, bins=bins, color=AQUA, alpha=.85, rwidth=.85)
    ax.axvline(np.percentile(r, 90), color=CORAL, ls="--", lw=1.5, label="1 de cada 10 cuentas ve esto o más")
    ax.set(xlabel="Racha perdedora más larga", ylabel="Cuentas (de 10.000)",
           title=f"Rachas normales con un {a.acierto:.0%} de acierto en {a.ops} operaciones")
    ax.legend(frameon=False)
    _guardar(plt, fig, "rachas", a)


def cuentas(a):
    R = _operaciones(a.acierto, a.ratio, a.ops, a.coste, size=1000)
    cap = np.empty_like(R)
    saldo = np.full(1000, float(a.capital))
    for i in range(a.ops):
        saldo = np.maximum(saldo + saldo * a.riesgo * R[:, i], 0)
        cap[:, i] = saldo
    final = cap[:, -1]
    dd = np.array([(np.maximum.accumulate(c) - c).max() / np.maximum.accumulate(c).max() for c in cap])
    print(f"1.000 cuentas de {a.capital:,.0f} $ · acierto {a.acierto:.0%} · ratio {a.ratio} · riesgo {a.riesgo:.1%} del saldo por operación · "
          f"{a.ops} operaciones")
    print(f"  saldo final · mediana {np.median(final):,.0f} $ · peor 10 % ≤ {np.percentile(final, 10):,.0f} $ · mejor 10 % ≥ "
          f"{np.percentile(final, 90):,.0f} $")
    print(f"  cuentas que acaban perdiendo dinero: {(final < a.capital).mean():.0%} · caída máxima mediana {np.median(dd):.0%} "
          f"(1 de cada 10 sufre ≥ {np.percentile(dd, 90):.0%})")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for c in cap[:120]:
        ax.plot(c, color=ACERO, alpha=.18, lw=.8)
    for q, col in ((10, CORAL), (50, AQUA), (90, CAL)):
        ax.plot(np.percentile(cap, q, axis=0), color=col, lw=2, label=f"percentil {q}")
    ax.axhline(a.capital, color=ACERO, ls="--", lw=1)
    # Unas pocas cuentas disparadas aplastan la escala: se corta en el percentil 95 y se dice cuántas quedan fuera
    tope = max(np.percentile(cap, 95, axis=0).max(), a.capital) * 1.1
    ax.set_ylim(0, tope)
    fuera = int((cap.max(axis=1) > tope).sum())
    if fuera:
        ax.text(.99, .97, f"{fuera} cuentas se salen por arriba (la mayor llega a {cap.max():,.0f} $)".replace(",", "."),
                transform=ax.transAxes, ha="right", va="top", color=ACERO, fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))
    ax.set(xlabel="Operación", ylabel="Saldo ($)", title="El mismo sistema, mil destinos distintos")
    ax.legend(frameon=False, loc="upper left")
    _guardar(plt, fig, "cuentas", a)


def ruina(a):
    riesgos = np.array([0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.2])
    R = _operaciones(a.acierto, a.ratio, a.ops, a.coste, size=4000)
    filas = []
    for f in riesgos:
        saldo = np.ones(4000); pico = np.ones(4000); quebrada = np.zeros(4000, bool)
        for i in range(a.ops):
            saldo = saldo * (1 + f * R[:, i])
            pico = np.maximum(pico, saldo)
            quebrada |= saldo <= 1 - a.limite
        filas.append((f, quebrada.mean(), np.median(saldo)))
    print(f"Acierto {a.acierto:.0%} · ratio {a.ratio} · {a.ops} operaciones · «ruina» = perder el {a.limite:.0%} de la cuenta")
    for f, q, m in filas:
        print(f"  riesgo {f:5.1%} por operación → ruina {q:5.1%} · la cuenta mediana acaba en ×{m:.2f}")
    plt = _plt()
    fig, ax1 = plt.subplots(figsize=(9, 5.2))
    ax1.plot(riesgos * 100, [q * 100 for _, q, _ in filas], color=CORAL, lw=2.2, marker="o", label="probabilidad de ruina")
    ax1.set(xlabel="Riesgo por operación (% del saldo)", ylabel="Ruina (%)", title="Mismo sistema, distinto tamaño")
    ax2 = ax1.twinx()
    ax2.plot(riesgos * 100, [m for _, _, m in filas], color=AQUA, lw=2.2, marker="o", label="crecimiento mediano (×)")
    ax2.set_ylabel("Cuenta mediana al final (×)", color=AQUA)
    ax2.grid(False)
    h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left")
    _guardar(plt, fig, "ruina", a)


def tamano(a):
    e = a.acierto * a.ratio - (1 - a.acierto) - a.coste
    kelly = max((a.acierto * a.ratio - (1 - a.acierto)) / a.ratio, 0)
    R = _operaciones(a.acierto, a.ratio, a.ops, a.coste, size=4000)
    planes = {"fijo (siempre 1 % del capital inicial)": None, "1 % del saldo": 0.01, "2 % del saldo": 0.02,
              f"medio Kelly ({kelly / 2:.1%})": kelly / 2, f"Kelly completo ({kelly:.1%})": kelly}
    print(f"Esperanza {e:+.3f} R · Kelly teórico {kelly:.1%} del saldo (casi nadie lo usa entero: las caídas son brutales)")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for (nombre, f), col in zip(planes.items(), [ACERO, TEAL, AQUA, CAL, CORAL]):
        if f is None:
            saldo = 1 + 0.01 * R.cumsum(axis=1)
        else:
            saldo = np.cumprod(1 + f * R, axis=1)
        dd = np.array([(np.maximum.accumulate(s) - s).max() / np.maximum.accumulate(s).max() for s in saldo[:1000]])
        print(f"  {nombre:38s} → cuenta mediana ×{np.median(saldo[:, -1]):.2f} · caída máxima mediana {np.median(dd):.0%} · "
              f"pierde dinero {(saldo[:, -1] < 1).mean():.0%}")
        ax.plot(np.median(saldo, axis=0), color=col, lw=2, label=nombre)
    ax.set(yscale="log", xlabel="Operación", ylabel="Cuenta mediana (× capital, log)", title="Cómo crece la misma ventaja según el tamaño")
    ax.legend(frameon=False, fontsize=9)
    _guardar(plt, fig, "tamano", a)


def monos(a):
    mio = _operaciones(a.acierto, a.ratio, a.ops, a.coste)
    # Un mono tiene el MISMO perfil de operación pero sin ventaja: acierto que deja la esperanza en −coste.
    p0 = 1 / (1 + a.ratio)
    monos_ = _operaciones(p0, a.ratio, a.ops, a.coste, size=10000).sum(axis=1)
    pct = (monos_ < mio.sum()).mean() * 100
    t = _t(mio)
    print(f"Tu sistema (simulado): {a.ops} ops · acierto {a.acierto:.0%} · ratio {a.ratio} → total {mio.sum():+.1f} R · t = {t:.2f}")
    print(f"10.000 monos (mismas operaciones, dirección al azar, sin ventaja): ganas al {pct:.1f} % de ellos")
    print(f"  el mejor 5 % de los monos hace ≥ {np.percentile(monos_, 95):+.1f} R; el mejor mono, {monos_.max():+.1f} R")
    print("  Regla práctica: por debajo del percentil 95 no puedes distinguir tu sistema de la suerte.")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    # Los totales van a saltos de (ratio + 1) R: barras alineadas con esos saltos para que no salgan huecos
    paso = (1 + a.ratio) * max(1, round((monos_.max() - monos_.min()) / (1 + a.ratio) / 60))
    ax.hist(monos_, bins=np.arange(monos_.min() - paso / 2, monos_.max() + paso, paso), color=ACERO, alpha=.7,
            label="10.000 monos")
    ax.axvline(np.percentile(monos_, 95), color=CAL, ls="--", lw=1.2, label="percentil 95 de los monos")
    ax.axvline(mio.sum(), color=AQUA, lw=2.5, label=f"tu sistema (gana al {pct:.0f} %)")
    ax.set(xlabel="Resultado total (R)", ylabel="Monos", title="¿Ventaja o suerte? Tu sistema contra los monos")
    ax.legend(frameon=False)
    _guardar(plt, fig, "monos", a)


def sobreajuste(a):
    n, mitad = 3000, 1500
    precio = 100 + np.cumsum(RNG.normal(0, 1, n))   # paseo aleatorio: NO hay ninguna ventaja que encontrar
    def media(x, k):
        c = np.cumsum(np.insert(x, 0, 0)); m = (c[k:] - c[:-k]) / k
        return np.concatenate([np.full(k - 1, np.nan), m])
    mejores = []
    for _ in range(a.variantes):
        r, l = sorted(RNG.choice(np.arange(3, 120), 2, replace=False))
        pos = np.sign(media(precio, r) - media(precio, l))
        pnl = np.nan_to_num(pos[:-1] * np.diff(precio))
        mejores.append((pnl[:mitad].sum(), pnl[mitad:].sum(), r, l, pnl))
    mejores.sort(key=lambda z: -z[0])
    dentro, fuera, r, l, pnl = mejores[0]
    print(f"Precio = paseo aleatorio (por construcción NO existe ventaja). Probadas {a.variantes} combinaciones de medias móviles.")
    print(f"  La mejor en la primera mitad (medias {r}/{l}): {dentro:+.0f} puntos. En la segunda mitad, la misma: {fuera:+.0f} puntos.")
    top = mejores[:10]
    print(f"  Las 10 mejores dentro de muestra ganaban de media {np.mean([z[0] for z in top]):+.0f}; fuera, "
          f"{np.mean([z[1] for z in top]):+.0f} — lo mismo que el resto de combinaciones ({np.mean([z[1] for z in mejores[10:]]):+.0f}).")
    print("  Fuera de muestra, ser «la mejor» no dice nada: el precio es azar y cualquier ganancia allí también lo es.")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for z in mejores[1:30]:
        ax.plot(np.cumsum(z[4]), color=ACERO, alpha=.15, lw=.8)
    ax.plot(np.cumsum(pnl), color=AQUA, lw=2.2, label=f"la «mejor» de {a.variantes}")
    ax.axvline(mitad, color=CAL, ls="--", lw=1.2)
    ax.text(mitad * .5, ax.get_ylim()[1] * .9, "optimizada aquí", ha="center", color=CAL)
    ax.text(mitad * 1.5, ax.get_ylim()[1] * .9, "el futuro", ha="center", color=CORAL)
    ax.set(xlabel="Barra", ylabel="Beneficio acumulado (puntos)", title="Sobreajuste: buscar mucho siempre encuentra algo")
    ax.legend(frameon=False, loc="lower left")
    _guardar(plt, fig, "sobreajuste", a)


def montecarlo(a):
    x = _leer(a.archivo)
    curvas = np.array([np.cumsum(RNG.permutation(x)) for _ in range(5000)])
    dds = np.array([_caida_max(c) for c in curvas])
    real = _caida_max(np.cumsum(x))
    print(f"{len(x)} operaciones · total {x.sum():,.2f} · caída máxima real {real:,.2f}")
    print(f"Barajando el orden 5.000 veces: caída máxima mediana {np.median(dds):,.2f} · 1 de cada 20 órdenes ≥ "
          f"{np.percentile(dds, 95):,.2f} · peor {dds.max():,.2f}")
    print("  Tu caída histórica es solo UNA de las posibles. Planifica el capital con el percentil 95, no con la real.")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for c in curvas[:150]:
        ax.plot(c, color=ACERO, alpha=.12, lw=.8)
    ax.plot(np.cumsum(x), color=AQUA, lw=2.2, label="el orden real")
    ax.set(xlabel="Operación", ylabel="Resultado acumulado", title="Mismas operaciones, otro orden: Monte Carlo")
    ax.legend(frameon=False)
    _guardar(plt, fig, "montecarlo", a)


def tstat(a):
    x = _leer(a.archivo)
    t = _t(x)
    p = _p_una_cola(t)
    n_ef = a.variantes
    p_aj = min(1.0, p * n_ef)
    print(f"{len(x)} operaciones · media {x.mean():,.2f} · desviación {x.std(ddof=1):,.2f} · acierto {(x > 0).mean():.0%}")
    print(f"t = media / (desviación / √n) = {t:.2f} → p ≈ {p:.4f} (probabilidad de ver algo así sin ventaja, una cola)")
    if n_ef > 1:
        g = 0.5772156649
        t_max = (1 - g) * _z(1 - 1 / n_ef) + g * _z(1 - 1 / (n_ef * math.e))
        print(f"Has probado {n_ef} variantes: corrección de Bonferroni p × N = {p_aj:.4f}")
        print(f"  Entre {n_ef} variantes SIN ventaja, la mejor sale de media con t ≈ {t_max:.2f} (máximo esperado de {n_ef} normales).")
        print(f"  Tu t {'supera' if t > t_max else 'NO supera'} ese listón: es la idea del Sharpe deflactado.")
    print("  Guía: t < 2 no se distingue del azar; t ≥ 2 empieza a ser interesante; con muchas variantes el listón sube.")


# ── tramo 5 · las matemáticas del trading ───────────────────────────────────────────────────────────────────────────────

def colas(a):
    x, origen = _serie(a)
    m, s = x.mean(), x.std(ddof=1)
    z = (x - m) / s
    asim, curt = float(np.mean(z ** 3)), float(np.mean(z ** 4) - 3)
    normal3 = math.erfc(3 / math.sqrt(2))
    print(f"{origen}: {len(x)} operaciones · media {m:+.3f} · desviación {s:.3f}")
    print(f"  asimetría {asim:+.2f} (0 en la campana; positiva = cola larga de ganancias)")
    print(f"  exceso de curtosis {curt:+.2f} (0 en la campana; > 0 = colas gordas, más extremos de lo «normal»)")
    print(f"  operaciones a más de 3 desviaciones: {(np.abs(z) > 3).mean():.2%} · la campana diría {normal3:.2%}")
    print(f"  la mejor operación es {x.max() / s:.1f} desviaciones; sin ella el total pasa de {x.sum():+.1f} a {x.sum() - x.max():+.1f}")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.hist(x, bins=60, density=True, color=AQUA, alpha=.75, label="operaciones")
    xs = np.linspace(x.min(), x.max(), 300)
    ax.plot(xs, np.exp(-((xs - m) / s) ** 2 / 2) / (s * math.sqrt(2 * math.pi)), color=CORAL, lw=2, label="campana con la misma media y σ")
    ax.set(xlabel="Resultado por operación", ylabel="Densidad", title="Tus resultados no son una campana")
    ax.legend(frameon=False)
    _guardar(plt, fig, "colas", a)


def bootstrap(a):
    x, origen = _serie(a)
    n = len(x)
    medias = x[RNG.integers(0, n, (10000, n))].mean(axis=1)
    lo, hi = np.percentile(medias, [2.5, 97.5])
    se = x.std(ddof=1) / math.sqrt(n)
    print(f"{origen}: {n} operaciones · esperanza observada {x.mean():+.3f}")
    print(f"  intervalo del 95 % por bootstrap (10.000 remuestreos): [{lo:+.3f}, {hi:+.3f}]")
    print(f"  intervalo con la fórmula (media ± 1,96·σ/√n): [{x.mean() - 1.96 * se:+.3f}, {x.mean() + 1.96 * se:+.3f}]")
    print(f"  remuestreos con esperanza ≤ 0: {(medias <= 0).mean():.1%}"
          + (" → el cero cabe en el intervalo: no puedes descartar que no haya ventaja." if lo <= 0 else " → el cero queda fuera."))
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.hist(medias, bins=70, color=ACERO, alpha=.75, label="esperanza en cada remuestreo")
    ax.axvspan(lo, hi, color=TEAL, alpha=.15, label="intervalo del 95 %")
    ax.axvline(0, color=CORAL, lw=1.5, ls="--", label="sin ventaja")
    ax.axvline(x.mean(), color=AQUA, lw=2.5, label="lo observado")
    ax.set(xlabel="Esperanza por operación", ylabel="Remuestreos", title="¿Entre qué valores está tu esperanza real?")
    ax.legend(frameon=False)
    _guardar(plt, fig, "bootstrap", a)


def metricas(a):
    x, origen = _serie(a)
    n = len(x)
    reales = _metricas(x)
    muestras = [_metricas(x[RNG.integers(0, n, n)]) for _ in range(2000)]
    print(f"{origen}: {n} operaciones. Cada métrica con su intervalo del 95 % por bootstrap (lo que podría haber salido):")
    for k, v in reales.items():
        vals = np.array([m[k] for m in muestras]); vals = vals[np.isfinite(vals)]
        lo, hi = np.percentile(vals, [2.5, 97.5])
        print(f"  {k:24s} {v:8.2f}   [{lo:6.2f} – {hi:6.2f}]")
    print("  SQN = media/σ·√min(n,100). Sharpe y Sortino por operación (anualizar exige saber cuántas operaciones hay al año).")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    pf = np.array([m["profit factor"] for m in muestras]); pf = pf[np.isfinite(pf)]
    ax.hist(pf, bins=60, color=AQUA, alpha=.8)
    ax.axvline(1, color=CORAL, ls="--", lw=1.5, label="profit factor 1 (no gana)")
    ax.axvline(reales["profit factor"], color=CAL, lw=2, label=f"el tuyo: {reales['profit factor']:.2f}")
    ax.set(xlabel="Profit factor", ylabel="Remuestreos", title="El profit factor que ves es uno de muchos posibles")
    ax.legend(frameon=False)
    _guardar(plt, fig, "metricas", a)


def muestra(a):
    e = a.acierto * a.ratio - (1 - a.acierto) - a.coste
    if e <= 0:
        sys.exit(f"Esperanza {e:+.3f} R: sin ventaja no hay nada que demostrar.")
    s = math.sqrt(a.acierto * (1 - a.acierto)) * (a.ratio + 1)
    print(f"Acierto {a.acierto:.0%} · ratio {a.ratio} → esperanza {e:+.3f} R · desviación por operación {s:.2f} R")
    print(f"  t esperada tras n operaciones = (E/σ)·√n = {e / s:.3f}·√n")
    for potencia in (0.5, 0.8, 0.9):
        n = ((_z(0.95) + _z(potencia)) * s / e) ** 2
        print(f"  para que el test (t > 1,645, una cola al 5 %) lo detecte el {potencia:.0%} de las veces: "
              f"{math.ceil(n):,} operaciones".replace(",", ".").replace("1.645.", "1,645,"))
    ns = np.unique(np.geomspace(20, max(200, 4 * ((_z(0.95) + _z(0.9)) * s / e) ** 2), 25).astype(int))
    pot = [np.mean([_t(r) > 1.645 for r in _operaciones(a.acierto, a.ratio, n, a.coste, size=1500)]) for n in ns]
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(ns, np.array(pot) * 100, color=AQUA, lw=2.2, marker="o", ms=4)
    ax.axhline(80, color=CAL, ls="--", lw=1, label="80 % (lo habitual en un estudio)")
    ax.set(xscale="log", ylim=(0, 100), xlabel="Operaciones (escala log)", ylabel="Veces que la ventaja se demuestra (%)",
           title=f"¿Cuántas operaciones para demostrar {e:+.2f} R?")
    ax.legend(frameon=False)
    _guardar(plt, fig, "muestra", a)


def kelly(a):
    k_real = max((a.acierto * a.ratio - (1 - a.acierto)) / a.ratio, 0)
    g = lambda f, p: p * math.log1p(f * a.ratio) + (1 - p) * math.log1p(-min(f, .999))
    p_est = RNG.binomial(a.muestra, a.acierto, 20000) / a.muestra
    k_est = np.clip((p_est * a.ratio - (1 - p_est)) / a.ratio, 0, .99)
    print(f"Acierto real {a.acierto:.0%} (el trader no lo sabe) · ratio {a.ratio} · Kelly real {k_real:.1%}")
    print(f"El trader estima su acierto con {a.muestra} operaciones y aplica la fórmula. 20.000 traders así:")
    print(f"  acierto estimado: del {np.percentile(p_est, 5):.0%} al {np.percentile(p_est, 95):.0%} (90 % de los casos)")
    for frac, nombre in ((1, "Kelly completo"), (.5, "medio Kelly"), (.25, "cuarto de Kelly")):
        f = k_est * frac
        crec = np.array([g(v, a.acierto) for v in f]) / g(k_real, a.acierto) if k_real else np.zeros_like(f)
        print(f"  {nombre:16s} → apuesta más del doble del Kelly real (crecimiento negativo): {(f > 2 * k_real).mean():5.1%} · "
              f"crecimiento mediano {np.median(crec):.0%} del óptimo")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fs = np.linspace(0, min(.99, max(3 * k_real + .02, np.percentile(k_est, 99))), 300)
    ax.plot(fs * 100, [g(f, a.acierto) * 100 for f in fs], color=AQUA, lw=2.2, label="crecimiento por operación (log)")
    ax.set_ylim(-3 * g(k_real, a.acierto) * 100, 1.6 * g(k_real, a.acierto) * 100)
    ax.axhline(0, color=ACERO, lw=1)
    ax.axvline(k_real * 100, color=CAL, ls="--", lw=1.2, label="Kelly real")
    ax.hist(k_est * 100, bins=50, weights=np.full(len(k_est), 1 / len(k_est)) * max(g(k_real, a.acierto) * 100, .01) * 6,
            color=CORAL, alpha=.35, label=f"Kelly que calculan con {a.muestra} operaciones")
    ax.set(xlabel="Riesgo por operación (% del saldo)", ylabel="Crecimiento esperado (% log por operación)",
           title="Kelly con un acierto que no conoces")
    ax.legend(frameon=False)
    _guardar(plt, fig, "kelly", a)


def fondeo(a):
    miles = lambda v: f"{v:,.0f}".replace(",", ".")
    if a.archivo:
        base, origen = _leer(a.archivo), "tus operaciones"
        if np.abs(base).max() < 20:                              # parece estar en R, no en $: se pasa a $ con --riesgo-usd
            base, origen = base * a.riesgo_usd, f"tus operaciones (en R, pasadas a $ con {miles(a.riesgo_usd)} $ por R)"
        else:
            origen += " (en $; --riesgo-usd no se usa)"
    else:
        base, origen = _realistas(a.acierto, a.ratio, 5000, a.coste) * a.riesgo_usd,             f"sistema sintético (acierto {a.acierto:.0%}, ratio {a.ratio}, {miles(a.riesgo_usd)} $ de riesgo)"
    def sim(datos, factor, n=4000):
        ops = datos[RNG.integers(0, len(datos), (n, a.ops))] * factor
        saldo = np.cumsum(ops, axis=1)
        suelo = (np.maximum.accumulate(np.maximum(saldo, 0), axis=1) if a.trailing else 0) - a.dd
        llega = np.where((saldo >= a.objetivo).any(axis=1), (saldo >= a.objetivo).argmax(axis=1), a.ops + 1)
        quema = np.where((saldo <= suelo).any(axis=1), (saldo <= suelo).argmax(axis=1), a.ops + 1)
        return (llega < quema).mean(), (quema < llega).mean(), llega[llega < quema]
    mu, sd = base.mean(), base.std(ddof=1)
    print(f"Fondeo: objetivo +{miles(a.objetivo)} $ · pérdida máxima {miles(a.dd)} $ {'(trailing desde el máximo)' if a.trailing else '(fija)'} · "
          f"hasta {a.ops} operaciones · {origen}")
    print(f"  media {mu:+.1f} $ por operación · σ {sd:.0f} $" + (f" · t = {_t(base):.2f} con {len(base)} operaciones" if a.archivo else ""))
    factores = np.array([.25, .5, .75, 1, 1.25, 1.5, 2, 3])
    res = [sim(base, f) for f in factores]
    for f, (pp, qq, t) in zip(factores, res):
        print(f"  tamaño ×{f:<4} → pasa {pp:5.1%} · quema {qq:5.1%} · ni una cosa ni otra {max(0.0, 1 - pp - qq):5.1%}"
              + (f" · pasa en una mediana de {np.median(t):.0f} ops" if len(t) else "") + ("   ← el actual" if f == 1 else ""))
    p0, _, _ = sim(base - mu, 1.0)
    print(f"  Referencia SIN ventaja (las mismas operaciones centradas en 0): pasa {p0:.1%}"
          + ("" if a.trailing else f" (fórmula b/(a+b) = {a.dd / (a.objetivo + a.dd):.1%})"))
    if not a.trailing and mu != 0:
        th = 2 * mu / sd ** 2
        teo = (1 - math.exp(-th * a.dd)) / (1 - math.exp(-th * (a.objetivo + a.dd)))
        print(f"  Fórmula con ventaja (sin tope de operaciones): P = (1 − e^(−θb)) / (1 − e^(−θ(a+b))), θ = 2μ/σ² = {th:.2e} → {teo:.1%}")
    if a.archivo and _t(base) < 2:
        print("  Ojo: con t < 2 no está demostrado que esa media sea ventaja real; si no lo es, vale la referencia sin ventaja.")
    print("  Aproximación: el trailing se mide al cierre de cada operación (muchas firmas lo aplican también con la operación abierta,")
    print("  así que la realidad es algo peor) y no modela límites diarios ni el bloqueo del trailing. Un tamaño muy pequeño puede")
    print("  no llegar a ninguna barrera dentro del tope de operaciones (--ops).")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(factores, [r[0] * 100 for r in res], color=AQUA, lw=2.2, marker="o", label="pasa el reto")
    ax.plot(factores, [r[1] * 100 for r in res], color=CORAL, lw=2.2, marker="o", label="quema la cuenta")
    ax.axhline(p0 * 100, color=ACERO, ls=":", lw=1.2, label="pasar sin ventaja")
    ax.axvline(1, color=ACERO, ls="--", lw=1)
    ax.set(xlabel="Tamaño (× el actual)", ylabel="Probabilidad (%)", ylim=(0, 100), title="Probabilidad de pasar el fondeo según el tamaño")
    ax.legend(frameon=False)
    _guardar(plt, fig, "fondeo", a)


def cartera(a):
    rhos = np.array([-.3, 0, .2, .4, .6, .8, 1])
    def dos(rho, n=2000):
        z1 = RNG.standard_normal((n, a.ops)); z2 = rho * z1 + math.sqrt(1 - rho ** 2) * RNG.standard_normal((n, a.ops))
        corte = _z(a.acierto)                                # gana cuando su normal queda por debajo del cuantil del acierto
        r1 = np.where(z1 < corte, a.ratio, -1.0) - a.coste
        r2 = np.where(z2 < corte, a.ratio, -1.0) - a.coste
        return r1, (r1 + r2) / 2
    sola, _ = dos(0, 1000)
    dd_sola = np.median([_caida_max(np.cumsum(r)) for r in sola])
    print(f"Dos estrategias iguales (acierto {a.acierto:.0%}, ratio {a.ratio}), cada una a medio tamaño, {a.ops} operaciones:")
    print(f"  una sola a tamaño completo: caída máxima mediana {dd_sola:.1f} R")
    filas = []
    for rho in rhos:
        _, junta = dos(rho, 1000)
        dd = np.median([_caida_max(np.cumsum(r)) for r in junta])
        filas.append(dd)
        print(f"  correlación {rho:+.1f} → caída mediana {dd:5.1f} R ({dd / dd_sola - 1:+.0%}) · la esperanza no cambia")
    print(f"  Con tu correlación {a.correlacion:+.1f} la teoría da σ de la cartera = σ·√((1+ρ)/2) = {math.sqrt((1 + a.correlacion) / 2):.0%} de una sola.")
    print("  En las crisis las correlaciones suben: la diversificación desaparece justo cuando más falta hace.")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(rhos, filas, color=AQUA, lw=2.2, marker="o", label="cartera de dos")
    ax.axhline(dd_sola, color=CORAL, ls="--", lw=1.5, label="una sola estrategia")
    ax.set(xlabel="Correlación entre las dos", ylabel="Caída máxima mediana (R)", title="Diversificar solo sirve si no se mueven juntas")
    ax.legend(frameon=False)
    _guardar(plt, fig, "cartera", a)


def aleatoriedad(a):
    x, origen = _serie(a)
    w = (x > 0).astype(int)
    n1, n0 = w.sum(), len(w) - w.sum()
    rachas_ = 1 + int((w[1:] != w[:-1]).sum())
    mu = 2 * n1 * n0 / (n1 + n0) + 1
    var = (mu - 1) * (mu - 2) / (n1 + n0 - 1)
    z = (rachas_ - mu) / math.sqrt(var) if var > 0 else 0.0
    p = math.erfc(abs(z) / math.sqrt(2))
    ac = float(np.corrcoef(x[:-1], x[1:])[0, 1])
    tras_perdida = w[1:][w[:-1] == 0].mean()
    print(f"{origen}: {len(x)} operaciones · {n1} ganadoras · {n0} perdedoras")
    print(f"  rachas observadas {rachas_} · esperadas si es azar {mu:.1f} · z = {z:+.2f} · p (dos colas) = {p:.3f}")
    print(f"  {'Menos rachas de las esperadas: las ganancias y pérdidas se agrupan.' if z < -2 else 'Más rachas de las esperadas: tienden a alternarse.' if z > 2 else 'Compatible con azar: una operación no predice la siguiente.'}")
    print(f"  autocorrelación de un paso {ac:+.3f} (±{2 / math.sqrt(len(x)):.3f} es ruido) · "
          f"acierto tras una pérdida {tras_perdida:.0%} frente a {w.mean():.0%} en general")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    lags = np.arange(1, 21)
    acs = [np.corrcoef(x[:-k], x[k:])[0, 1] for k in lags]
    ax.bar(lags, acs, color=AQUA, alpha=.85)
    ax.axhspan(-2 / math.sqrt(len(x)), 2 / math.sqrt(len(x)), color=ACERO, alpha=.15, label="zona de ruido (±2/√n)")
    ax.set(xlabel="Separación entre operaciones", ylabel="Autocorrelación", title="¿Una operación dice algo de la siguiente?")
    ax.legend(frameon=False)
    _guardar(plt, fig, "aleatoriedad", a)


def bayes(a):
    p_si, p_no = a.acierto, 1 / (1 + a.ratio)
    k, n = a.ganadas, a.ops
    ver_si = p_si ** k * (1 - p_si) ** (n - k)
    ver_no = p_no ** k * (1 - p_no) ** (n - k)
    post = a.previa * ver_si / (a.previa * ver_si + (1 - a.previa) * ver_no)
    print(f"Hipótesis A: el sistema tiene ventaja (acierto {p_si:.0%}). Hipótesis B: ya no la tiene (acierto {p_no:.1%}, esperanza 0 con ratio {a.ratio}).")
    print(f"Confianza previa en A: {a.previa:.0%}. Observas {k} ganadoras de {n}.")
    print(f"  verosimilitud con A {ver_si:.3g} · con B {ver_no:.3g} · cociente {ver_si / ver_no:.2f}")
    print(f"  confianza en A después: {post:.0%}  (P(A|datos) = P(datos|A)·P(A) / P(datos))")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ks = np.arange(0, n + 1)
    vs, vn = p_si ** ks * (1 - p_si) ** (n - ks), p_no ** ks * (1 - p_no) ** (n - ks)
    ax.plot(ks, a.previa * vs / (a.previa * vs + (1 - a.previa) * vn) * 100, color=AQUA, lw=2.2, marker="o", ms=4)
    ax.axhline(a.previa * 100, color=ACERO, ls="--", lw=1, label="confianza previa")
    ax.scatter([k], [post * 100], s=110, color=CAL, zorder=5, label="lo que has visto")
    ax.set(xlabel=f"Ganadoras de {n}", ylabel="Confianza en que hay ventaja (%)", ylim=(0, 100), title="Bayes: cuánto cambia tu confianza")
    ax.legend(frameon=False)
    _guardar(plt, fig, "bayes", a)


def cusum(a):
    e = a.acierto * a.ratio - (1 - a.acierto) - a.coste
    if e <= 0:
        sys.exit("CUSUM vigila una ventaja que existe: usa un sistema con esperanza positiva.")
    k = e / 2                                                   # a medio camino entre «con ventaja» (e) y «sin ventaja» (0)
    def cusum_(r):
        c, hist = np.zeros(r.shape[0]), []
        for i in range(r.shape[1]):
            c = np.maximum(0, c + (k - r[:, i]))                 # acumula lo que cada operación se queda por debajo de lo esperado
            hist.append(c.copy())
        return np.array(hist).T
    sano = cusum_(_operaciones(a.acierto, a.ratio, a.ops, a.coste, size=2000))
    h = float(np.percentile(sano.max(axis=1), 100 * (1 - a.falsas)))   # umbral que da --falsas alarmas en sistemas sanos
    roto = np.concatenate([_operaciones(a.acierto, a.ratio, a.cambio, a.coste, size=2000),
                           _operaciones(1 / (1 + a.ratio), a.ratio, a.ops - a.cambio, a.coste, size=2000)], axis=1)
    hist = cusum_(roto)
    cruza = hist > h
    al_roto = np.where(cruza.any(axis=1), cruza.argmax(axis=1), -1)
    tras = al_roto[al_roto >= a.cambio] - a.cambio
    print(f"Sistema con esperanza {e:+.3f} R. CUSUM con referencia k = E/2 = {k:.3f} R")
    print(f"  umbral h = {h:.1f} R, elegido para que solo el {a.falsas:.0%} de los sistemas SANOS dé una falsa alarma en {a.ops} operaciones")
    print(f"  sistemas que pierden la ventaja en la operación {a.cambio}: detectados antes del final {(al_roto >= a.cambio).mean():.0%}"
          + (f" · tardan una mediana de {np.median(tras):.0f} operaciones" if len(tras) else ""))
    print(f"  Cuanto más pequeña la ventaja (aquí E/σ = {e / (math.sqrt(a.acierto * (1 - a.acierto)) * (a.ratio + 1)):.2f}), más tarda en notarse que se fue.")
    print("  Subir h = menos falsas alarmas pero detección más lenta. No hay umbral gratis.")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for c in hist[:40]:
        ax.plot(c, color=ACERO, alpha=.25, lw=.8)
    ax.plot(hist[0], color=AQUA, lw=2.2, label="un sistema")
    ax.axhline(h, color=CORAL, ls="--", lw=1.5, label="umbral de alarma")
    ax.axvline(a.cambio, color=CAL, ls=":", lw=1.5, label="aquí se va la ventaja")
    ax.set(xlabel="Operación", ylabel="CUSUM (R por debajo de lo esperado)", title="CUSUM: ¿racha normal o ventaja perdida?")
    ax.legend(frameon=False, loc="upper left")
    _guardar(plt, fig, "cusum", a)


def _leer_mae(archivo):
    """Exportación de operaciones de NinjaTrader (o cualquier CSV con columnas de resultado, MAE y MFE). Devuelve (res, mae, mfe)."""
    import csv
    with open(archivo, encoding="utf-8-sig") as f:
        sep = ";" if f.readline().count(";") > 1 else ","
        f.seek(0)
        filas = list(csv.reader(f, delimiter=sep))
    cab = [c.strip().lower() for c in filas[0]]
    def col(*nombres):
        for i, c in enumerate(cab):
            if any(c == n or c.startswith(n) for n in nombres):
                return i
        sys.exit(f"No encuentro la columna {nombres[0]} en el CSV (columnas: {', '.join(cab)}).")
    ir, im, iM = col("profit", "resultado", "pnl", "beneficio"), col("mae"), col("mfe")
    num = lambda s: float(s.replace("$", "").replace("(", "-").replace(")", "").replace(" ", "").replace(",", "")) if s.strip() else float("nan")
    datos = np.array([[num(r[ir]), abs(num(r[im])), abs(num(r[iM]))] for r in filas[1:] if len(r) > max(ir, im, iM)])
    datos = datos[~np.isnan(datos).any(axis=1)]
    return datos[:, 0], datos[:, 1], datos[:, 2]


def mae(a):
    if a.archivo:
        res, adv, fav = _leer_mae(a.archivo)
        unidad, origen = "$", "tuyas"
    else:
        # Operaciones como paseos aleatorios con un poco de deriva, stop a −1 R y objetivo a +ratio R
        n, pasos = 2000, 1500
        camino = np.cumsum(RNG.normal(a.deriva, 0.1, (n, pasos)), axis=1)
        sale = np.where(((camino <= -1) | (camino >= a.ratio)).any(axis=1), ((camino <= -1) | (camino >= a.ratio)).argmax(axis=1), pasos - 1)
        res = np.clip(camino[np.arange(n), sale], -1, a.ratio)
        adv = np.array([-min(0, camino[i, :sale[i] + 1].min()) for i in range(n)])
        fav = np.array([max(0, camino[i, :sale[i] + 1].max()) for i in range(n)])
        unidad, origen = "R", f"sintéticas (stop 1 R, objetivo {a.ratio} R)"
    gan = res > 0
    print(f"{len(res)} operaciones {origen} · {gan.mean():.0%} ganadoras")
    print(f"  MAE (lo máximo que fueron en contra) de las GANADORAS: mediana {np.median(adv[gan]):.2f} {unidad} · "
          f"el 90 % no pasó de {np.percentile(adv[gan], 90):.2f} {unidad}")
    print(f"  MAE de las PERDEDORAS: mediana {np.median(adv[~gan]):.2f} {unidad}")
    print(f"  MFE (lo máximo que fueron a favor) de las PERDEDORAS: mediana {np.median(fav[~gan]):.2f} {unidad} "
          f"(lo que llegaron a ganar antes de perder)")
    print("  Si casi ninguna ganadora va más en contra que X, un stop algo más allá de X corta perdedoras sin tocar ganadoras.")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    bins = np.linspace(0, np.percentile(adv, 99), 40)
    ax.hist(adv[gan], bins=bins, color=AQUA, alpha=.75, label="ganadoras")
    ax.hist(adv[~gan], bins=bins, color=CORAL, alpha=.6, label="perdedoras")
    ax.axvline(np.percentile(adv[gan], 90), color=CAL, ls="--", lw=1.2, label="90 % de las ganadoras va menos en contra")
    ax.set(xlabel=f"MAE: máximo en contra ({unidad})", ylabel="Operaciones", title="MAE: hasta dónde van en contra las que acaban ganando")
    ax.legend(frameon=False)
    _guardar(plt, fig, "mae", a)


# ── dibujos de conceptos ───────────────────────────────────────────────────────────────────────────────────────────────

def vela(a):
    """Una vela alcista y una bajista con sus cuatro precios (o la del alumno con --apertura --maximo --minimo --cierre)."""
    plt = _plt()
    propia = None not in (a.apertura, a.maximo, a.minimo, a.cierre)
    velas = [("Tu vela", a.apertura, a.maximo, a.minimo, a.cierre)] if propia else         [("Vela alcista (sube)", 100, 108, 97, 105), ("Vela bajista (baja)", 105, 108, 97, 100)]
    fig, axs = plt.subplots(1, len(velas), figsize=(4.6 * len(velas) + .4, 5.2), squeeze=False)
    for ax, (titulo, o, h, l, c) in zip(axs[0], velas):
        col = AQUA if c >= o else CORAL
        ax.plot([0, 0], [l, h], color=col, lw=2.5, solid_capstyle="butt")
        ax.add_patch(plt.Rectangle((-0.18, min(o, c)), 0.36, max(abs(c - o), (h - l) * .004), color=col))
        for y, txt in sorted({(h, "Máximo"), (l, "Mínimo"), (o, "Apertura"), (c, "Cierre")}, key=lambda z: -z[0]):
            ax.plot([0.2, 0.55], [y, y], color=ACERO, lw=.8)
            ax.text(0.6, y, f"{txt}: {y:g}", va="center", color=CAL, fontsize=11)
        ax.set_title(titulo, color=col, loc="left")
        ax.set(xlim=(-0.6, 1.6), ylim=(l - (h - l) * .08, h + (h - l) * .08))
        ax.axis("off")
    if propia:
        print(f"Apertura {a.apertura:g} · máximo {a.maximo:g} · mínimo {a.minimo:g} · cierre {a.cierre:g} → "
              f"{'alcista' if a.cierre >= a.apertura else 'bajista'} · cuerpo {abs(a.cierre - a.apertura):g} · "
              f"mecha superior {a.maximo - max(a.apertura, a.cierre):g} · mecha inferior {min(a.apertura, a.cierre) - a.minimo:g}")
    else:
        print("Cuerpo = de la apertura al cierre · mechas = hasta el máximo y el mínimo · color = si cerró por encima o por debajo")
    _guardar(plt, fig, "vela", a)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("leccion", choices=["esperanza", "ley", "rachas", "cuentas", "ruina", "tamano", "monos", "sobreajuste",
                                        "montecarlo", "tstat", "colas", "bootstrap", "metricas", "muestra", "kelly", "fondeo",
                                        "cartera", "aleatoriedad", "bayes", "cusum", "mae", "vela"])
    ap.add_argument("--acierto", type=float, default=0.45)
    ap.add_argument("--ratio", type=float, default=1.5)
    ap.add_argument("--coste", type=float, default=0.0, help="coste por operación en R (comisión + deslizamiento)")
    ap.add_argument("--ops", type=int, default=300)
    ap.add_argument("--riesgo", type=float, default=0.02)
    ap.add_argument("--capital", type=float, default=10000)
    ap.add_argument("--limite", type=float, default=0.5, help="pérdida que cuenta como ruina (0,5 = −50 %%)")
    ap.add_argument("--variantes", type=int, default=200)
    ap.add_argument("--archivo")
    ap.add_argument("--muestra", type=int, default=100, help="kelly: operaciones con las que el trader estima su acierto")
    ap.add_argument("--objetivo", type=float, default=3000, help="fondeo: beneficio para pasar ($)")
    ap.add_argument("--dd", type=float, default=2500, help="fondeo: pérdida máxima permitida ($)")
    ap.add_argument("--riesgo-usd", type=float, default=250, help="fondeo: $ que pierdes cuando salta el stop")
    ap.add_argument("--trailing", action="store_true", help="fondeo: la pérdida máxima se mide desde el máximo del saldo")
    ap.add_argument("--correlacion", type=float, default=0.3)
    ap.add_argument("--previa", type=float, default=0.6, help="bayes: confianza previa en que el sistema tiene ventaja")
    ap.add_argument("--ganadas", type=int, default=5, help="bayes: ganadoras observadas de --ops")
    ap.add_argument("--cambio", type=int, default=300, help="cusum: operación en la que desaparece la ventaja")
    ap.add_argument("--falsas", type=float, default=0.1, help="cusum: falsas alarmas aceptadas en sistemas sanos (0,1 = 10 %%)")
    ap.add_argument("--deriva", type=float, default=0.004, help="mae: ventaja por paso en las operaciones sintéticas")
    for k in ("apertura", "maximo", "minimo", "cierre"):
        ap.add_argument(f"--{k}", type=float, help="vela: precio de la vela del alumno")
    ap.add_argument("--semilla", type=int)
    ap.add_argument("--salida")
    a = ap.parse_args()
    if a.acierto > 1:
        a.acierto /= 100
    if a.semilla is not None:
        global RNG
        RNG = np.random.default_rng(a.semilla)
    if a.leccion in ("montecarlo", "tstat") and not a.archivo:
        sys.exit("Esta lección necesita --archivo con tus operaciones.")
    if a.leccion == "tstat" and a.variantes == 200:
        a.variantes = 1
    if a.leccion == "fondeo" and a.ops == 300:
        a.ops = 1000
    if a.leccion == "bayes" and a.ops == 300:
        a.ops = 20
    if a.leccion == "cusum" and a.ops <= a.cambio:
        a.ops = 3 * a.cambio
    globals()[a.leccion](a)


if __name__ == "__main__":
    main()
