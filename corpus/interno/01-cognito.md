# Cognito como Identity as a Service

Cognito es el segundo emisor confiable de la solucion. Los microservicios no
cambian de codigo para aceptarlo: basta agregar su issuer a `SEGURIDAD_EMISORES`.

## Lo que quedo creado

| Recurso              | Valor                                                        |
|----------------------|--------------------------------------------------------------|
| User Pool            | `us-east-1_9su4GmYfk`                                             |
| Issuer               | `https://cognito-idp.us-east-1.amazonaws.com/us-east-1_9su4GmYfk` |
| Dominio              | `exp1-oidc-u4gmyfk`                                       |
| Resource Server      | `exp1-api`                                                   |
| Cliente maquina a maquina | `5ag8ir0tp98mgfsh5kn53j5jfr`                             |

El *client secret* no aparece aqui ni en el repositorio: vive solo en el archivo
`.env` local, que esta en `.gitignore`.

Scopes definidos en el resource server `exp1-api`:
`productos.leer`, `productos.escribir`, `pedidos.leer`, `pedidos.escribir`.

## Crearlo desde cero por CLI

```bash
# 1. User Pool
POOL=$(aws cognito-idp create-user-pool \
  --pool-name exp1-oidc \
  --auto-verified-attributes email \
  --username-attributes email \
  --query 'UserPool.Id' --output text)

# 2. Dominio del endpoint de tokens
aws cognito-idp create-user-pool-domain --domain exp1-oidc-xxxx --user-pool-id $POOL

# 3. Resource Server con los scopes de la API
aws cognito-idp create-resource-server \
  --user-pool-id $POOL --identifier exp1-api --name "API EXP1" \
  --scopes '[{"ScopeName":"productos.leer","ScopeDescription":"Consultar el catalogo"},
             {"ScopeName":"productos.escribir","ScopeDescription":"Modificar el catalogo"},
             {"ScopeName":"pedidos.leer","ScopeDescription":"Consultar pedidos"},
             {"ScopeName":"pedidos.escribir","ScopeDescription":"Crear pedidos"}]'

# 4. Cliente maquina a maquina (client_credentials, sin interaccion de usuario)
aws cognito-idp create-user-pool-client \
  --user-pool-id $POOL --client-name exp1-maquina-a-maquina --generate-secret \
  --allowed-o-auth-flows client_credentials --allowed-o-auth-flows-user-pool-client \
  --allowed-o-auth-scopes "exp1-api/productos.leer" "exp1-api/pedidos.escribir" \
  --supported-identity-providers COGNITO
```

## Pedir un token

```bash
curl -X POST https://exp1-oidc-u4gmyfk.auth.us-east-1.amazoncognito.com/oauth2/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -u "$COGNITO_CLIENT_ID:$COGNITO_CLIENT_SECRET" \
  -d 'grant_type=client_credentials&scope=exp1-api/productos.leer exp1-api/pedidos.escribir'
```

Este es el mismo comando que la consola de Cognito entrega como "curl" y que se
importa en Postman.

## El detalle que rompe la autorizacion si se pasa por alto

Cognito antepone el identificador del resource server a cada scope. El token no
trae `pedidos.escribir` sino:

```json
"scope": "exp1-api/pedidos.escribir exp1-api/productos.leer"
```

Si el Resource Server mapeara el scope tal cual, la autoridad quedaria como
`SCOPE_exp1-api/pedidos.escribir` y ningun `@PreAuthorize` escrito contra
`SCOPE_pedidos.escribir` coincidiria: el token seria valido pero daria 403.
Por eso `SecurityConfig` recorta el prefijo antes de construir la autoridad.

## Conectarlo a los microservicios

```bash
SEGURIDAD_EMISORES=http://localhost:9000,https://cognito-idp.us-east-1.amazonaws.com/us-east-1_9su4GmYfk
```

No hay que recompilar ni tocar `SecurityConfig`.
