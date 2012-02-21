from cron.appsignals import cron_signal
from django_rdflib.utils import garbage_collection

def gc(sender, **kwargs):
    if (kwargs['freq'] != 'hourly'):
        return
    garbage_collection()

def register():
    cron_signal.connect(gc)

