# Microsoft Entra ID como Identity as a Service

Entra ID es el proveedor de identidad del sistema. Los microservicios no guardan
contrasenias ni saben autenticar: solo verifican la firma de los tokens que
Microsoft emite.

## El tenant

| Dato               | Valor                                              |
|--------------------|----------------------------------------------------|
| Nombre             | Pedidos360                                         |
| Tenant ID          | `5cb85dc6-a73b-41fc-b2b9-5b2a9b3f531b`             |
| Dominio            | `pedidos360ismaoyarzun.onmicrosoft.com`            |
| Tipo               | Microsoft Entra ID (workforce)                     |
| Licencia           | Entra ID Free                                      |
| Emisor de tokens   | `https://login.microsoftonline.com/<tenant>/v2.0`  |

### Por que workforce y no External ID

El material de la asignatura indica crear un tenant **Microsoft Entra External
ID**, que es la variante CIAM y trae registro de usuarios en autoservicio. No se
pudo, y la razon quedo comprobada:

```
ciamDirectories admite las ubicaciones:
  global, unitedstates, europe, asiapacific, australia, japan

Azure for Students restringe los despliegues a:
  brazilsouth, westus3, centralus, canadacentral, southafricanorth
```

La interseccion es vacia. Crear el recurso en `unitedstates` responde
`RequestDisallowedByPolicy`, y la restriccion regional es una asignacion **de
sistema**: `az policy exemption create` devuelve "Cannot create exemption for
system policy assignments" incluso siendo Owner de la suscripcion.

El registro de usuarios que aporta External ID se implementa en su lugar contra
Microsoft Graph desde el backend. Ver la seccion "Registro de usuarios".

## La aplicacion registrada

| Dato               | Valor                                              |
|--------------------|----------------------------------------------------|
| Nombre             | Pedidos360 SPA                                     |
| Client ID          | `c483f102-da2d-41b5-b48e-26e7ca78ab98`             |
| Application ID URI | `api://c483f102-da2d-41b5-b48e-26e7ca78ab98`       |
| Tipo de cuenta     | Solo este directorio (`AzureADMyOrg`)              |
| Version del token  | 2                                                  |

### Registro y redirecciones

```bash
az ad app create --display-name "Pedidos360 SPA" --sign-in-audience AzureADMyOrg
az ad app update --id $OBJ --identifier-uris "api://$APPID"

az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/$OBJ" \
  --body '{"spa":{"redirectUris":[
     "http://localhost:4200",
     "https://<stage>.execute-api.us-east-1.amazonaws.com/desarrollo/"]}}'
```

Las redirecciones van en `spa`, **no en `web`**. Es la diferencia critica: con
`web` Azure asume que existe un backend capaz de guardar un secreto y exige
`client_secret`, que una aplicacion de pagina unica no puede esconder porque su
JavaScript es visible. Con `spa` Azure habilita **Authorization Code con PKCE**.
Elegir mal no da ningun error evidente: el login falla recien al canjear el
codigo.

Comprobacion:

```bash
az ad app show --id $OBJ --query "{spa:spa.redirectUris,web:web.redirectUris}"
# web debe salir vacio
```

### Scopes y roles

```bash
# Primero los scopes, y en una segunda llamada la preautorizacion: no se puede
# preautorizar un permiso que todavia no existe.
az rest --method PATCH --uri ".../applications/$OBJ" --body '{"api":{
  "oauth2PermissionScopes":[
    {"id":"<uuid>","value":"productos.leer","type":"User", ...},
    {"id":"<uuid>","value":"pedidos.escribir","type":"User", ...}]}}'

az rest --method PATCH --uri ".../applications/$OBJ" --body '{"api":{
  "preAuthorizedApplications":[{"appId":"<clientId>","delegatedPermissionIds":[...]}]}}'

az rest --method PATCH --uri ".../applications/$OBJ" --body '{"appRoles":[
  {"id":"<uuid>","value":"ADMIN","allowedMemberTypes":["User"], ...},
  {"id":"<uuid>","value":"USER","allowedMemberTypes":["User"], ...}]}'
```

Preautorizar la propia SPA evita la pantalla de consentimiento en cada login.

Los **scopes** dicen que puede hacer la aplicacion (`pedidos.escribir`); los
**roles** dicen quien es la persona (`ADMIN`). El controlador de pedidos usa los
dos: `hasAuthority('SCOPE_pedidos.escribir') or hasRole('ADMIN')`.

