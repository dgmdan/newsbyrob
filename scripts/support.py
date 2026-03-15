import os
import time
import json
import shutil
import datetime
import numpy as np
import json
from os.path import exists
import logging

#Progress bar fun
from rich.progress import (
    Progress,
    BarColumn,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TimeElapsedColumn
)
from rich.logging import RichHandler
from rich.console import Console
from pathlib import Path, PurePath

################################# Emailing Funcs ####################################

#FUNCTION URL Format
def urlformat(urls: list) -> str:
    """
    Formats the list of URLs into an HTML list with site and category printed once per group,
    followed by a list of titles as links.

    Args:
        urls (list): List of new listings found, where each item is a tuple:
                     (link, site, category, title).

    Returns:
        str: HTML formatted string for emailing.
    """

    if not urls:
        return "<p>No new links found.</p>"

    links_html = ""
    prev_site_cat = None

    for link, site, cat, title in urls:
        current_site_cat = (site, cat)
        if current_site_cat != prev_site_cat:
            if prev_site_cat is not None:
                links_html += "</ol>\n" + "-" * 45 + "\n" 
            links_html += f"<br><i><b>{site} - {cat}</b></i>\n<ol>"
            prev_site_cat = current_site_cat
        links_html += f"<li><a href='{link}'>{title}</a></li>"

    links_html += "</ol>" # close the final list.
    return links_html

#FUNCTION Send email update
def send_email_update(urls:str):
    """[Function for sending an email.  Formats the url list into a basic email with said list]

    Args:
        url (str): [url of the news story]

    Returns:
        [None]: [Just sends the email.  Doesn't return anything]
    """	
    import smtplib, ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    def inputdatlink(urls:str):
        html = """
        <html>
            <body>
                <p>Helloooooooooooo,<br>
                Rob wanted you to look at these new articles!<br>
                """ + urls + """
                </p>
            </body>
        </html>
        """
        return html

    def _parse_field(line: str, default: str = "") -> str:
        parts = line.split(":", 1)
        return parts[1].strip() if len(parts) == 2 else parts[0].strip()

    try:
        with open('./secret/login.txt') as login_file:
            login = [line.strip() for line in login_file.read().splitlines() if line.strip()]
    except FileNotFoundError:
        logger.warning("secret/login.txt not found; skipping email delivery.")
        return False

    if len(login) < 3:
        logger.warning("secret/login.txt must contain username, password, and recipients lines; skipping email delivery.")
        return False

    sender_email = _parse_field(login[0])
    password = _parse_field(login[1])
    recipients = _parse_field(login[2]).split(",")
    receiver_email = [email.strip() for email in recipients if email.strip()]

    if not sender_email or not password or not receiver_email:
        logger.warning("Incomplete login details found; skipping email delivery.")
        return False

    # Establish a secure session with gmail's outgoing SMTP server using your gmail account
    smtp_server = "smtp.gmail.com"
    port = 465 #used for a secure connection with SSL encryption#  #587 is the newer ver with TLS
    html = inputdatlink(urls)

    message = MIMEMultipart("alternative")
    if "Forms Updates" in urls:
        message["Subject"] = "FORMS FORMS FORMS!!! -> Immigration updates from Rob!"
    else:
        message["Subject"] = "Immigration Updates ala Rob!"
    message["From"] = sender_email
    message["To"] = ", ".join(receiver_email)   #multiple emails need to be comma separated strings
    attachment = MIMEText(html, "html")
    message.attach(attachment)
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)		
        server.sendmail(sender_email, receiver_email, message.as_string())
    return True

