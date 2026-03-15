import time
import datetime
# import requests
import curl_cffi as cf
from scripts.support import logger, USER_AGENTS, chrome_version
from bs4 import BeautifulSoup

def date_convert(time_str:str)->datetime:
    # _.strftime("%a, %d %b %y %H:%M:%S %z") #To verify correct converstion
    dateOb = datetime.datetime.strptime(time_str, "%a, %d %b %y %H:%M:%S %z")
    return dateOb

def get_articles(results:BeautifulSoup, cat:str, source:str, NewArticle)->list:
    """[Ingest XML of summary page for articles info]

    Args:
        result (BeautifulSoup object): html of apartments page
        cat (str): category being searched
        source (str): source website
        logger (logging.logger): logger for Kenny loggin
        NewArticle (dataclass) : Dataclass object for NewsArticle

    Returns:
        articles (list): [List of NewArticle objects]
    """

    articles = []
    #Set the outer loop over each card returned. 
    for card in results:
        article = NewArticle()
        # Time of pull
        article.pull_date = time.strftime("%m-%d-%Y_%H-%M-%S")
        
        for row in card.contents:
            rname = row.name
            if row == "\n":
                continue
            match rname:
                case "title":
                    article.title = row.text
                case "link":
                    article.link = row.text
                case "description":
                    article.description = row.text
                case "pubDate":
                    article.pub_date = date_convert(row.text)
                case "creator":
                    article.creator = row.text
                case "guid":
                    article.id = row.text
        # Assign category
        article.category = cat
        # Assign source
        article.source = source
        articles.append(article)

    return articles

def ingest_xml(cat:str, source:str, NewArticle)->list:
    """[Outer scraping function to set up request pulls]

    Args:
        cat (str): category of site to be searched
        source (str): RSS feed origin
        NewArticle (dataclass): Custom data object

    Returns:
        new_articles (list): List of dataclass objects
    """
    feeds = {
        "Fact Sheets"         :"https://www.uscis.gov/news/rss-feed/93166",
        "News Releases"       :"https://www.uscis.gov/news/rss-feed/23269",
        "Stakeholder Messages":"https://www.uscis.gov/news/rss-feed/97790", 
        "Alerts"              :"https://www.uscis.gov/news/rss-feed/22984",
        "Forms Updates"       :"https://www.uscis.gov/forms/forms-updates/rss-feed"
    }
    new_articles = []
    url = feeds.get(cat)
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Content-Type': 'text/html,application/xhtml+xml,application/xml',
        'Referer':'https://www.google.com/',
        # 'referer': url,
        'Sec-Ch-Ua': f'"Not)A;Brand";v="99", "Google Chrome";v="{chrome_version}", "Chromium";v="{chrome_version}"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': USER_AGENTS[9],
        'Origin':source,
    }

    try:
        # response = requests.get(url, headers=headers)
        with cf.requests.Session(impersonate="chrome") as session:
            response = session.get(url=url,headers=headers, impersonate="chrome", timeout=10)
            #Just in case we piss someone off
            if response.status_code != 200:
                # If there's an error, log it and return no data for that site
                logger.warning(f'Status code: {response.status_code}')
                logger.warning(f'Reason: {response.reason}')
                return None
            
    except Exception as e:            
        logger.warning(f"Error {e}")
        return None
    
    #Parse the XML
    bs4ob = BeautifulSoup(response.text, features="xml")

    #Find all records (item CSS)
    results = bs4ob.find_all("item")
    if results:
        new_articles = get_articles(results, cat, source, NewArticle)
        logger.info(f'{len(new_articles)} articles returned from {source}')
        return new_articles
            
    else:
        logger.warning(f"No articles returned on {source} / {cat}.  Moving to next feed")
