import time
import datetime
from urllib.parse import urljoin

from scripts.support import logger
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright._impl._errors import Error as PlaywrightError

def date_convert(time_str:str)->datetime:
    # _.strftime("%a, %d %b %y %H:%M:%S %z") #To verify correct converstion
    # dateOb = datetime.datetime.strptime(time_str, "%a, %d %b %Y %H:%M:%S %Z")
    dateOb = datetime.datetime.strptime(time_str, "%B %d, %Y")
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

    #Set the outer loop over each card returned. 
    for child in result:
        article = NewArticle()
        article.id = child.find("a").get("data-wf-cms-context", default_val)
        #If no ID found, move along!
        if not article.id: 
            logger.warning("Article missing ID")
            continue

        # Time of pull
        article.pull_date = time.strftime("%m-%d-%Y_%H-%M-%S")
        
        # grab creator
        article.creator = "www.boundless.com"

        # Grab the author
        article.author = "www.boundless.com"
        
        # Assign category
        article.category = cat
        
        # Assign source
        article.source = source

        #grab the title
        article.title = child.find("div", class_="heading-style-h7-2").text.strip()
        
        # grab the url and resolve relative paths against the source domain
        raw_link = child.find("a").get("href", default_val)
        article.link = urljoin(source, raw_link) if raw_link else default_val

        article.description = child.find("div", class_="text-size-body3-4 text-style-2lines").text.strip()
        
        #Not available either without digesting the downstream link
        article.pub_date = date_convert(child.find("div", {"fs-list-fieldtype":"date"}).text.strip())

        articles.append(article)
    
    return articles

def get_html(url: str, retries:int = 3, delay:int = 5):
    browser = None
    for attempt in range(retries):
        try:
            with sync_playwright() as p:
                logger.debug("Playwright launched")
                browser = p.chromium.launch(headless=True)
                logger.debug("Browser launched")
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
                logger.debug("Context created")
                page = context.new_page()
                logger.debug(f"Navigating to {url}")
                response = page.goto(url)

                if response.status == 403:
                    logger.warning(f"Attempt {attempt + 1} - 403 Forbidden. Retrying in {delay} seconds.")
                    time.sleep(delay)
                    delay *= 2
                    continue

                if response.status != 200:
                    logger.warning(f"Status code: {response.status}")
                    logger.warning(f"Reason: {response.status_text}")
                    return None

                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)

                page.wait_for_selector(".w-dyn-item", timeout=15000)
                html = page.content()
                logger.info("HTML retrieved")
                return html

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} - Error: {e}")
            if attempt + 1 == retries:
                return None
            time.sleep(delay)
            delay *= 2
        finally:
            if browser: #check if the browser object exists.
                try:
                    browser.close()
                    logger.debug("Browser closed")
                except PlaywrightError as pe: #Catch the playwright error specifically.
                    logger.warning(f"Error closing browser (PlaywrightError): {pe}")
                except Exception as close_error:
                    logger.warning(f"Error closing browser: {close_error}")
                
    return None

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
        "Boundless Blog"  :"https://www.boundless.com/blog-topics/immigration-news/",
        # "Boundless Weekly":"https://www.boundless.com/blog-topics/boundless-weekly-immigration-news/"
    }
    new_articles = []
    url = feeds.get(cat)
    try:
        response = get_html(url)
    except Exception as e:            
        logger.warning(f"Error {e}")
        return None
    
    #Parse the XML
    if response:
        bs4ob = BeautifulSoup(response, features="lxml")

        #Find all records (item CSS)
        results = bs4ob.find_all("div", {"role":"listitem"}, class_="cards-collection-item w-dyn-item")
        if results:
            new_articles = get_articles(results, cat, source, NewArticle)
            logger.info(f'{len(new_articles)} articles returned from {source}')
            return new_articles
    else:
        logger.warning(f"No articles returned on {source} / {cat}.  Moving to next feed")
