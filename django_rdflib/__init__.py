from django.db import transaction
from rdflib import plugin
from rdflib.store import Store
import hashlib


RDFLIB_STORE_IDENTIFIER = 'rdfstore' # don't change after the store has been created
RDFLIB_STORE_IDENTIFIER_HASH = hashlib.sha1(RDFLIB_STORE_IDENTIFIER).hexdigest()[:10]
plugin.register('PostgreSQLStore', Store, 'django_rdflib.PostgreSQLStore', 'PostgreSQL')

try:
    with transaction.commit_on_success():
        from utils import create_custom_namespaces
        create_custom_namespaces()
except:
    pass

