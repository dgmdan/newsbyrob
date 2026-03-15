# News by Rob

[![Python ->3.11](https://img.shields.io/badge/Python-%3E3.11-blue)](https://www.python.org/)

## Purpose
A dear friend of my fiancée, Rob, used to curate his own email listings of the latest shifts in U.S. immigration law. When he passed, I built this project so that the same news could keep circulating in his memory. The scraper aggregates RSS feeds across multiple government and advocacy sites, stores every article in a SQLite database, and still emails you whenever new content is discovered. The Django web layer now lets you browse the accumulated links, see what tags were applied, and filter the roster of stories without opening an inbox.

## Requirements
- Python 3.11+
- All dependencies listed in `requirements.txt` (Django 5.2.7 is bundled with the rest).

## Cloning and setting up the environment
Open a terminal and run the following (adjust the directory path as needed):

```bash
$ git clone https://github.com/Landcruiser87/newsbyrob.git
$ cd newsbyrob
$ python -m venv .news_venv
$ source .news_venv/bin/activate  # On Windows: .news_venv\\Scripts\\activate.bat
```

Upgrade `pip`/`setuptools` and confirm you only see the base packages:

```bash
$ pip install --upgrade pip setuptools
$ pip list  # Expect just pip/setuptools in a fresh venv
```

Now install the project dependencies:

```bash
$ pip install -r requirements.txt
```

## Directory and secret setup
```bash
$ mkdir -p data/logs
$ mkdir -p secret
```

Inside `secret/login.txt`, place three colon-separated values, one per line:

1. `username:your.email@gmail.com`
2. `password:app-specific-password`
3. `recipients:you@example.com,them@example.com`

The scraper still relies on Gmail SMTP and the same `support.send_email_update` helper, so keep that file on disk and guard it with strict permissions.

## Running the scraper and web UI
1. Let Django prepare the SQLite schema:
   ```bash
   $ python manage.py migrate
   ```
2. Scrape the feeds once, populate the database, and trigger the familiar notification email:
   ```bash
   $ python manage.py collect_news
   ```
   This command reuses the RSS/Playwright modules under `scripts/`, stores every item in `db.sqlite3`, updates `data/im_updates.json`, and keeps sending the same emails you got before.
3. Start the development server:
   ```bash
   $ python manage.py runserver
   ```
4. Visit `http://127.0.0.1:8000/` to browse collected articles. Use the tag filters at the top of the page to narrow results, and click any headline to jump to the original story. The UI is backed by tags derived from the original category names and keywords, so you can also filter on sites or curated terms.

Want to manage the records via the admin? Create a superuser (if you haven’t already):

```bash
$ python manage.py createsuperuser
```

## Data layout
- `db.sqlite3` holds the new Django models (`Article` and `Tag`).
- `data/im_updates.json` is rewritten every time `collect_news` runs and mirrors the historical structure that the old CLI used.
- Logs are written to `data/logs/<timestamp>.log`.
- The `secret/login.txt` file is persisted but ignored by Git (`.gitignore` already covers `secret/`).

## Sites scraped
- Aggregate news data from:
  - [Boundless](https://www.boundless.com)
  - [USCIS](https://www.uscis.gov/news/rss-feed/59144)
  - [DOS](https://travel.state.gov/_res/rss/TAsTWs.xml#.html)
  - [ICE](https://www.ice.gov/rss)
  - [Google News](https://news.google.com/rss)
  - [AILA](https://aila.org)

- Sunsetted feeds:
  - [CBP](https://www.cbp.gov/rss)

## CLI
The original script is still available under `scripts/main.py`. You can run it via `python -m scripts.main` if you need the old progress bar behavior, but picture it as another way to feed `data/im_updates.json`. The source of truth is now the SQLite-backed Django web app.

## Running tests
Run Django’s test suite with:

```bash
$ python manage.py test newsfeed
```

If you ever add tests elsewhere, just point the command at that app (e.g., `python manage.py test newsfeed.models`). The command uses the same SQLite settings, so it works inside your activated virtualenv.
