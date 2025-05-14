# Zignal

Ett Django-baserat projekt för intelligent kommunikation och datahantering.

## Installation

1. Klona projektet:
```bash
git clone https://github.com/jonasulveseth/zignal.git
cd zignal
```

2. Skapa en virtuell miljö:
```bash
python -m venv venv
source venv/bin/activate  # På Windows: venv\Scripts\activate
```

3. Installera beroenden:
```bash
pip install -r requirements.txt
```

4. Konfigurera miljövariabler:
Kopiera `.env.example` till `.env` och uppdatera värdena.

5. Kör migrationer:
```bash
python manage.py migrate
```

6. Starta utvecklingsservern:
```bash
python manage.py runserver
```

## Utveckling

Detta projekt använder Python 3.13 och Django. Alla bidrag bör följa PEP 8-riktlinjerna. 