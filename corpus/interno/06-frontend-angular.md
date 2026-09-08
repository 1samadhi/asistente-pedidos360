# Frontend Angular con MSAL

El codigo vive en un repositorio aparte, como pide el enunciado:
https://github.com/1samadhi/cloud-exp1-front-angular

Este documento resume las decisiones de diseño relevantes para la evaluacion.

## Versiones

| Paquete                  | Version | Por que                                            |
|--------------------------|---------|----------------------------------------------------|
| `@angular/core`          | 22.1    | estable actual                                     |
| `@azure/msal-angular`    | 6.2     | publicada despues de Angular 22                    |
| `@azure/msal-browser`    | 5.21    | peer dependency de msal-angular                    |

`@azure/msal-angular` no declara `@angular/core` entre sus peer dependencies,
asi que npm no avisa si las versiones no encajan: el fallo aparece recien en
tiempo de ejecucion. La compatibilidad se verifico por fecha de publicacion.

## Las dos piezas de MSAL

### MsalGuard

Protege las rutas en `app.routes.ts`:

```ts
{ path: 'catalogo', component: Catalogo, canActivate: [MsalGuard] }
```

Si no hay sesion activa, redirige a Microsoft **antes** de construir el
componente. No hay ninguna comprobacion de sesion escrita a mano.

`/` y `/registro` quedan abiertas: quien todavia no tiene cuenta debe poder
llegar a ellas.

### MsalInterceptor y el protectedResourceMap

En `auth/msal.config.ts`:

```ts
mapa.set(`${api}/v1/productos`, [SCOPES.productosLeer]);
mapa.set(`${api}/v1/pedidos`,   [SCOPES.pedidosEscribir]);
```

Se declara que scope corresponde a cada URL, y el interceptor obtiene el token,
lo renueva si expiro y lo adjunta. Por eso `servicios/api.ts` no manipula
tokens en ningun metodo.

Las URL que no estan en el mapa viajan sin token, que es lo que se busca para
`/v1/public` y `/auth/registro`.

## Authorization Code con PKCE

No se programa: MSAL lo aplica solo porque la aplicacion esta registrada en
Entra ID con redirecciones de tipo `spa`. MSAL genera el `code_verifier`,
envia su hash como `code_challenge` y presenta el original al canjear el
codigo. Un codigo interceptado no sirve sin el verifier.

La configuracion no lleva ningun secreto, y no puede llevarlo: el JavaScript de
una SPA es visible. Esa es justamente la razon de ser de PKCE.

## Manejo de la redireccion

`msal-browser` v5 exige `initialize()` antes de cualquier otra llamada:

```ts
this.msal.initialize()
  .pipe(concatMap(() => this.msal.handleRedirectObservable()))
  .subscribe(...)
```

Despues hay que fijar la cuenta activa con `setActiveAccount`: MSAL admite
varias cuentas en cache y tanto el guard como el interceptor piden tokens para
la activa.

## Base href

El stage del API Gateway sirve la aplicacion bajo `/desarrollo/`. La imagen se
construye con `--base-href /desarrollo/`; con el valor por defecto `/` el
enrutador generaria enlaces a `/catalogo` y la navegacion se romperia.

`nginx.conf` devuelve `index.html` para cualquier ruta desconocida, porque el
enrutado ocurre en el navegador y recargar `/catalogo` daria 404.

## Configuracion por entorno

Angular resuelve la configuracion en tiempo de compilacion mediante
`fileReplacements`, no por variables de entorno: `environment.prod.ts`
sustituye a `environment.ts` en la build de produccion. Por eso la URL del
stage y los identificadores de Entra quedan incrustados en el bundle.

## Paginas

| Ruta        | Protegida | Contenido                                        |
|-------------|-----------|--------------------------------------------------|
| `/`         | no        | explicacion del flujo y llamada a `/v1/public`    |
| `/registro` | no        | formulario que crea la cuenta en el tenant        |
| `/catalogo` | si        | productos desde RDS y creacion de pedidos         |
| `/pedidos`  | si        | pedidos del usuario del token                     |
| `/perfil`   | si        | claims del id_token, del access_token y del backend |

`/perfil` sirve como evidencia en la presentacion: muestra los claims `scp` y
`roles` que emite Entra junto a lo que el microservicio ve tras validar la firma.
