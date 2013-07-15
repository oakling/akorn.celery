COUCH_SERVER = "http://couchdb.private:5984"

try:
    from local_settings import *
except ImportError:
    pass
