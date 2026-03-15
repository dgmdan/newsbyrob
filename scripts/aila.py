import time
import datetime
import requests
import numpy as np
from scripts.support import logger
from bs4 import BeautifulSoup

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
    feeds = {
        "AILA Daily News Update":f"https://www.aila.org/library/daily-immigration-news-clips-{month}-{day}-{year}",
        #"Aaila Blog"           :f"https://www.aila.org/library/daily-immigration-news-clips-march-6-2025",
    }
    # 

    new_articles = []
    url = feeds.get(cat)
    chrome_version = np.random.randint(120, 132)
    headers = {
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': f'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Mobile Safari/537.36',
        'sec-ch-ua': f'"Not)A;Brand";v="99", "Google Chrome";v={chrome_version}, "Chromium";v={chrome_version}',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'referer': url,
        'origin':source,
        'Content-Type': 'text/html,application/xhtml+xml,application/xml'
    }
    try:
        response = requests.get(url, headers=headers)
    
        if response.status_code != 200:
            logger.warning(f'Status code: {response.status_code}')
            logger.warning(f'Reason: {response.reason}')
            logger.warning(f"Daily news not up yet for {source}.  Check again later")
            return None
    except Exception as e:            
        logger.warning(f"Error {e}")
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
