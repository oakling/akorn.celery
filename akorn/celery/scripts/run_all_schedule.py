from akorn.celery.feeds import tasks

def main():
  tasks.fetch_feed.delay()

