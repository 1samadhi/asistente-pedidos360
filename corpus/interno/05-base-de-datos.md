# Base de datos cloud (RDS MySQL)

## Por que RDS y no un contenedor en la EC2

La pauta pide integrar el backend con una base de datos cloud mediante
entidades, repositorios y propiedades de conexion. Un contenedor MySQL dentro
de la misma EC2 cumpliria la parte tecnica, pero seguiria siendo un servicio
autogestionado: es justo la arquitectura que el enunciado pide dejar atras.
Con RDS el motor, los parches y el almacenamiento los administra AWS.

En desarrollo local si se usa un contenedor, porque no tiene sentido pagar una
instancia para probar. La configuracion es la misma en ambos casos: solo cambia
el valor de `DB_HOST`.

## La instancia

| Parametro       | Valor                                              |
|-----------------|----------------------------------------------------|
| Identificador   | `pedidos360-db`                                    |
| Motor           | MySQL 8.0                                          |
| Clase           | `db.t3.micro`                                      |
| Almacenamiento  | 20 GB gp2                                          |
| Accesible publicamente | No                                          |
| Security group  | `pedidos360-rds-sg`                                |
| Subnet group    | `pedidos360-subnets`                               |

## Aislamiento de red

La instancia no tiene IP publica. La unica regla de entrada abre el puerto 3306
**hacia el security group de la EC2**, no hacia un rango de direcciones:

```
sg-0eb01ac3f105a14c2  (RDS)
    entrada  tcp/3306  origen: sg-02d3746ecad5b5492  (EC2)
```

Referenciar el security group en lugar de una IP importa en el Learner Lab,
donde la IP publica de la EC2 cambia en cada reinicio: la regla sigue siendo
valida sin tocarla. El API Gateway, en cambio, si guarda la IP en sus
integraciones y hay que corregirla con `scripts/actualizar-api-gateway.sh`.

Comprobacion de que el aislamiento funciona:

```bash
# desde la EC2 (via SSM)
timeout 15 bash -c '</dev/tcp/pedidos360-db.ci6tydtphtks.us-east-1.rds.amazonaws.com/3306' \
  && echo ALCANZABLE
# -> ALCANZABLE

# desde internet
timeout 12 bash -c '</dev/tcp/pedidos360-db.ci6tydtphtks.us-east-1.rds.amazonaws.com/3306' \
  || echo BLOQUEADO
# -> BLOQUEADO
```

El nombre DNS si resuelve publicamente, pero a una direccion privada
(`172.31.28.48`), que no es enrutable desde fuera de la VPC.

## Usuarios

| Usuario      | Uso                          | Permisos                              |
|--------------|------------------------------|---------------------------------------|
| `admin`      | tareas administrativas       | maestro de la instancia               |
| `pedidos360` | los microservicios           | solo sobre el esquema `pedidos360`    |

Los microservicios nunca usan el usuario maestro. Si alguno se viera
comprometido, el atacante no podria crear usuarios ni tocar otras bases.

## Esquema

Hibernate crea y actualiza las tablas al arrancar (`ddl-auto: update`) a partir
de las anotaciones de las entidades. Para la experiencia es suficiente; en un
sistema real se usaria una herramienta de migraciones como Flyway o Liquibase,
porque `update` no sabe borrar ni renombrar columnas.

```
productos                        pedidos
  id       bigint PK               id           bigint PK
  nombre   varchar(120)            cantidad     int
  precio   int                     cliente      varchar(200)  indexado
                                   creado       datetime(6)
                                   producto_id  bigint
```

`pedidos.cliente` guarda el claim `sub` del token, es decir el identificador
que asigna el IdP. Va indexado porque toda consulta del servicio filtra por el.
No hay clave foranea hacia `productos`: son microservicios distintos y cada uno
es dueño de sus datos; la existencia del producto se valida por HTTP contra
ms-productos propagando el token del usuario.

## Variables de conexion

| Variable      | Local            | AWS                                   |
|---------------|------------------|---------------------------------------|
| `DB_HOST`     | `mysql`          | endpoint del RDS                      |
| `DB_PUERTO`   | `3306`           | `3306`                                |
| `DB_NOMBRE`   | `pedidos360`     | `pedidos360`                          |
| `DB_USUARIO`  | `pedidos360`     | `pedidos360`                          |
| `DB_PASSWORD` | ver `.env`       | ver `.env`                            |

Las credenciales viven en `.env`, que esta en `.gitignore`. La plantilla
`.env.example` solo lleva valores de ejemplo.

## Costos

`db.t3.micro` cuesta del orden de USD 0,017 por hora mas el almacenamiento. En
el Learner Lab la instancia se detiene junto con el laboratorio, asi que el
gasto real se limita a las horas de trabajo. Se apaga a mano con:

```bash
aws rds stop-db-instance --db-instance-identifier pedidos360-db
aws rds start-db-instance --db-instance-identifier pedidos360-db
```

Las copias de seguridad automaticas estan desactivadas
(`--backup-retention-period 0`) porque los datos son de prueba y cada snapshot
ocupa almacenamiento facturable.
