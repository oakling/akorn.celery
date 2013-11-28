from celery import Celery

from akorn.scrapers.scrapers import Scrapers
from akorn.celery.couch import db_store
from akorn.celery.scrapers.router import resolve_and_scrape, resolve_doi, resolve_journal
from akorn.celery.celeryconfig import BROKER_URL, CELERY_RESULT_BACKEND

app = Celery('scraping_tasks', broker=BROKER_URL, backend=CELERY_RESULT_BACKEND)

scrapers = Scrapers()

def resolve_merges():
    # TODO: At this stage, we check that our source doesn't have the same IDs as any other records.
    #if article:
    #  to_merge = set()
    #
    #  for id_type, id in article['ids'].items():
    #    #print id_type, id
    #    for row in db.view('index/ids', key=id_type + ":" + id).rows:
    #      to_merge.add(row.id)
    #
    #  if len(to_merge) >= 2:
    #    pass
    pass 

@app.task('rescrape-articles')
def rescrape_articles():
  records = db_store.view('rescrape/rescrape', include_docs='true').rows

  for record in records:
    scrape_journal.delay(record.doc['source_url'], record.doc.id)

@app.task('scrape-doi')
def scrape_doi(doi, doc_id=None):
    records_doi = db_store.view('index/ids', key='doi:' + doi, include_docs='true').rows

    url = resolve_doi(doi)
    records_source = db_store.view('index/sources', key=url, include_docs='true').rows
    
    if doc_id is not None or not (records_doi and records_source):
        # source url isn't in db
        if doc_id:
          article = db_store[doc_id]
          rev_id = article.rev
        else:
          article = {}
           
        try:
          scraped_article = resolve_and_scrape(url)

          # If we haven't excepted at this point, clear the current article and save it
          article.clear()
          article.update(scraped_article)

          # Add the id and revision back in since we just cleared the doc. Awkward.
          if doc_id:
            article['_id'] = doc_id
            article['_rev'] = rev_id
        except Exception, e:
          # Make a doc to remember to rescrape later
          article['error'] = str(e)
          article['rescrape'] = True
          article['source_urls'] = [url]

        if article:
          doc_id, _ = db_store.save(article)

    else:
        article = records[0].doc
        doc_id = article.id

    resolve_merges()

    return doc_id

def check_source(url):
  rows = db_store.view('index/sources', key=url).rows
  
  if len(rows) == 0:
    return True
  else:
    return False

@app.task('scrape-rss')
def scrape_rss(scraper_module, item):
  s = scrapers.module_names[scraper_module]
  d = s.scrape_rss(item)

  if 'journal' in d:
    d['journal_id'] = resolve_journal(d['journal'])

  if check_source(d['source_urls'][0]):
    doc_id, _ = db_store.save(d)
  else:
    print "Already got this one"
    rows = db_store.view('index/sources', key=d['source_urls'][0], include_docs='true').rows
    article = rows[0].doc
    doc_id = article.id

  return doc_id

@app.task('scrape-journal')
def scrape_journal(url, doc_id=None, base_article={}):
    """Find the paper in the database and then add or merge as
    necessary."""

    # TODO: Make sure that if doc_id is not None, it does actually
    # refer to a document in the database.

    # Scrape if we have a doc_id or it hasn't already been scraped
    # always scrape if we're given a doc_id
    if doc_id is not None or check_source(url):
        # source url isn't in db
        if doc_id:
          article = db_store[doc_id]
          rev_id = article.rev
        else:
          article = {}
           
        scraped_article = resolve_and_scrape(url)

        # clear the current article and save it
        article.clear()
        article.update(base_article)
        article.update(scraped_article)

        # Add the id and revision back in since we just cleared the
        # doc. Awkward.
        if doc_id:
          article['_id'] = doc_id
          article['_rev'] = rev_id

        # If we haven't explicitly asked for the article to be scraped
        # by providing a doc_id, then check that it hasn't been
        # inadvertantly scraped already before we go
        if doc_id is not None or check_source(article['source_urls'][-1]):
            doc_id, _ = db_store.save(article)
    else:
        # we've already scraped this url. there should only be one
        # such doc.
        rows = db_store.view('index/sources', key=url, include_docs='true').rows
        article = rows[0].doc
        doc_id = article.id

    resolve_merges()

    return doc_id
