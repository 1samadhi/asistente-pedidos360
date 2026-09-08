# EXP1 — Arquitectura segura en la nube con OIDC y OAuth 2.0

Solucion de la Experiencia 1 de Cloud: tres microservicios Spring Boot desacoplados
de la logica de autenticacion, protegidos con OAuth 2.0 y publicados a Internet
a traves de AWS API Gateway.


## Repositorios

El sistema se entrega en dos repositorios, uno por componente:

| Componente                | Repositorio                                                  |
|---------------------------|--------------------------------------------------------------|
| Microservicios (backend)  | https://github.com/1samadhi/cloud-exp1-oidc                  |
| Frontend Angular          | https://github.com/1samadhi/cloud-exp1-front-angular         |

`scripts/desplegar-en-ec2.sh` clona y actualiza ambos en la instancia: compila
la imagen del frontend en su repositorio y levanta el stack desde este.

## Despliegue en marcha

| Recurso        | Valor                                              |
|----------------|----------------------------------------------------|
| URL publica    | https://j37oj1wn16.execute-api.us-east-1.amazonaws.com/desarrollo |
| HTTP API       | `j37oj1wn16`                                         |
| Instancia EC2  | `i-0314ddd12fadeb125`                              |

## Arquitectura

```
                    Internet
                       |
                       v
        +--------------------------------+
        |   AWS API Gateway (HTTP API)    |
        |   stage: desarrollo — HTTPS     |
        |                                 |
        |   Autorizador JWT               |
        |   issuer = este mismo stage     |
        +----------------+----------------+
                         | HTTP
                         v
        +--------------------------------+
        |   EC2 t3.small — Docker Compose |
        |                                 |
        |   front-end     :80   nginx     |
        |   ms-auth       :9000 IdP OIDC  |
        |   ms-productos  :8081 Resource  |
        |   ms-pedidos    :8082 Resource  |
        +--------------------------------+

Emisores aceptados por los Resource Server:
  - ms-auth (propio)   RS256, JWKS publicado por el gateway
  - Amazon Cognito     maquina a maquina
  - Microsoft Entra ID login de usuarios desde el frontend
```

Solo el API Gateway ofrece HTTPS. Los microservicios no confian en la red: cada
peticion se autoriza por el token, tanto en el borde como dentro de cada servicio.

## Microservicios

| Servicio       | Puerto | Rol                                                |
|----------------|--------|----------------------------------------------------|
| `ms-auth`      | 9000   | Identity Provider propio (OIDC)                    |
| `ms-productos` | 8081   | Catalogo de productos — Resource Server            |
| `ms-pedidos`   | 8082   | Gestion de pedidos — Resource Server               |
| `front-end`    | 80     | SPA React + Vite con MSAL                          |

## Emisores de identidad

Los Resource Server aceptan tokens de tres emisores a la vez, resueltos por el
claim `iss` del token entrante:

| Emisor                | Rol en la solucion                                 |
|-----------------------|----------------------------------------------------|
| `ms-auth` (propio)    | Identity Provider OIDC construido en el proyecto   |
| Amazon Cognito        | Identity as a Service, flujo maquina a maquina     |
| Microsoft Entra ID    | Login de usuarios desde el frontend con MSAL       |

Agregar o quitar un emisor es cambiar `SEGURIDAD_EMISORES`, sin recompilar.

## Stack

- Java 21, Spring Boot 4.1.0
- React 18 + Vite, MSAL para Entra ID
- Docker (multistage, usuario no root) y Docker Compose
- AWS EC2 + AWS API Gateway (HTTP API)

## Endpoints disponibles

### ms-auth — Identity Provider OIDC
| Metodo | Ruta                                    | Auth | Descripcion                          |
|--------|-----------------------------------------|------|--------------------------------------|
| POST   | `/auth/login`                           | No   | Valida credenciales y emite tokens   |
| GET    | `/auth/userinfo`                        | Si   | Claims del token presentado          |
| GET    | `/.well-known/openid-configuration`     | No   | Metadatos OIDC del emisor            |
| GET    | `/.well-known/jwks.json`                | No   | Llaves publicas para validar la firma|
| GET    | `/v1/estado`                        | No   | Estado y version del servicio        |

Usuarios de prueba:

| Usuario   | Contrasenia  | Roles                   |
|-----------|--------------|-------------------------|
| `admin`   | `admin123`   | `ROLE_ADMIN`, `ROLE_USER` |
| `cliente` | `cliente123` | `ROLE_USER`             |

Obtener un token:

```bash
curl -X POST http://localhost:9000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
```

#### Por que RS256 y no HS256

El autorizador JWT de AWS API Gateway verifica la firma descargando las llaves
publicas desde el `jwks_uri` que anuncia el discovery del emisor. Con HS256 la
firma depende de un secreto compartido que AWS nunca va a tener, asi que el
autorizador no podria validar nada. Por eso el IdP firma con RSA y publica su
llave publica.

