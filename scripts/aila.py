import time
import datetime
import re
import random
from urllib.parse import urljoin

import requests
from scripts.support import logger
from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:148.0) Gecko/20100101 Firefox/148.0"
RECENT_POSTINGS_URL = "https://www.aila.org/recent-postings"
RECENT_POSTINGS_LABEL = "Daily Immigration News Clips"
RECENT_POSTINGS_DATE = re.compile(
    rf"{RECENT_POSTINGS_LABEL}\s*[-–—]\s*(?P<date>[A-Za-z]+\s+\d{{1,2}},\s*\d{{4}})",
)

def date_convert(time_str:str)->datetime:
    dateOb = datetime.datetime.strptime(time_str, "%a, %d %b %Y %H:%M:%S %Z")
    return dateOb

def get_articles(result:BeautifulSoup, cat:str, source:str, NewArticle)->list:
    """[Ingest XML of summary page for articles info]

    Args:
        result (BeautifulSoup object): html of apartments page
        cat (str): category being searched
        source (str): source website
        NewArticle (dataclass) : Dataclass object for NewsArticle

    Returns:
        articles (list): [List of NewArticle objects]
    """

    articles = []
    default_val = None

    #BUG - So.... This time they decided to next multiple articles underneath a p tag????
        #Not sure if that was a mistake as i've never seen them do that.  
        #Keep an eye on the format and see if that shifts. 
        #https://www.aila.org/library/daily-immigration-news-clips-
        
    #Set the outer loop over each card returned. 
    for child in result.contents:
        article = NewArticle()
        #Description not available.  Putting regional info here
        if child.name == "h2" or child.name == "h3" or child.name == "h4":
            descript = child.find("em").text
            continue
        if not child.name or child.text == "\xa0":
            continue

        # Time of pull
        article.pull_date = time.strftime("%m-%d-%Y_%H-%M-%S")
        
        # grab creator
        if child.find("em"):
            article.creator = child.find("em").text
        else:
            article.creator = ""

        # Grab the author
        if child.find("br"):
            article.author = child.text.split("\n")[1].strip("By ")
        else:
            article.author = ""
        # Assign category
        article.category = cat
        
        # Assign source
        article.source = source

        #Put section in description
        article.description = descript

        #grab the title
        if child.find("a"):
            article.title = article.description + " - " + article.creator + " - " + child.find("a").text
        else:
            logger.warning("No title found on article")
            continue
        #grab the url
        article.link = child.find("a").get("href", default_val)
        
        #assign id
        article.id = article.link

        #Not available either without digesting the downstream link
        article.pub_date = datetime.datetime.now()

        articles.append(article)
    
    return articles

def _parse_postings_date(text: str) -> datetime.date | None:
    match = RECENT_POSTINGS_DATE.search(text)
    if not match:
        return None
    date_text = match.group("date")
    try:
        return datetime.datetime.strptime(date_text, "%B %d, %Y").date()
    except ValueError:
        return None


def _resolve_latest_daily_news_link() -> str | None:
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    try:
        response = requests.get(RECENT_POSTINGS_URL, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as exc:
        logger.warning(f"Unable to read recent postings for AILA: {exc}")
        return None

    soup = BeautifulSoup(response.text, features="html.parser")
    anchors = soup.find_all("a", string=lambda text: RECENT_POSTINGS_LABEL in (text or ""))
    candidates: list[tuple[datetime.date | None, str]] = []
    for anchor in anchors:
        href = anchor.get("href")
        if not href:
            continue
        url = urljoin(RECENT_POSTINGS_URL, href)
        date = _parse_postings_date(anchor.get_text(" ", strip=True))
        candidates.append((date, url))

    if not candidates:
        logger.warning("Daily Immigration News Clips link not found on recent postings.")
        return None

    best_date = None
    best_url = None
    for parsed_date, url in candidates:
        if best_url is None:
            best_url = url
            best_date = parsed_date
            continue
        if parsed_date and (best_date is None or parsed_date > best_date):
            best_url = url
            best_date = parsed_date

    logger.debug(f"Resolved latest Daily Immigration News link: {best_url}")
    return best_url


def ingest_xml(cat:str, source:str, NewArticle)->list:
    """[Outer scraping function to set up request pulls]

    Args:
        cat (str): category of site to be searched
        source (str): RSS feed origin
        NewArticle (dataclass): Custom data object

    Returns:
        new_articles (list): List of dataclass objects
    """
    dt = datetime.datetime.now()
    day = dt.day
    weekend = dt.weekday() > 4
    if weekend:
        logger.info("AILA only posts on weekdays. No soup for you!")
        return None

    month = dt.strftime("%B").lower()
    year = dt.year
    fallback_url = f"https://www.aila.org/library/daily-immigration-news-clips-{month}-{day}-{year}"
    resolved_url = _resolve_latest_daily_news_link()
    url_candidates = []
    if resolved_url:
        url_candidates.append(resolved_url)
    if fallback_url not in url_candidates:
        url_candidates.append(fallback_url)

    new_articles = []
    response = None
    fetched_url = None
    for candidate in url_candidates:
        chrome_version = random.randint(120, 132)
        headers = {
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': f'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Mobile Safari/537.36',
            'sec-ch-ua': f'"Not)A;Brand";v="99", "Google Chrome";v={chrome_version}, "Chromium";v={chrome_version}',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'referer': candidate,
            'origin': source,
            'Content-Type': 'text/html,application/xhtml+xml,application/xml'
        }
        try:
            response = requests.get(candidate, headers=headers, timeout=10)
        except Exception as exc:
            logger.warning(f"Error fetching {candidate}: {exc}")
            response = None
        if not response:
            continue
        if response.status_code == 200:
            fetched_url = candidate
            break
        logger.warning(f'Status code: {response.status_code} fetching {candidate}')
        logger.warning(f'Reason: {response.reason}')

    if not response or response.status_code != 200:
        logger.warning(f"Daily news not up yet for {source}.  Check again later")
        return None

    #Parse the XML
    bs4ob = BeautifulSoup(response.text, features="lxml")

    #Find all records (item CSS)
    results = bs4ob.find("div", class_="typography text rte")
    if results:
        new_articles = get_articles(results, cat, source, NewArticle)
        logger.debug(f'{len(new_articles)} articles returned from {source}')
        return new_articles
            
    else:
        logger.info(f"No articles returned on {source} / {cat}.  Moving to next feed")

#Bex suggestions.  
#Anywway to filter specifically for chicago based immigration news. 
#Also wants to filter out asylum and removal updates.  Not sure how that might work. 

#root url
#https://www.aila.org/immigration-news
#
# Basic URl structure of searching postings
#https://www.aila.org/recent-postings?FromDate=2025-02-28&ToDate=2025-03-07&limit=50
