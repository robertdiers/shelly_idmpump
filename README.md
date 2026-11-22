# shelly_idmpump

use Shelly Pro 3EM values to set PV generation for iDM pump

The MQTT values published by a Shelly Pro 3EM are read and written to the
iDM heat pump every 3 minutes. At 23:00 an emergency job writes 0 to the iDM.

## Configuration

Defaults are in `python/shelly-idm.ini`. Every value can be overridden by an
environment variable:

| Environment variable | Example |
| --- | --- |
| `MQTT_BROKER` | `192.168.1.3` |
| `MQTT_USER` | `admin` |
| `MQTT_PASSWORD` | `mypassword` |
| `MQTT_TOPIC` | `shellypro3em-fce8c0d97c10/status/em:0` |
| `IDM_IP` | `192.168.1.81` |
| `IDM_PORT` | `502` |
| `FEED_IN_LIMIT` | `300` (Watt) |

## Deployment

Build the image locally:

```bash
docker build -t shelly-idmpump:latest .
```

Run the container, overriding the MQTT settings and the iDM IP:

```bash
docker run -d \
  --name shelly-idmpump \
  --restart unless-stopped \
  -e MQTT_BROKER=192.168.1.3 \
  -e MQTT_USER=admin \
  -e MQTT_PASSWORD=mypassword \
  -e MQTT_TOPIC=shellypro3em-fce8c0d97c10/status/em:0 \
  -e IDM_IP=192.168.1.81 \
  -e IDM_PORT=502 \
  -e FEED_IN_LIMIT=300 \
  shelly-idmpump:latest
```

To avoid exposing the password in the shell history or process list, put the
`-e` values in a file instead and use `--env-file /path/to/shelly-idm.env`.

Follow the log output (one line per cron run) with:

```bash
docker logs -f shelly-idmpump
```

`image.sh` builds and pushes a multi-arch image named
`docker.io/robertdiers/goodweidm:latest` (the name is kept from the former
Goodwe based version). If the container cannot reach the LAN devices, run it
with `--network host` in addition to the options above.

## Notes

* The Shelly topic must be `status/em:0` (instantaneous power, about 1 msg/s).
  `status/emdata:0` only contains energy counters and is not usable here.
* `total_act_power` is negative for feed-in. It is averaged over 10 messages,
  then rounded to 100 W steps. The iDM register is only written when the value
  changes.