### ms-productos
| Metodo | Ruta                  | Descripcion               |
|--------|-----------------------|---------------------------|
| GET    | `/v1/productos`      | Lista el catalogo         |
| GET    | `/v1/productos/{id}` | Consulta un producto      |

### ms-pedidos — Resource Server
| Metodo | Ruta                | Auth | Descripcion                                        |
|--------|---------------------|------|----------------------------------------------------|
| GET    | `/v1/public`    | No   | Comprobacion de despliegue                         |
| GET    | `/v1/pedidos`   | Si   | Pedidos del usuario del token                      |
| POST   | `/v1/pedidos`   | Si   | Crea un pedido — requiere scope `pedidos.escribir` |

`POST /v1/pedidos` valida el producto llamando a `ms-productos` y reenviando
el mismo token del usuario, de modo que la identidad viaja entre servicios en
lugar de confiar ciegamente en el llamador interno.

## Variables de entorno

| Variable              | Servicio            | Descripcion                                     |
|-----------------------|---------------------|-------------------------------------------------|
| `OIDC_ISSUER`         | ms-auth             | Valor del claim `iss`. En AWS, la URL del stage |
| `OIDC_AUDIENCIA`      | ms-auth             | Valor del claim `aud`                           |
| `OIDC_RUTA_LLAVE`     | ms-auth             | Ruta del JWK persistido                         |
| `SEGURIDAD_EMISORES`  | productos, pedidos  | Emisores confiables, separados por coma         |
| `SEGURIDAD_AUDIENCIAS`| productos, pedidos  | Audiencias aceptadas. Vacio desactiva el chequeo|
| `SEGURIDAD_ORIGENES_CORS` | productos, pedidos | Origenes del frontend permitidos             |
| `PRODUCTOS_URL`       | ms-pedidos          | URL base de ms-productos                        |

## Probar los endpoints

### Script de humo

Ejecuta las 18 comprobaciones y verifica el codigo HTTP de cada una:

```bash
./scripts/probar-endpoints.sh https://TU-API.execute-api.us-east-1.amazonaws.com/desarrollo
./scripts/probar-endpoints.sh http://localhost      # contra el stack local
```

### Thunder Client

1. Menu **Collections** → `...` → **Import** → `thunder-client/thunder-collection_EXP1.json`
2. Pestania **Env** → `...` → **Import** → `thunder-client/thunder-environment_EXP1.json`
3. **Activar el entorno EXP1** (marcarlo con el check). Sin entorno activo la
   peticion de login no puede guardar el token y todo lo demas da 401.
4. Ejecutar **1. Login IdP propio**. Su test `set-env-var` guarda el
   `access_token` en `{{token}}` y el resto de las peticiones lo toma solo.

Cada peticion trae aserciones sobre el codigo HTTP, asi que la barra de tests
queda en verde y sirve directamente como evidencia.

Para la carpeta de Cognito hay que rellenar antes `cognitoClientId` y
`cognitoClientSecret` en el entorno.

La carpeta **5. Multi emisor** llama directo a la EC2 saltandose el gateway: es
donde se ve que el mismo Resource Server acepta tokens de dos emisores distintos.

### Postman

Importar `postman/EXP1.postman_collection.json`. Mismo criterio: ejecutar primero
**1. Login IdP propio**, que guarda el token en la variable de coleccion.

### Navegador

Abrir la URL del stage. El frontend permite iniciar sesion, ver el token con sus
claims decodificados y llamar a cada endpoint mostrando la respuesta.

## Documentacion

| Documento                     | Contenido                                     |
|-------------------------------|-----------------------------------------------|
| `docs/01-cognito.md`          | User Pool, resource server y flujo maquina a maquina |
| `docs/02-entra-id.md`         | Registro en Azure, exponer la API y MSAL      |
| `docs/03-api-gateway.md`      | Rutas, autorizador JWT y la IP cambiante      |
| `docs/04-despliegue-ec2.md`   | La instancia, SSM y el control de costos      |
| `docs/05-base-de-datos.md`    | RDS MySQL, aislamiento de red y esquema       |
| `docs/06-frontend-angular.md` | Angular, MSAL, guard, interceptor y PKCE      |
| `thunder-client/`             | Coleccion y entorno de Thunder Client         |
| `postman/`                    | Coleccion de Postman con 16 peticiones        |
| `scripts/`                    | Despliegue, pruebas y correccion de la IP      |

## Como ejecutar

Con Docker Compose (levanta los tres servicios):

```bash
docker compose up --build -d
```

Verificar:

```bash
curl http://localhost:9000/v1/estado
curl http://localhost:8081/v1/productos
curl http://localhost:8082/v1/pedidos
```

Detener:

```bash
docker compose down
```

Un servicio por separado, sin Docker:

```bash
cd ms-productos && ./mvnw spring-boot:run
```

## Nota sobre persistencia

El catalogo y los pedidos viven en memoria. La actividad permite simular el almacen
de datos, y evitar un contenedor de base de datos deja la solucion dentro del
presupuesto de la cuenta AWS Academy y de la RAM de una instancia pequenia.
