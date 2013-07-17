import urllib2
import cookielib
import urlparse
from akorn.scrapers import utils, scrapers
from akorn.celery.couch import db_store, db_journals, db_scrapers

# TODO This should be instantiated by the task creation code
scraper_factory = scrapers.Scrapers()

def resolve_doi(doi):
  cookiejar = cookielib.CookieJar()
  req = urllib2.Request('http://dx.doi.org/' + doi, headers=utils.headers)
  urls = []
  opener = urllib2.build_opener(utils.Ignore401Handler(), utils.RedirectHandler(urls),
                                urllib2.HTTPCookieProcessor(cookiejar))
  response = opener.open(req)

  return response.geturl()

def resolve_url(url):
  cookiejar = cookielib.CookieJar()
  req = urllib2.Request(url, headers=utils.headers)
  urls = []
  opener = urllib2.build_opener(utils.Ignore401Handler(), utils.RedirectHandler(urls),
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

def resolve_and_scrape(url):
  """Scrape URL; handle any errors; return dictionary to be inserted
  into store."""

  module_path = "Unable to resolve"
  article={}
  try:
    # lambda is used to make evaluation lazy, to avoid cost of resolve_url
    to_try = [lambda: url, lambda: resolve_url(url)]
    for attempt in to_try:
      try:
        # Attempt is a function, as lambda wraps each url in a function
        module_path, scraper_method = scraper_factory.resolve_scraper(attempt())
        break
      except scrapers.ScraperNotFound:
        # Then try to get the scraper with the next
        continue
    else:
      # Use generic scraper
      module_path, scraper_method = scraper_factory.generic_scraper()

    # Use the scraper method returned to scrape the article
    article = scraper_method(url)

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
