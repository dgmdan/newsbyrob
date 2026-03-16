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

## Environment configuration

- `DJANGO_ENV` defaults to `development` and keeps the app running against `db.sqlite3` inside the project root.
- Set `DJANGO_ENV=production` in hosted deployments along with a Postgres URI stored in `DATABASE_URL` (for example `postgresql://user:pass@db.example.com:5432/newsbyrob`). The settings loader requires `DATABASE_URL` and validates that it includes a database name.
- Override `ALLOWED_HOSTS` (comma separated) when your production hostnames differ from `localhost`.
- On DigitalOcean Managed Postgres instances, run `GRANT ALL PRIVILEGES ON SCHEMA public TO <your role>;` (substituting the username in `DATABASE_URL`) before running migrations so the role can create tables. If you ever recreate the DB, rerun the grant before your next deploy.
- If you want the scraper to run daily on App Platform, add a scheduled Job component that runs `python manage.py collect_news` with cron `0 20 * * *` (set the job timezone to America/New_York for 4 PM Eastern) and share the same secrets as the web service.
- Production deployments also rely on `python manage.py collectstatic` to copy static assets into `STATIC_ROOT`, and WhiteNoise serves that bundle without a proxy like S3 or Cloudflare. Do **not** set `DISABLE_COLLECTSTATIC=1` on Heroku/App Platform so the release script can collect the favicon and other static files WhiteNoise exposes.

## Running the scraper and web UI
1. Let Django prepare the SQLite schema:
   ```bash
   $ python manage.py migrate
   ```
2. Scrape the feeds once, populate the database, and trigger the familiar notification email:
   ```bash
   $ python manage.py collect_news
   ```
   This command reuses the RSS/Playwright modules under `scripts/`, stores every item in `db.sqlite3`, and emails the new links.
3. Start the development server:
   ```bash
   $ python manage.py runserver
   ```
4. Visit `http://127.0.0.1:8000/` to browse collected articles. Use the tag filters at the top of the page to narrow results, and click any headline to jump to the original story. The UI is backed by tags derived from the original category names and keywords, so you can also filter on sites or curated terms.
5. Use the new search box alongside the filters to look for an exact word or phrase inside article titles and summaries; the search prefers whole-word (or whole-phrase) matches and keeps the current tag filter in place.
6. An RSS feed of the 50 most recent articles is available at `/feed/`; subscribe with any reader to receive the aggregated immigration news updates.

Want to manage the records via the admin? Create a superuser (if you haven’t already):

```bash
$ python manage.py createsuperuser
```

## Data layout
- `db.sqlite3` holds the new Django models (`Article` and `Tag`).
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

## Running tests
Run Django’s test suite with:

```bash
$ python manage.py test newsfeed
```

If you ever add tests elsewhere, just point the command at that app (e.g., `python manage.py test newsfeed.models`). The command uses the same SQLite settings, so it works inside your activated virtualenv.

## Maintenance helpers
- `python manage.py fix_future_pub_dates [--limit N]` revisits any `Article` records where `pub_date` is still ahead of the current time, scrapes the original link for a corrected published timestamp, and rewrites the stored date (falling back to the run time when the scrape fails).
