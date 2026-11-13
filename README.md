# Property Sale Planner

Flask app that shows Conservative / Realistic / Optimistic sale scenarios for a property,
the capital gains tax (including the proposed 1 July 2027 changes), a year-by-year table and chart.

Login: username `test`, password `test`.

## Run on your computer (optional)

    python -m venv .venv
    .venv\Scripts\activate        (Windows)   or   source .venv/bin/activate   (Mac/Linux)
    pip install -r requirements.txt
    python app.py

Then open http://127.0.0.1:5000

## Deploy on Render (free)

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Environment variable: `SECRET_KEY` = any long random text

## Files

- `app.py` - web pages and login
- `model.py` - sale price and capital gains tax calculations (edit rates here)
- `rental_model.py` - rental gearing and tax position
- `super_model.py` - superannuation projection
- `templates/`, `static/` - pages, styling, chart

Planning estimate only - not tax or financial advice.
