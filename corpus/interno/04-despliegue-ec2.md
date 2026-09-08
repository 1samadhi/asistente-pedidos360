# Despliegue en EC2

## La instancia

| Dato               | Valor                                |
|--------------------|--------------------------------------|
| Instancia          | `i-0314ddd12fadeb125`                |
| Tipo               | `t3.small` (2 GB RAM)                |
| Sistema            | Amazon Linux 2023                    |
| Disco              | 20 GB gp3                            |
| Security Group     | `sg-02d3746ecad5b5492`             |
| Key pair           | `vockey`                             |
| Perfil IAM         | `LabInstanceProfile` (habilita SSM)  |

### Por que t3.small y no t3.micro

Una `t3.micro` tiene 913 MB de RAM, de los que quedan unos 600 MB libres. Tres
JVM de Spring Boot consumen entre 250 y 350 MB de RSS **cada una**, y eso no se
arregla bajando `-Xmx`: el heap es solo una parte del consumo real, aparte van
metaspace, code cache y las pilas de los hilos. Con `t3.small` (2 GB) los tres
servicios mas nginx caben con holgura.

Se agregaron ademas 2 GB de swap, porque el pico de compilacion de Maven dentro
de Docker es bastante mas alto que el consumo en regimen.

### Puertos del Security Group

| Puerto | Motivo                                            |
|--------|---------------------------------------------------|
| 22     | SSH con `vockey`                                  |
| 80     | nginx del frontend                                |
| 9000   | ms-auth                                           |
| 8081   | ms-productos                                      |
| 8082   | ms-pedidos                                        |

Los puertos de los microservicios estan abiertos porque una HTTP API con
integracion HTTP necesita alcanzar el destino por Internet. Lo que los protege
no es la red sino el token: sin un JWT valido responden 401.

En una arquitectura de produccion esto se resolveria con un **VPC Link**, que
permite integrar el API Gateway con instancias en subredes privadas sin
exponerlas. Se descarto aqui porque agrega un balanceador de carga, y su costo
por hora no cabe en el presupuesto de la cuenta de AWS Academy.

## Acceso sin SSH

La instancia tiene el perfil `LabInstanceProfile`, asi que se puede operar por
**Systems Manager** sin abrir una sesion SSH:

```bash
aws ssm start-session --target i-0314ddd12fadeb125
```

## Desplegar

```bash
./scripts/desplegar-en-ec2.sh i-0314ddd12fadeb125
```

Hace `git pull` y `docker compose up --build -d` dentro de la instancia.

La primera compilacion tarda varios minutos porque Maven descarga las
dependencias de los tres servicios. Las siguientes reutilizan la cache de capas
de Docker.

## Rutina al retomar el laboratorio

AWS Academy detiene las instancias al cerrar la sesion. Al volver:

```bash
# 1. Encender la instancia
aws ec2 start-instances --instance-ids i-0314ddd12fadeb125

# 2. Re-apuntar el API Gateway a la IP nueva
./scripts/actualizar-api-gateway.sh j37oj1wn16 i-0314ddd12fadeb125

# 3. Los contenedores levantan solos (restart: unless-stopped)
```

Las credenciales de AWS Academy tambien caducan al cerrar la sesion: hay que
copiar las nuevas a `~/.aws/credentials` antes de ejecutar estos comandos.

## Control de costos

Lo que se cobra por hora de forma continua es lo que hay que vigilar; el computo
solo corre mientras el laboratorio esta encendido.

| Recurso              | Costo                      | Estado             |
|----------------------|----------------------------|--------------------|
| EC2 t3.small         | ~$0.021/h **encendida**    | Se apaga sola      |
| EBS 20 GB gp3        | ~$1.60/mes continuo        | Permanente         |
| NAT Gateway          | ~$32/mes continuo          | **No se uso**      |
| Elastic IP           | ~$3.60/mes si esta detenida| **No se uso**      |
| API Gateway HTTP API | $1.00 por millon de peticiones | Despreciable   |
| Cognito              | Gratis hasta 50.000 usuarios activos | Gratis     |

Evitar el NAT Gateway y las Elastic IP es lo que mantiene el gasto fijo cerca de
cero. El precio a pagar es tener que re-apuntar las integraciones cuando cambia
la IP, que es justo lo que automatiza `scripts/actualizar-api-gateway.sh`.
