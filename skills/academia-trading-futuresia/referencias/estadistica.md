# La estadística del trading · fondo para el tutor

Material de consulta para dar el tramo 3 con precisión. No lo recites: tradúcelo a ejemplos y deja que la simulación hable.

## Unidades: R
1 R = lo que se pierde si salta el stop. Expresar resultados en R permite comparar sistemas y mercados distintos. Un sistema
que gana 0,2 R por operación arriesgando 100 $ gana 20 $ de media; arriesgando 500 $, 100 $.

## Esperanza
E = p·G − (1 − p)·P − c, con p acierto, G ganancia media, P pérdida media y c coste. En R: E = p·ratio − (1 − p) − c.
Acierto mínimo para E = 0: p* = (1 + c) / (1 + ratio).
Errores típicos del alumno: creer que un acierto alto basta (sin mirar el ratio) y olvidar el coste. Un sistema con ratio muy
pequeño (objetivo cerca, stop lejos) necesita aciertos muy altos y una sola pérdida grande borra muchas ganancias.

## Varianza y error estándar
Desviación típica σ de los resultados por operación. Error estándar de la media = σ / √n. La media observada oscila ±2 errores
estándar alrededor de la real en ~95 % de los casos. Para un porcentaje (acierto): σ = √(p(1 − p)).
Consecuencia: para distinguir una ventaja pequeña (E pequeña frente a σ) hacen falta muchas operaciones. n necesario para t ≈ 2:
n ≈ (2σ / E)². Con E = 0,1 R y σ ≈ 1,2 R → n ≈ 576 operaciones.

## Rachas
La racha perdedora más larga en n operaciones con probabilidad de fallo q crece aproximadamente como log(n) / log(1/q). No
depende de que el sistema «se haya roto». Es lo que más hace abandonar sistemas buenos. Úsala para fijar expectativas antes de
operar: «con tu acierto, en un año verás probablemente X pérdidas seguidas».

## Caída máxima (drawdown)
Máxima distancia del pico al valle de la curva de capital. Depende del orden de las operaciones (Monte Carlo) y crece con el
tiempo que se opera: con más operaciones, más ocasiones de una mala racha. Recuperación asimétrica: perder un x % exige ganar
x / (1 − x) para volver (−20 % → +25 %; −50 % → +100 %).

## Tamaño de posición
- Fijo en contratos: simple, la curva crece en línea.
- Fracción fija del saldo (f): crecimiento compuesto; tras pérdidas reduce el tamaño solo.
- Kelly: f* = (p·ratio − (1 − p)) / ratio. Maximiza el crecimiento logarítmico esperado si p y ratio se conocen con exactitud,
  cosa que nunca pasa. Con estimaciones con error, Kelly completo sobreapuesta. Medio Kelly da ~75 % del crecimiento con mucha
  menos caída. Por encima de 2× Kelly, el crecimiento esperado es negativo aunque la esperanza por operación sea positiva.
- Riesgo de ruina: aumenta muy deprisa con f. Con cuentas de fondeo (límite de pérdida fijo), la «ruina» llega mucho antes.

## Ventaja frente a suerte: los monos
Un mono opera con las mismas reglas de tamaño, horario y salida, pero elige la dirección al azar. Repetido miles de veces da la
distribución de lo que se obtiene sin ventaja. Percentil de tu sistema ≥ 95 → difícil de explicar por suerte (con una sola
prueba). En `sim.py monos`, el mono tiene el mismo ratio y el acierto que deja la esperanza en −coste.
Variante con datos reales: invertir la dirección de cada operación al azar (el «espejo») o elegir días al azar.

## t de Student y valor p
t = media / (σ / √n). Con n grande, t ≈ normal: t = 2 → p ≈ 0,023 a una cola. El valor p es P(resultado tan bueno | sin
ventaja). NO es la probabilidad de que el sistema funcione ni la de que siga funcionando.
Errores típicos: confundir p con «probabilidad de acertar»; calcular t sobre muy pocas operaciones (< 30); ignorar que las
operaciones de un mismo día pueden no ser independientes (entonces se suma por día y se calcula t por días).

## Probar muchas cosas (comparaciones múltiples)
Con N variantes independientes y ninguna ventaja real, la probabilidad de que al menos una salga con p < 0,05 es 1 − 0,95^N
(N = 20 → 64 %). Correcciones: Bonferroni (p × N, conservadora) o control de la tasa de falsos descubrimientos
(Benjamini–Hochberg, menos estricta). Lo esencial para el alumno: **contar todo lo que ha probado**, incluidas las
optimizaciones de la plataforma (3 parámetros con 10 valores = 1.000 variantes).

## Sobreajuste
Ajustar reglas y parámetros al ruido del pasado. Señales: muchos parámetros, reglas con excepciones, curva perfecta, resultado que
depende de un valor exacto (pico en vez de meseta), caída fuerte fuera de muestra. Defensa: pocas reglas con una razón económica,
separación de datos, walk-forward, mesetas, N contada.

## Monte Carlo
Remuestrear las operaciones (barajar el orden o sacar con reemplazo) para obtener la distribución de caída máxima y de resultado.
Supone que las operaciones son intercambiables: si hay rachas reales por régimen de mercado, la caída real puede ser mayor que la
del Monte Carlo. Usa el percentil 95 para el capital y para fijar el punto de abandono.

## Dentro y fuera de muestra, walk-forward
- Dentro de muestra: donde se diseña. Todo lo que se mira ahí está «gastado».
- Fuera de muestra: datos que no se han usado para decidir nada. Solo valen una vez: si se retoca la regla tras verlos, pasan a
  ser de diseño.
- Walk-forward anclado o rodante: optimizar en [inicio, t], probar en (t, t + k], avanzar. La eficiencia (resultado fuera /
  resultado dentro, anualizados) mide cuánto se conserva.

## Frases útiles para el alumno
- «Una racha de pérdidas no te dice que el sistema esté roto; te lo dice que se salga de lo que esperabas antes de empezar.»
- «El backtest es la mejor versión de tu sistema. La realidad casi siempre es peor.»
- «Si probaste muchas cosas, la mejor siempre parece buena.»
- «El tamaño no convierte un sistema malo en bueno, pero sí puede convertir uno bueno en ruina.»