################################# Timing Func ####################################
def log_time(fn):
    """Decorator timing function.  Accepts any function and returns a logging
    statement with the amount of time it took to run. DJ, I use this code everywhere still.  Thank you bud!

    Args:
        fn (function): Input function you want to time
    """	
    def inner(*args, **kwargs):
        tnow = time.time()
        out = fn(*args, **kwargs)
        te = time.time()
        took = round(te - tnow, 2)
        if took <= 60:
            logging.warning(f"{fn.__name__} ran in {took:.2f}s")
        elif took <= 3600:
            logging.warning(f"{fn.__name__} ran in {(took)/60:.2f}m")		
        else:
            logging.warning(f"{fn.__name__} ran in {(took)/3600:.2f}h")
        return out
    return inner

################################# Logger functions ####################################
#FUNCTION Logging Futures
def get_file_handler(log_dir:Path)->logging.FileHandler:
    """Assigns the saved file logger format and location to be saved

    Args:
        log_dir (Path): Path to where you want the log saved

    Returns:
        filehandler(handler): This will handle the logger's format and file management
    """	
    log_format = "%(asctime)s|%(levelname)-8s|%(lineno)-3d|%(funcName)-14s|%(message)s|" 
    file_handler = logging.FileHandler(log_dir)
    file_handler.setFormatter(logging.Formatter(log_format, "%m-%d-%Y %H:%M:%S"))
    return file_handler

def get_rich_handler(console:Console)-> RichHandler:
    """Assigns the rich format that prints out to your terminal

    Args:
        console (Console): Reference to your terminal

    Returns:
        rh(RichHandler): This will format your terminal output
    """
    rich_format = "|%(funcName)-14s|%(message)s "
    rh = RichHandler(console=console)
    rh.setFormatter(logging.Formatter(rich_format))
    return rh

def get_logger(console:Console, log_dir:Path)->logging.Logger:
    """Loads logger instance.  When given a path and access to the terminal output.  The logger will save a log of all records, as well as print it out to your terminal. Propogate set to False assigns all captured log messages to both handlers.

    Args:
        log_dir (Path): Path you want the logs saved
        console (Console): Reference to your terminal

    Returns:
        logger: Returns custom logger object.  Info level reporting with a file handler and rich handler to properly terminal print
    """	
    #Load logger and set basic level
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    #Load file handler for how to format the log file.
    file_handler = get_file_handler(log_dir)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    rich_handler = get_rich_handler(console)
    rich_handler.setLevel(logging.INFO)
    logger.addHandler(rich_handler)
    logger.propagate = False
    return logger

#FUNCTION get time
def get_time():
    """Function for getting current time

    Returns:
        t_adjusted (str): String of current time
    """
    current_t_s = datetime.datetime.now().strftime("%m-%d-%Y-%H-%M-%S")
    current_t = datetime.datetime.strptime(current_t_s, "%m-%d-%Y-%H-%M-%S")
    return current_t

def move_log():
    ts = datetime.datetime.strptime(start_time, "%m-%d-%Y_%H-%M-%S")
    year = ts.year
    month = ts.month
    destination_path = PurePath(
        Path(f"./data/logs"),
        Path(f"{year}"),
        Path(f"{month}")
    )
    if not exists(destination_path):
        os.makedirs(destination_path)
    shutil.move(log_dir, destination_path)


################################# Global Vars ####################################
start_time = get_time().strftime("%m-%d-%Y_%H-%M-%S")
console = Console(color_system="auto", stderr=True, width=200)
log_dir = PurePath(Path.cwd(), Path(f'./data/logs/{start_time}.log'))
logger = get_logger(log_dir=log_dir, console=console)
chrome_version = np.random.randint(130, 142)

#Additional USER agents
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2919.83 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:101.0) Gecko/20100101 Firefox/101.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:99.0) Gecko/20100101 Firefox/99.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A',
    'Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5355d Safari/8536.25',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582',
    f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36',
    'Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16.2',
    'Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16',
    'Opera/9.80 (Macintosh; Intel Mac OS X 10.14.1) Presto/2.12.388 Version/12.16'
]


