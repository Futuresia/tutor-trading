# Tutor de trading de Futuresia

Un profesor de trading dentro de Claude, en español. Te pregunta, te explica poco y bien, te pone ejercicios y te enseña con
simulaciones, a tu ritmo y desde cero, hasta que piensas como un trader algorítmico: con hipótesis, reglas y números, no con
corazonadas.

Lo hace [Futuresia](https://futuresia.com) y es gratuito. Es formación, no asesoramiento financiero: no da señales ni
recomendaciones de inversión. Operar con apalancamiento conlleva riesgo de pérdida.

## Qué aprendes

1. **Fundamentos:** mercados y contratos, futuros, ticks y valor del tick, sesiones, largo y corto, órdenes, apalancamiento y
   margen, vencimientos.
2. **Leer el mercado:** velas, temporalidades, volumen, tendencia y rango, VWAP, qué mide de verdad un indicador.
3. **La estadística del trading:** esperanza, acierto frente a ratio, coste, rachas, caída máxima, tamaño de posición y Kelly,
   riesgo de ruina, ventaja frente a suerte (los monos), t de Student, sobreajuste, Monte Carlo.
4. **Pensar como un trader algorítmico:** de la idea a la hipótesis, reglas sin ambigüedad, backtest honesto, dentro y fuera de
   muestra, walk-forward, incubación, cuándo dejar una estrategia.
5. **Estadística avanzada (módulo opcional):** colas gordas, intervalos y bootstrap, cuántas operaciones necesitas para fiarte de
   un sistema, métricas y sus trampas, Kelly con incertidumbre, probabilidad de pasar una cuenta de fondeo, cartera, test de
   rachas, Sharpe deflactado, Bayes, CUSUM y MAE/MFE.

Los conceptos se explican con futuros (MNQ, MES, oro) y valen igual para forex, acciones o cripto.

## Cómo se usa

Escribe en un chat nuevo: «Quiero empezar la academia de trading». Algunas frases útiles:

| Frase | Qué hace |
|---|---|
| «Lo dejo por hoy» | cierra la sesión y te da tu tarjeta de progreso |
| «Quiero seguir con la academia» (pegando tu tarjeta) | sigue donde lo dejaste |
| «Ábreme el simulador» | mil cuentas, riesgo de ruina y monos para tocar |
| «Explícamelo más fácil» | otra vez, más corto y con un ejemplo sencillo |
| «Analiza mis operaciones» (con un CSV) | ¿ventaja o suerte?, con tus propios datos |
| «Quiero la estadística avanzada» | el módulo avanzado |

Claude no recuerda un chat en otro: el tutor te da una **tarjeta de progreso** al terminar cada lección. Guárdala y pégala la
próxima vez.

## Qué ejecuta y qué datos usa

- **`skills/academia-trading-futuresia/scripts/sim.py`**: simulaciones en Python (numpy y matplotlib) que imprimen resultados y
  guardan gráficas PNG en la carpeta de trabajo (`academia_graficas/`). Todo es sintético o sale del CSV de operaciones que tú
  le des. No se conecta a internet ni descarga datos.
- **`skills/academia-trading-futuresia/assets/simulador.html`**: un simulador interactivo (HTML y JavaScript, sin librerías
  externas ni llamadas de red) que Claude abre como artefacto.
- No usa conectores, servidores MCP, hooks ni credenciales. Tus operaciones no salen de tu sesión de Claude.

En claude.ai necesita la ejecución de código activada (Configuración → Capacidades). En Claude Code, Python con numpy y
matplotlib.

## Licencia

[CC BY-NC 4.0](LICENSE): puedes usarlo, compartirlo y adaptarlo citando a Futuresia, pero no con fines comerciales.
