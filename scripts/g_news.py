import time
import datetime
import requests
from scripts.support import logger
from bs4 import BeautifulSoup

def date_convert(time_str:str)->datetime:
    # _.strftime("%a, %d %b %y %H:%M:%S %z") #To verify correct converstion
    dateOb = datetime.datetime.strptime(time_str, "%a, %d %b %Y %H:%M:%S %Z")
    return dateOb

def get_articles(results:BeautifulSoup, cat:str, source:str, NewArticle)->list:
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
                case "source url":
                    article.creator = row.text
                case "guid":
                    article.id = row.text
        # Assign category
        article.category = cat
        # Assign source
        article.source = source
        articles.append(article)
    
    return sorted(articles, key=lambda x:x.pub_date, reverse=True)[:5] #Only return top 5

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
        "US Immigration Changes":"https://news.google.com/rss/search?q=US+immigration+changes",
        "USCIS Updates"         :"https://news.google.com/rss/search?q=USCIS+updates",        
    }
    for feed in feeds.keys():
        new_articles = []
        url = feeds.get(feed)
        headers = {
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
            'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="122", "Chromium";v="122"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'referer': url,
            'origin':source,
            'Content-Type': 'text/html,application/xhtml+xml,application/xml'
        }
        try:
            response = requests.get(url, headers=headers)
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
            logger.info(f'{len(new_articles)} articles returned from {source} searching {cat}')
            return new_articles
                
        else:
            logger.warning(f"No articles returned on {source} / {cat}.  Moving to next feed")
