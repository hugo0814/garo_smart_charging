# Garo smart charging

Styr en Garo GLB-laddbox så att elbilen laddar under nattens billigaste timmar.
Priserna hämtas från [elprisetjustnu.se](https://www.elprisetjustnu.se/).

- Väljer de N billigaste timmarna mellan 20:00 och 07:00 varje natt och skriver dem till laddboxens schema.
- Morgondagens priser hämtas när de publiceras (efter kl 13) och schemat uppdateras då.
- "Ladda nu" sätter laddboxen på ALWAYS_ON i 16 timmar. Pågår laddning när tiden gått ut väntar den en timme till.
- Webbsidan är ren HTML utan JavaScript-bibliotek och laddas om varje minut, så den fungerar på enkla skärmar och gamla enheter.

## Konfiguration

Miljövariabler (se `.env.example`):

| Variabel | Beskrivning | Standard |
|---|---|---|
| `GARO_URL` | Laddboxens adress, t.ex. `http://<ip>:8080` | – |
| `PRICE_AREA` | Elområde `SE1`–`SE4` | `SE3` |
| `CHARGING_HOURS` | Laddtimmar per natt vid start | `7` |
| `SECRET_KEY` | Nyckel för sessionsmeddelanden | slumpas vid start |

## Köra

Med Docker:

```bash
cp .env.example .env
docker compose up -d --build
```

Utan Docker:

```bash
pip install -r requirements.txt
GARO_URL=http://<ip>:8080 python app.py
```

Sidan finns sedan på `http://<server>:5000`.