#CLASS Numpy encoder
class NumpyArrayEncoder(json.JSONEncoder):
    """Custom numpy JSON Encoder.  Takes in any type from an array and formats it to something that can be JSON serialized.
    Source Code found here.  https://pynative.com/python-serialize-numpy-ndarray-into-json/
    Args:
        json (object): Json serialized format
    """	
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, str):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            return datetime.datetime.strftime(obj, "%m-%d-%Y_%H-%M-%S")
        else:
            return super(NumpyArrayEncoder, self).default(obj)
        
################################# Rich Spinner Control ####################################

#FUNCTION sleep progbar
def mainspinner(console:Console, totalstops:int):
    """Load a rich Progress bar for however many categories that will be searched

    Args:
        console (Console): reference to the terminal
        totalstops (int): Amount of categories searched

    Returns:
        my_progress_bar (Progress): Progress bar for tracking overall progress
        jobtask (int): Job id for the main scraping job
    """    
    my_progress_bar = Progress(
        TextColumn("{task.description}"),
        SpinnerColumn("pong"),
        BarColumn(),
        TextColumn("*"),
        "time elapsed:",
        TextColumn("*"),
        TimeElapsedColumn(),
        TextColumn("*"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        transient=True,
        console=console,
        refresh_per_second=10
    )
    jobtask = my_progress_bar.add_task("[green]Checking RSS Feeds", total=totalstops + 1)
    return my_progress_bar, jobtask

def add_spin_subt(prog:Progress, msg:str, howmanysleeps:int):
    """Adds a secondary job to the main progress bar that will take a nap at each of the servers that are visited

    Args:
        prog (Progress): Main progress bar
        msg (str): Message to update secondary progress bar
        howmanysleeps (int): How long to let the timer sleep
    """
    #Add secondary task to progbar
    liljob = prog.add_task(f"[magenta]{msg}", total = howmanysleeps)
    #Run job for random sleeps
    for _ in range(howmanysleeps):
        time.sleep(1)
        prog.update(liljob, advance=1)
    #Hide secondary progress bar
    prog.update(liljob, visible=False)

################################# Date/Load/Save Funcs ####################################

#FUNCTION Save Data
def save_data(jsond:dict):
    """This function saves the dictionary to a JSON file. 

    Args:
        jsond (dict): Main dictionary container
    """    
    # Sort by published date. U Have to sort it by string because some of the
    # datetimes stored are timezone aware, some are not therefore you have to
    # turn it into a Y-M-D string then split it on the ("-") so you can first 
    # sort by year, then month, then day.
    sorted_dict = dict(sorted(jsond.items(), key=lambda x:datetime.datetime.strftime(x[1]["pub_date"], "%Y-%m-%d").split("-"), reverse=True))
    out_json = json.dumps(sorted_dict, indent=2, cls=NumpyArrayEncoder)
    with open("./data/im_updates.json", "w") as out_f:
        out_f.write(out_json)

#FUNCTION Convert Date
def date_convert(str_time:str)->datetime:
    """When Loading the historical data.  Turn all the published dates into datetime objects so they can be sorted in the save routine. 

    Args:
        str_time (str): Converts a string to a datetime object 

    Returns:
        dateOb (datetime): str_time as a datetime object
    """    
    dateOb = datetime.datetime.strptime(str_time,'%m-%d-%Y_%H-%M-%S')
    return dateOb

#FUNCTION Load Historical
def load_historical(fp:str)->json:
    """Loads the saved JSON of previously scraped data.

    Args:
        fp (str): File path for saving

    Returns:
        jsondata (JSON): dictionary version of saved JSON
    """    
    if exists(fp):
        with open(fp, "r") as f:
            jsondata = json.loads(f.read())
            #Quick format the pub date strings back to dates. 
            #We need them as dates to sort them on the save above.
            for key in jsondata.keys():
                jsondata[key]["pub_date"] = date_convert(jsondata[key]["pub_date"])
            return jsondata	
