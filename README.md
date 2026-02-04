# FollowMe – Treningsapp (lokal prototype)

## Hva som er laget
Denne prototypen dekker kravene med en enkel, spillbasert web-app:
- Logge km og type trening
- Reise mellom destinasjoner i verden
- Låse opp fakta og bilder
- Poeng/level-system og achievements
- Venneliste og high score
- Rapporter (uke, måned, år)
- Brukeradministrasjon (roller)
- Avatar og oppgraderingsfølelse via nivåer

## Kjør lokalt
1. Opprett virtuelt miljø (valgfritt, men anbefalt)
2. Installer avhengigheter
3. Start appen

```bash
cd followme_app
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Åpne `http://127.0.0.1:5000` i nettleseren.

## Deploy til Render (gratis)
1. Push prosjektet til GitHub.
2. Opprett en **Web Service** på Render og koble repoet.
3. Bruk disse kommandoene:
   - Build Command:
     ```bash
     pip install -r followme_app/requirements.txt
     ```
   - Start Command:
     ```bash
     gunicorn followme_app.app:app
     ```

### Miljøvariabler (anbefalt)
Legg til disse i Render → **Environment**:
- `SECRET_KEY` = en lang tilfeldig streng
- `DATABASE_URL` = valgfritt (brukes hvis du har ekstern DB)

**Merk:** Gratis‑planen har begrensninger (idle sleep og ingen persistent disk). SQLite‑data kan gå tapt ved redeploy.

## Testdata
Ved første oppstart opprettes:
- Standard destinasjoner
- Achievements
- Eksempel på challenges

## Roller
Alle nye brukere blir opprettet som `user`. For å lage en admin:
- Åpne databasen i SQLite og sett `role` til `admin` på ønsket bruker.

## Struktur
- `app.py` – Flask app og datamodeller
- `templates/` – HTML
- `static/css/style.css` – styling
- `followme.db` – SQLite database

## Scrum – 6 faser (forslag)
1. **Sprint 1**: Innlogging, bruker, loggføring av økter
2. **Sprint 2**: Destinasjoner + visning av fremgang
3. **Sprint 3**: Achievements + nivåsystem
4. **Sprint 4**: Venner + high score
5. **Sprint 5**: Rapporter + adminvisning
6. **Sprint 6**: Polering, test mot krav, opplæringsmateriell

Mellom hver fase bør det gjøres:
- Oppsummering
- Planlegging av neste fase
- Kjøring av prototypen
- Verifisering mot krav
