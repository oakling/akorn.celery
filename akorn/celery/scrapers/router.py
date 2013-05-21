import sys, os
import urllib2
import cookielib
import pkgutil
import urlparse
from akorn.scrapers.journals import utils
from akorn.scrapers.journals.utils import RedirectHandler, Ignore401Handler
from akorn.scrapers.journals.utils import get_scrapers_folder
from akorn.celery.couch import db_store, db_journals, db_scrapers

def resolve_doi(doi):
  cookiejar = cookielib.CookieJar()
  req = urllib2.Request('http://dx.doi.org/' + doi, headers=utils.headers)
  urls = []
  opener = urllib2.build_opener(Ignore401Handler(), RedirectHandler(urls),
                                urllib2.HTTPCookieProcessor(cookiejar))
  response = opener.open(req)

  return response.geturl()

def resolve_url(url):
  cookiejar = cookielib.CookieJar()
  req = urllib2.Request(url, headers=utils.headers)
  urls = []
  opener = urllib2.build_opener(Ignore401Handler(), RedirectHandler(urls),
                                urllib2.HTTPCookieProcessor(cookiejar))
  response = opener.open(req)

  return response.geturl()

def resolve_journal(alias):
  matches = db_journals.view('index/aliases', key=alias).rows

  if matches:
    journal_id = matches[0].id
    #cache[journal_name] = journal_id
  else:
    journal_id = None

  return journal_id

def load_module(module_path):
    __import__(module_path)
    return sys.modules[module_path]

def discover_scrapers():
  """
    Use pkgutil to find scrapers in this module. Build a list of scrapers and which domains they map to.
  """

  scraper_modules = []
  scraper_domain_map = {}

  d = get_scrapers_folder()

  for module_importer, name, ispkg in pkgutil.iter_modules([d,]):
    if not name.startswith('scrape_'):
      continue
    module = module_importer.find_module(name).load_module(name)

    scraper_modules.append(module)

    if hasattr(module, 'SCRAPER_DOMAINS'):
      for domain in module.SCRAPER_DOMAINS:
        scraper_domain_map[domain] = module

  return (scraper_modules, scraper_domain_map)

scraper_modules, scraper_domain_map = discover_scrapers()

def get_domain(url):
  url_parsed = urlparse.urlparse(url)
  return url_parsed.netloc

def resolve_scraper(url):
  # Do it by domain for now. This might not always work, a full url prefix might be needed, but this is cheaper.

  domain = get_domain(url)

  if domain in scraper_domain_map:
    scraper_module = scraper_domain_map[domain]
  else:
    url = resolve_url(url)
    domain = get_domain(url)
    if domain in scraper_domain_map:
      scraper_module = scraper_domain_map[domain]
    else:
      scraper_module = load_module('scrape_meta_tags')

  module_path = "akorn.scrapers.journals." + scraper_module.__name__

  return module_path, scraper_module

def resolve_and_scrape(url):
  """Scrape URL; handle any errors; return dictionary to be inserted
  into store."""

  module_path = "Unable to resolve"
  article={}
  try:
    module_path, scraper_module = resolve_scraper(url)
    article = scraper_module.scrape(url)

    if 'journal' in article:
      journal_name = article['journal']
    elif 'citation' in article and 'journal' in article['citation']:
      journal_name = article['citation']['journal']
    elif 'categories' in article and 'arxiv' in article['categories']:
      journal_name = 'arxiv:' + article['categories']['arxiv'][0]
    else:
      journal_name = None

    if journal_name:
      journal_id = resolve_journal(journal_name)

      if journal_id:
        article['journal_id'] = journal_id
  except Exception, e:
    article['exception'] = str(type(e))
    article['error_text'] = str(e)
    article['source_urls'] = [url]
    article['rescrape'] = True
    
  article['scraper_module'] = module_path 

  return article
