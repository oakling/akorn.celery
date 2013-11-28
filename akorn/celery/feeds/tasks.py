from celery import Celery
from akorn.celery.scrapers.tasks import scrape_journal, scrape_rss
from akorn.scrapers import scrapers
import feedparser

from akorn.celery.couch import db_store
from akorn.celery.celeryconfig import BROKER_URL, CELERY_RESULT_BACKEND

app = Celery('feed_tasks', broker=BROKER_URL, backend=CELERY_RESULT_BACKEND)

scraper_factory = scrapers.Scrapers()

@app.task('fetch-feeds')
def fetch_feed(scraper_module=None):
    if scraper_module is not None:
        feedhandler, feed_urls = scraper_factory.feeds[scraper_module]
        for feed_url in feed_urls:
            add_feed_items.delay(scraper_module, feedhandler, feed_url)
    else:
        for scraper_module, (feedhandler, feed_urls) in scraper_factory.feeds.items():
            for feed_url in feed_urls:
                add_feed_items.delay(scraper_module, feedhandler, feed_url)


@app.task('add-feed-items')
def add_feed_items(scraper_module, feedhandler, feed_url):
    """Add feed items to database.."""

    # should be smarter here, e.g. use If-Modified-Since
    feed = feedparser.parse(feed_url, agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50')

    should_scrape = scraper_factory.should_scrape[scraper_module]

    for item in feed['items']:
        base_article = {}

        if type(feedhandler) is list:
          for feedhandler_ in feedhandler:
            if feedhandler_ in item:
              item_url = item[feedhandler_]
              break
          else:
            raise Exception("Feed tag(s) not valid.")
        else:
          item_url = item[feedhandler]

        check_exists = db_store.view('index/sources', key=item_url, include_docs='false')

        try:
          check_exists.rows
        except:
          check_exists = db_store.view('index/sources', key=item_url, include_docs='false')

        if not check_exists.rows:
          if should_scrape:
            scrape_journal.delay(item_url, base_article=base_article)
          else:
            scrape_rss.delay(scraper_module, item)

