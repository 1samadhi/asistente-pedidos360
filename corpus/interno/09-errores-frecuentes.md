# Errores frecuentes al integrarse con la API de Pedidos360

Guía de resolución de problemas para el desarrollador que está integrando su comercio.
Está escrita desde el síntoma —el código de error que recibe— y no desde el diseño del
sistema, porque es así como llega la consulta.

> **Origen de este documento.** Se redactó tras comprobar contra el despliegue real qué
> responde cada ruta con cada tipo de token. Cubre un vacío detectado en la documentación:
> el resto de los documentos describe cómo se construyó la plataforma, pero ninguno
> relaciona los errores HTTP con su causa.

---

## 401 Unauthorized en `/v1/pedidos` o `/v1/productos` con un token que parece válido

**Síntoma.** Obtienes un token de `POST /auth/login`, el token trae el `iss` correcto, la
audiencia `exp1-api` y los scopes `pedidos.leer pedidos.escribir`, y aun así la API
responde `{"message":"Unauthorized"}`.

**Causa.** Cada ruta del API Gateway está asociada a **un solo autorizador**, y las rutas
de negocio están asociadas al autorizador de **Microsoft Entra ID**, no al del IdP propio
de Pedidos360. Un token emitido por `ms-auth` es rechazado en el borde antes de llegar al
microservicio, sin importar que sea válido y esté correctamente firmado.

Es una consecuencia directa de una limitación de la plataforma: el autorizador JWT de una
HTTP API valida un único emisor. Exponer varios emisores exige un autorizador por emisor,
y cada ruta elige uno.

**Qué autorizador usa cada ruta:**

| Ruta | Autorizador | Emisor que acepta |
|---|---|---|
| `GET /v1/productos` | `entra-id` | Microsoft Entra ID |
| `GET /v1/productos/{id}` | `entra-id` | Microsoft Entra ID |
| `GET /v1/productos/quien-soy` | `entra-id` | Microsoft Entra ID |
| `GET /v1/pedidos` | `entra-id` | Microsoft Entra ID |
| `POST /v1/pedidos` | `entra-id` | Microsoft Entra ID |
| `GET /auth/userinfo` | `idp-propio` | `ms-auth` de Pedidos360 |
| `POST /auth/login` | — | público |
| `GET /v1/public` | — | público |
| `GET /.well-known/*` | — | público |

**Solución.** Para consumir las rutas de negocio, obtén el token de Entra ID:

```bash
curl -X POST "https://login.microsoftonline.com/$TENANT_ID/oauth2/v2.0/token" \
  -d "client_id=$CLIENT_ID" \
  -d "scope=$APP_ID_URI/.default" \
  -d "username=$USUARIO" \
  -d "password=$PASSWORD" \
  -d "grant_type=password"
```

El token de `ms-auth` sigue sirviendo para `/auth/userinfo` y para llamar directamente a
los microservicios sin pasar por el gateway: los Resource Server de Spring sí aceptan los
tres emisores.

---

## 401 al crear un pedido, aunque leer funcione

**Causa.** `POST /v1/pedidos` exige el scope `pedidos.escribir` o el rol `ADMIN`. Leer
solo requiere estar autenticado.

**Solución.** Revisa los scopes concedidos a tu aplicación en Entra ID. En el token
aparecen en el claim `scp`.

---

## 503 Service Unavailable en todas las rutas

**Causa.** El API Gateway está vivo pero la integración apunta a una dirección que ya no
responde. Ocurre cuando la instancia EC2 se reinicia y recibe una IP pública nueva: el
gateway conserva la anterior.

**Solución.** Ejecutar `scripts/actualizar-api-gateway.sh`, que lee la IP actual de la
instancia y actualiza todas las integraciones.

---

## 404 Not Found en `/api/v1/...`

**Causa.** Confundir la ruta del gateway con la del microservicio. Los microservicios
exponen `/api/v1/...`, pero el gateway publica esas mismas operaciones bajo `/v1/...` y
reescribe el prefijo al reenviar.

**Solución.** Desde Internet usa `/v1/pedidos`. `/api/v1/pedidos` no es una ruta del
gateway: cae en la ruta comodín del frontend.

---

## El token de Entra funciona en la API pero el `sub` no es el correo del usuario

**Causa.** El claim `sub` de Entra ID es un identificador opaco y específico de cada
aplicación, no el nombre de usuario. Pedidos360 asocia los pedidos a ese `sub`.

**Consecuencia.** Cada aplicación registrada ve un `sub` distinto para la misma persona.
Si cambias el registro de aplicación, los pedidos anteriores dejan de asociarse a ese
usuario. El correo está en el claim `preferred_username`.

---

## Los pedidos creados no aparecen al listarlos

**Causa.** `GET /v1/pedidos` filtra por el `sub` del token que presentas. Solo devuelve
los pedidos del comercio autenticado.

**Comprobación.** Si creaste el pedido con un token y lo consultas con otro, no lo verás.
No es un fallo: es el aislamiento por identidad.