### Version 2 de los tokens

Por defecto Entra emite tokens **v1**, con emisor `https://sts.windows.net/<tenant>/`,
que es el formato heredado. Se cambia a v2:

```bash
az rest --method PATCH --uri ".../applications/$OBJ" \
  --body '{"api":{"requestedAccessTokenVersion":2}}'
```

Con v2 el emisor pasa a `https://login.microsoftonline.com/<tenant>/v2.0`, que
es el que espera MSAL, el que publica discovery OIDC estandar y el que el
autorizador JWT de AWS puede consultar.

## Usuarios de prueba

```bash
az ad user create --display-name "Administrador Pedidos360" \
  --user-principal-name "admin@<dominio>" --password "<clave>" \
  --force-change-password-next-sign-in false

# Asignar el rol requiere el service principal de la aplicacion
az ad sp create --id $APPID
az rest --method POST --uri "https://graph.microsoft.com/v1.0/users/$USER/appRoleAssignments" \
  --body '{"principalId":"<usuarioId>","resourceId":"<spId>","appRoleId":"<rolId>"}'
```

| Usuario                  | Roles         |
|--------------------------|---------------|
| `admin@<dominio>`        | ADMIN, USER   |
| `cliente@<dominio>`      | USER          |

Las contrasenias estan en `.env`, que no se commitea.

## Conectarlo al resto del sistema

### API Gateway

```bash
aws apigatewayv2 create-authorizer --api-id $API \
  --name entra-id --authorizer-type JWT \
  --identity-source '$request.header.Authorization' \
  --jwt-configuration "Issuer=https://login.microsoftonline.com/$TEN/v2.0,Audience=$APPID"
```

AWS descarga por su cuenta el JWKS que anuncia el discovery de Azure. Las dos
nubes no comparten credenciales ni red: el unico puente es criptografia de llave
publica.

Un autorizador JWT admite **un solo emisor**. Por eso la validacion multi emisor
vive en los microservicios y no en el gateway.

### Microservicios

Solo variables de entorno, sin tocar codigo:

```
SEGURIDAD_EMISORES=https://login.microsoftonline.com/<tenant>/v2.0,<emisor del IdP propio>
SEGURIDAD_AUDIENCIAS=<clientId>,exp1-api
```

El `SecurityConfig` elige el validador segun el claim `iss` del token entrante y
normaliza los permisos de cada emisor a un mismo vocabulario.

## Claims de un token de Entra

```json
{
  "iss": "https://login.microsoftonline.com/5cb85dc6-.../v2.0",
  "aud": "c483f102-da2d-41b5-b48e-26e7ca78ab98",
  "sub": "a_2SyIjVm22xKmjUXc-...",
  "scp": "pedidos.escribir productos.leer",
  "roles": ["USER", "ADMIN"],
  "ver": "2.0"
}
```

Entra usa `scp` para los scopes, mientras el IdP propio y Cognito usan `scope`.
El convertidor de autoridades lee ambos, por eso el mismo codigo sirve para los
tres emisores.

## Diferencias entre los emisores

| Aspecto              | IdP propio     | Cognito              | Entra ID          |
|----------------------|----------------|----------------------|-------------------|
| Claim de scopes      | `scope`        | `scope` con prefijo  | `scp`             |
| Claim de roles       | `roles`        | `cognito:groups`     | `roles`           |
| Claim `aud`          | si             | no en client_credentials | si            |
| Flujo del frontend   | contrasenia    | client_credentials   | code + PKCE       |

## Pruebas sin navegador

Para pedir un token desde curl o Thunder Client sin pasar por el navegador se
habilito el cliente publico:

```bash
az rest --method PATCH --uri ".../applications/$OBJ" \
  --body '{"isFallbackPublicClient":true}'

curl -X POST "https://login.microsoftonline.com/$TEN/oauth2/v2.0/token" \
  -d "client_id=$APPID" -d "grant_type=password" \
  -d "scope=api://$APPID/productos.leer api://$APPID/pedidos.escribir" \
  -d "username=admin@<dominio>" -d "password=<clave>"
```

Es solo para pruebas. El frontend **no** usa este flujo: usa Authorization Code
con PKCE a traves de MSAL, que es lo que exige la evaluacion. El flujo de
contrasenia manda las credenciales del usuario a la aplicacion, cosa que PKCE
evita por completo.
