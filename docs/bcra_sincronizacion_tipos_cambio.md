# Sincronización de tipos de cambio (BCRA)

La release `v1.1.0-beta.1` agrega una tarea programada que trae el **tipo de cambio oficial
del Banco Central de la República Argentina (BCRA)** para mantener al día las cotizaciones
usadas por el módulo de Recursos. Este documento explica qué hace, cómo se ejecuta y en qué
estado queda para Infraestructura GIDAS.

**Estado al 2026-10-08:** no instalado. La tabla `tipo_cambio` existe pero tiene **0 filas**,
porque la tarea nunca corrió. No afecta la operación: nada del sistema depende de que esté
corriendo todavía.

---

## Ruta rápida

1. Correrlo una vez a mano para poblar la tabla:

   ```bash
   cd /home/infra/gidas
   bash scripts/run-bcra-sync.sh
   ```

2. Verificar que haya datos:

   ```bash
   docker compose --env-file .env.production exec -T db psql -U gidas_admin -d gidas_db \
     -tAc "select fecha_cotizacion, moneda_origen, moneda_destino, valor from tipo_cambio order by fecha_cotizacion desc limit 5"
   ```

3. Para dejarlo automático: instalar el cron (ver "Instalación del cron").

---

## Qué hace

Consulta la API pública del BCRA y guarda una fila por cotización en la tabla `tipo_cambio`.

| Tema | Detalle |
|---|---|
| API | `https://api.bcra.gob.ar/estadisticas/v4.0` (variable `BCRA_API_BASE_URL`) |
| Serie | `7927` — tipo de cambio minorista, vendedor (variable `BCRA_RETAIL_EXCHANGE_RATE_SERIES`) |
| Variable | `4` (variable `BCRA_RETAIL_EXCHANGE_RATE_VARIABLE_ID`) |
| Filtro de texto | `tipo de cambio minorista,vendedor` (description tokens) y `9791` (methodology tokens) |
| Mirada hacia atrás | 7 días (`BCRA_SYNC_LOOKBACK_DAYS`) — refresca los últimos días por si hubo un dato atrasado |
| Timeout | 10 segundos (`BCRA_REQUEST_TIMEOUT_SECONDS`) |
| Código | `backend/modules/recursos/clients/bcra_client.py`, `backend/modules/recursos/services/tipo_cambio_service.py`, job `backend/modules/recursos/jobs/sincronizar_tipos_cambio.py` |
| Migración | `d8e1f4a6b2c9` — "Cotizaciones oficiales y equivalentes históricos de movimientos" |

El job no recibe argumentos: crea la app de Flask, entra en contexto y llama
`TipoCambioService.sincronizar()`.

### Tabla `tipo_cambio`

```text
id, moneda_origen, moneda_destino, fecha_cotizacion, valor (numeric 18,6),
serie_bcra, fuente, fecha_obtencion, created_at
```

---

## Instalación del cron

El archivo de ejemplo es `scripts/bcra-sync.cron.example`:

```cron
CRON_TZ=America/Argentina/Buenos_Aires
0 18 * * * /bin/sh /srv/gidas/scripts/run-bcra-sync.sh
```

Ojo con dos detalles antes de copiarlo tal cual:

- La ruta del ejemplo es `/srv/gidas`; en esta VM el proyecto vive en **`/home/infra/gidas`**.
- Instalar con el cron real del usuario que corre Docker:

```bash
crontab -e
# pegar (con la ruta corregida):
CRON_TZ=America/Argentina/Buenos_Aires
0 18 * * * /bin/sh /home/infra/gidas/scripts/run-bcra-sync.sh
```

La tarea corre todos los días a las **18:00 (hora Argentina)** dentro del contenedor del
backend, usando `.env.production` (se puede cambiar con `BCRA_COMPOSE_ENV_FILE`).

---

## Operación y verificación

```bash
# correr a mano en cualquier momento
bash scripts/run-bcra-sync.sh

# ver el último registro y su fecha de obtención
docker compose --env-file .env.production exec -T db psql -U gidas_admin -d gidas_db \
  -tAc "select fecha_cotizacion, valor, fecha_obtencion from tipo_cambio order by fecha_obtencion desc limit 3"

# comprobar que el cron quedó instalado
crontab -l | grep bcra
```

Si la API del BCRA no responde, el script falla con error (timeout de 10 s) y no escribe nada:
no deja la tabla a medias. Reprogramar o reintentar a mano.

---

## Decisiones pendientes

- [ ] Confirmar con desarrollo que queremos el cron diario instalado (la feature es suya,
      la ejecución en la VM es nuestra).
- [ ] Correr una primera sincronización manual y validar que los valores coinciden con el
      sitio del BCRA.
- [ ] Verificar en el próximo cierre de día que el cron corrió a las 18:00.
- [ ] Aclarar en la comunicación a Dirección que la sincronización quedó activada (hoy
      figura como pendiente en `docs/dossier_direccion_gidas/mail_actualizacion_v1_1_0_beta_1.md`).

## Próximo paso

Instalar el cron después de la primera corrida manual exitosa, y marcar la decisión como
resuelta en `docs/indice_release_v1_1_0_beta_1.md`.
