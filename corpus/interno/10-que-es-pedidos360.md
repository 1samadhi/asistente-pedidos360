# Qué es Pedidos360

Pedidos360 es una plataforma **B2B de gestión de pedidos** que se entrega como API. La
usan comercios asociados —no consumidores finales— para registrar y consultar los pedidos
de su operación desde sus propios sistemas.

> **Por qué existe este documento.** El resto de la documentación explica *cómo* se
> construyó la plataforma: el gateway, los emisores de identidad, el despliegue. Ninguno
> explicaba *qué es*. Se detectó al preguntárselo al asistente de integración, que
> respondió correctamente que no lo sabía.

## Qué problema resuelve a un comercio

Un comercio que vende productos necesita registrar pedidos, consultarlos y cruzarlos con
su catálogo. Construir eso desde cero significa base de datos, autenticación, control de
acceso y operación. Pedidos360 se lo entrega como servicio: el comercio integra su sistema
contra una API y se despreocupa de la infraestructura.

## Lo que la diferencia: autenticación federada

La mayoría de las plataformas obligan al comercio a crear usuarios nuevos y gestionar otra
contraseña más. Pedidos360 no.

Cada comercio **entra con la identidad corporativa que ya usa**. Si la empresa trabaja con
Microsoft 365, sus empleados acceden con esa misma cuenta a través de Microsoft Entra ID,
sin altas, sin contraseñas nuevas y sin que Pedidos360 llegue a ver ninguna credencial.

Para eso la plataforma acepta **tres emisores de identidad a la vez**:

| Emisor | Para qué |
|---|---|
| Microsoft Entra ID | Personas del comercio, desde el frontend |
| Amazon Cognito | Sistemas que llaman a la API sin usuario de por medio |
| `ms-auth`, IdP propio | Pruebas, y comercios sin proveedor de identidad propio |

Los microservicios resuelven cuál aplicar leyendo el claim `iss` del token. Añadir un
emisor nuevo es configuración, no código.

## Qué ofrece hoy

| Recurso | Operaciones |
|---|---|
| Catálogo de productos | Consultar el catálogo y el detalle de un producto |
| Pedidos | Crear un pedido y listar los propios |

Cada comercio ve **solo sus pedidos**: la API filtra por la identidad del token, así que
el aislamiento no depende de que el cliente pida bien las cosas.

## Cómo se integra un comercio

1. Obtiene un token de su emisor de identidad.
2. Llama a la API pasándolo en la cabecera `Authorization`.
3. Recibe únicamente los datos que le corresponden.

La guía de errores frecuentes cubre lo que suele fallar en ese camino.

## Sobre qué está construido

Tres microservicios Spring Boot (Java 21) desplegados en AWS: **API Gateway** como único
punto de entrada público, **EC2** ejecutando los servicios en contenedores y **RDS MySQL**
como base de datos. El frontend es una aplicación Angular que autentica con MSAL.

La arquitectura es deliberadamente conservadora: el gateway filtra el tráfico no
autenticado antes de que llegue a consumir recursos, y cada microservicio vuelve a validar
el token por su cuenta. Ninguno confía en que la red sea segura.
