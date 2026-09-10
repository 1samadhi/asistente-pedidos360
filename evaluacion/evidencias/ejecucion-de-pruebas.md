# Evidencia de las pruebas ejecutadas

**Generado:** 2026-09-09 22:31  
**Reproducir:** `python -m evaluacion.capturar_evidencia`

Salida literal de cada comprobacion, sin editar.

---

## Pruebas unitarias del guardrail

Verifica que el filtro de salida atrapa cada patron sensible, que no altera el texto legitimo, y que el corpus contiene efectivamente datos de ese tipo.

```
$ pytest evaluacion/ -v --no-header -q
============================= test session starts ==============================
collected 17 items

evaluacion/test_guardrails.py .................                          [100%]

============================== 17 passed in 0.04s ==============================
```

## Metricas de recuperacion sobre las 30 preguntas

Determinista y sin coste. Compara la busqueda solo-semantica con la hibrida sobre el mismo set.

```
$ evaluacion.evaluar
Set de evaluacion: 30 preguntas (23 sobre documentacion propia, 7 sobre fuentes externas)

RECUPERACION
  estrategia           recall  precision  sin fuente
  solo semantica         0.80       0.58           2
  hibrida ponderada      0.92       0.45           0
```

## Calibracion del juez

Comprueba que la rubrica discrimina antes de usarla para decidir nada: se le dan cuatro respuestas construidas a proposito y debe ordenarlas.

```
$ evaluacion.calibrar_juez
Calibracion del juez (openai/gpt-oss-20b)

  caso                    fidelidad  relevancia
  correcta                      1.0         1.0
  incompleta                    1.0        0.75
  con dato inventado           0.25         1.0
  falsa                         0.0         0.0

  La rubrica discrimina: sirve para comparar variantes.
```

## Estado de la API de Pedidos360

El asistente depende de un sistema externo. Se deja constancia de su estado en el momento de la ejecucion.

```
$ scripts/verificar_api.py
Verificacion de la API de Pedidos360
Base: https://j37oj1wn16.execute-api.us-east-1.amazonaws.com/desarrollo

Rutas publicas
  ok   /v1/public                             HTTP 200  0.67s
  ok   /.well-known/openid-configuration      HTTP 200  0.62s
  ok   /.well-known/jwks.json                 HTTP 200  0.73s

Rutas protegidas
  token de Entra obtenido (1640 caracteres)
  ok   /v1/productos                          HTTP 200  1.04s
  ok   /v1/pedidos                            HTTP 200  0.80s

Todo responde. Nada que reportar.
```

## Los tres tipos de consulta

El enrutamiento entre documentacion y datos en vivo no esta cableado con reglas: lo decide el modelo. Estas tres consultas lo ejercitan.

### Documental

> Tengo un token valido de ms-auth con los scopes correctos pero /v1/pedidos me devuelve 401. Por que?

```
El 401 se produce porque el endpoint **/v1/pedidos** está protegido por el autorizador de **Microsoft Entra ID** y solo acepta tokens emitidos por ese emisor.  
Aunque tu token de `ms‑auth` sea válido, tenga el `iss` correcto, la audiencia `exp1‑api` y los scopes necesarios, el API Gateway lo rechaza antes de llegar al microservicio, ya que cada ruta solo valida un único emisor.  

> “Un token emitido por `ms‑auth` es rechazado en el borde antes de llegar al microservicio… Cada ruta del API Gateway está asociada a **un solo autorizador**, y las rutas de negocio están asociadas al autorizador de **Microsoft Entra ID**” [1]  

Por eso recibes `401 Unauthorized`. Necesitas obtener un token de Microsoft Entra ID (o configurar un autorizador que acepte tu emisor) para poder acceder a `/v1/pedidos`.
```

### Datos en vivo

> Cuantos pedidos lleva mi comercio y cual es el producto que mas factura?

```
Tu comercio tiene **56 pedidos** en total, con una facturación acumulada de **$6.156.710**.  

El producto que más factura es **Monitor 27 pulgadas**, con **$1.709.910** facturados (9 unidades en 6 pedidos).
```

### Mixta

> Como obtengo el listado de mis pedidos por API y cuantos llevo ahora?

```
**Listado de pedidos por API**  
El endpoint para obtener el listado de pedidos es `GET /v1/pedidos`.  

**Cantidad actual de pedidos**  
Según la consulta en vivo, tienes **56 pedidos** facturados por un total de **$6.156.710**.  

Referencias: [1] para el endpoint y datos obtenidos de la consulta en tiempo real.
```

