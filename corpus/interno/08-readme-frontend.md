# Pedidos360 — Frontend

Aplicacion Angular del sistema Pedidos360. Autentica contra **Microsoft Entra
ID** mediante Authorization Code con PKCE y consume la API a traves del **AWS
API Gateway**.

El backend vive en un repositorio aparte:
https://github.com/1samadhi/cloud-exp1-oidc

## Tecnologias

| Paquete                  | Version |
|--------------------------|---------|
| `@angular/core`          | 22.1    |
| `@azure/msal-angular`    | 6.2     |
| `@azure/msal-browser`    | 5.21    |

`@azure/msal-angular` no declara `@angular/core` entre sus peer dependencies,
asi que npm no avisa si las versiones no encajan. La compatibilidad se
comprobo por fecha de publicacion: msal-angular 6.2 salio despues de Angular 22.

## Las dos piezas de MSAL

### MsalGuard

En `src/app/app.routes.ts`:

```ts
{ path: 'catalogo', component: Catalogo, canActivate: [MsalGuard] }
```

Si no hay sesion activa redirige a Microsoft **antes** de construir el
componente. No hay ninguna comprobacion de sesion escrita a mano.

`/` y `/registro` quedan abiertas: quien todavia no tiene cuenta debe poder
llegar a ellas.

### MsalInterceptor

En `src/app/auth/msal.config.ts`:

```ts
mapa.set(`${api}/v1/productos`, [SCOPES.productosLeer]);
mapa.set(`${api}/v1/pedidos`,   [SCOPES.pedidosEscribir]);
```

Se declara que scope corresponde a cada URL y el interceptor obtiene el token,
lo renueva si expiro y lo adjunta. Por eso `src/app/servicios/api.ts` no toca
la cabecera `Authorization` en ningun metodo.

Las URL que no aparecen en el mapa viajan sin token, que es lo que se busca
para `/v1/public` y `/auth/registro`.

## PKCE

No se programa. MSAL lo aplica porque la aplicacion esta registrada en Entra ID
con redirecciones de tipo **spa**: genera el `code_verifier`, envia su hash como
`code_challenge` y presenta el original al canjear el codigo, de modo que un
codigo interceptado no sirve.

La configuracion no lleva ningun secreto, y no puede llevarlo: el JavaScript de
una SPA es publico. Esa es precisamente la razon de ser de PKCE.

## Paginas

| Ruta        | Protegida | Contenido                                           |
|-------------|-----------|-----------------------------------------------------|
| `/`         | no        | explicacion del flujo y llamada a `/v1/public`      |
| `/registro` | no        | formulario que crea la cuenta en el tenant          |
| `/catalogo` | si        | productos y creacion de pedidos                     |
| `/pedidos`  | si        | pedidos del usuario del token                       |
| `/perfil`   | si        | claims del id_token, del access_token y del backend |

## Desarrollo

```bash
npm install
npm start          # http://localhost:4200
```

`http://localhost:4200` esta registrado como redireccion en Entra ID y
autorizado en el CORS del API Gateway.

## Construccion

```bash
npm run build -- --configuration production --base-href /desarrollo/
```

El stage del API Gateway sirve la aplicacion bajo `/desarrollo/`. Con el valor
por defecto `/` el enrutador generaria enlaces a `/catalogo` y la navegacion se
romperia.

La configuracion se resuelve en tiempo de compilacion mediante
`fileReplacements`, no por variables de entorno: `environment.prod.ts` sustituye
a `environment.ts` en la build de produccion.

## Contenedor

```bash
docker build -t exp1/front-angular:6.0.0 .
docker run -p 80:80 exp1/front-angular:6.0.0
```

`nginx.conf` devuelve `index.html` para cualquier ruta desconocida, porque el
enrutado ocurre en el navegador y recargar `/catalogo` daria 404.
