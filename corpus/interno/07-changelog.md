# Registro de cambios

El versionado sigue [SemVer](https://semver.org/lang/es/): MAYOR.MENOR.PARCHE.

## [3.1.0]

- Despliegue en **EC2 t3.small** con Docker Compose, operado por **SSM** sin SSH.
- **AWS API Gateway** (HTTP API) como unico punto de entrada publico, con doce
  rutas y una integracion por ruta.
- **Autorizador JWT** en el borde, con el issuer del Identity Provider propio.
  Las rutas de discovery quedan publicas para que AWS pueda descargar el JWKS.
- Segundo autorizador preconfigurado para Cognito, listo para asociar a rutas.
- `scripts/actualizar-api-gateway.sh`: re-apunta las integraciones cuando la EC2
  cambia de IP publica al reiniciarse el laboratorio.
- `scripts/desplegar-en-ec2.sh`: despliegue remoto por SSM.
- `docs/03-api-gateway.md` y `docs/04-despliegue-ec2.md`.

## [3.0.0]

Cambio mayor: la solucion deja de ser solo backend y suma frontend.

- Frontend **React + Vite** con **MSAL** (`@azure/msal-browser`, `@azure/msal-react`).
- Login dual: boton de Microsoft (Entra ID) y formulario contra el IdP propio,
  para evidenciar en pantalla que el mismo Resource Server acepta ambos emisores.
- Panel que muestra el token vigente, su emisor y sus claims decodificados.
- Panel para consumir la API protegida y ver los codigos de respuesta.
- Ningun identificador de Azure queda hardcodeado: todo sale de variables `VITE_*`.
  La app arranca y avisa si Entra ID no esta configurado, en vez de romperse.
- `Dockerfile` multistage con nginx y `base: './'` en Vite, necesario para servir
  la app detras del stage del API Gateway sin romper las rutas de los assets.
- `docker-compose.yml` levanta el stack completo, con volumen para la llave del IdP.

## [2.4.0]

- CORS configurable en ambos Resource Server (`seguridad.origenes-cors`). Sin
  esto el navegador aborta la peticion en el preflight `OPTIONS` y el frontend
  nunca alcanza a enviar el header `Authorization`.
- Se permiten solo los metodos y cabeceras que la aplicacion usa, y se limita a
  los origenes configurados: un origen desconocido recibe 403 en el preflight.

## [2.3.0]

- Se incorpora **Microsoft Entra ID** como tercer emisor confiable. El
  convertidor ya contemplaba su claim `scp` y sus `roles`.
- Validacion de **audiencia** configurable via `seguridad.audiencias`. Queda
  desactivada por defecto porque los tokens `client_credentials` de Cognito no
  llevan claim `aud` y exigirla romperia el flujo maquina a maquina.
- Los decodificadores se construyen con `NimbusJwtDecoder.withIssuerLocation`
  para poder encadenar validadores propios sobre los de firma, expiracion y emisor.
- `docs/02-entra-id.md` con la configuracion del portal y la tabla de diferencias
  entre los tres emisores.

## [2.2.0]

- Se incorpora **Amazon Cognito** como segundo emisor confiable (Identity as a
  Service), con User Pool, resource server `exp1-api` y cliente maquina a maquina
  con flujo `client_credentials`.
- El convertidor de autoridades recorta el prefijo que Cognito antepone a los
  scopes (`exp1-api/pedidos.escribir` pasa a `SCOPE_pedidos.escribir`), sin lo
  cual el token seria valido pero `@PreAuthorize` devolveria 403.
- `docs/01-cognito.md` con el paso a paso y los identificadores del pool.
- `.env.example` con las variables necesarias.
- Los microservicios no cambiaron para aceptar Cognito: solo su configuracion.

## [2.1.0]

- `ms-productos` y `ms-pedidos` pasan a ser **Resource Server OAuth 2.0**: ya no
  gestionan contrasenias, solo verifican la firma del JWT contra las llaves
  publicas del emisor.
- Resolucion **multi emisor** (`JwtIssuerAuthenticationManagerResolver`): la lista
  de emisores confiables es configuracion (`SEGURIDAD_EMISORES`), no codigo.
- Los scopes y roles de cualquier emisor se normalizan a `SCOPE_x` y `ROLE_x`.
- Autorizacion por scope con `@PreAuthorize` en `POST /api/v1/pedidos`.
- `GET /api/v1/public` queda abierto en ambos servicios para comprobar despliegues.
- `ms-pedidos` valida el producto contra `ms-productos` **propagando el token**
  del usuario en lugar de usar una credencial de servicio.
- Los pedidos se asocian al `sub` del token, no a un campo enviado por el cliente.

## [2.0.0]

Cambio mayor: `ms-auth` deja de ser un servicio de estado y pasa a ser un
Identity Provider OIDC completo.

- Firma de tokens en **RS256** con par de llaves RSA de 2048 bits. Se abandona
  HS256 porque el autorizador JWT de AWS API Gateway valida la firma con llaves
  publicas descargadas del JWKS, y un secreto simetrico no le sirve.
- `POST /auth/login` emite `access_token` e `id_token` con claims OIDC.
- `GET /.well-known/openid-configuration` y `GET /.well-known/jwks.json`
  publican los metadatos y las llaves publicas del emisor.
- `GET /auth/userinfo` protegido con el propio token.
- Contrasenias codificadas con BCrypt.
- La llave RSA se persiste en un volumen para que sobreviva a los reinicios.

## [1.1.1]

- Correccion: `GET /api/v1/productos/{id}` respondia 500 ante un id inexistente porque
  `orElseThrow()` propagaba `NoSuchElementException`. Ahora responde 404.
- Pruebas de `ProductoV1Controller` cubriendo los casos 200 y 404.

## [1.1.0]

- `ms-productos`: nuevo endpoint `GET /api/v1/productos/{id}` para consultar un producto puntual.
- `ms-pedidos`: nuevo endpoint `POST /api/v1/pedidos` para registrar un pedido.

## [1.0.0]

- Creacion de los tres microservicios base: `ms-auth`, `ms-productos` y `ms-pedidos`.
- Cada servicio expone un endpoint GET que responde en formato JSON.
- Contenerizacion con Dockerfile multistage (build con Maven, runtime con JRE 21 y usuario no root).
- Orquestacion local con Docker Compose.
