# Mercados y contratos

Datos de los contratos más usados en la academia. Fuente: especificaciones del CME Group (cmegroup.com). Las comisiones y los
márgenes cambian según el bróker y el momento: dilo así y que el alumno los compruebe en su bróker.

## Futuros de índices (CME)

| Contrato | Símbolo | Tick | Valor del tick | Valor por punto |
|---|---|---|---|---|
| Micro Nasdaq 100 | MNQ | 0,25 | 0,50 $ | 2 $ |
| E-mini Nasdaq 100 | NQ | 0,25 | 5,00 $ | 20 $ |
| Micro S&P 500 | MES | 0,25 | 1,25 $ | 5 $ |
| E-mini S&P 500 | ES | 0,25 | 12,50 $ | 50 $ |
| Micro Dow | MYM | 1 | 0,50 $ | 0,50 $ |
| Micro Russell 2000 | M2K | 0,10 | 0,50 $ | 5 $ |

Un micro es 1/10 del mini: el mismo gráfico, una décima parte del dinero por punto. Vencen en marzo (H), junio (M), septiembre
(U) y diciembre (Z).

## Materias primas (COMEX / NYMEX)

| Contrato | Símbolo | Tick | Valor del tick |
|---|---|---|---|
| Micro oro | MGC | 0,10 | 1,00 $ |
| Oro | GC | 0,10 | 10,00 $ |
| Micro crudo WTI | MCL | 0,01 | 1,00 $ |
| Crudo WTI | CL | 0,01 | 10,00 $ |

## Horario

Futuros del CME: de domingo 17:00 a viernes 16:00 (hora de Chicago), con pausa diaria de 16:00 a 17:00. Sesión regular de los
índices: 8:30–15:00 Chicago (15:30–22:00 en Madrid casi todo el año; en las semanas en que EE. UU. y Europa aún no han cambiado
ambos de horario, una hora antes). Chicago va una hora por detrás de Nueva York.

## Lo mismo en otros mercados

| Concepto | Futuros | Forex | Acciones | Cripto |
|---|---|---|---|---|
| Unidad mínima | tick | pip (0,0001 en la mayoría de pares) | céntimo | depende del exchange |
| Tamaño | contratos (micro, mini) | lotes (1 lote = 100.000 unidades; micro lote 1.000) | acciones | fracciones de moneda |
| Coste | comisión fija por contrato + deslizamiento | diferencial (spread) ± comisión | comisión + diferencial | comisión % + diferencial |
| Horario | casi 24 h, 5 días | 24 h, 5 días | sesión de la bolsa | 24/7 |
| Corto | igual que el largo | igual que el largo | requiere préstamo | según el producto |

La estadística (esperanza, rachas, tamaño, monos, sobreajuste) es idéntica en todos: lo que cambia es cuánto pesa el coste frente
al movimiento típico de cada operación.

## Cálculo de contratos por riesgo

contratos = riesgo en $ / (distancia del stop en ticks × valor del tick), redondeando hacia abajo. Si sale menos de 1, la
operación no cabe en ese riesgo con ese contrato: o un contrato más pequeño (micro) o no se opera.
