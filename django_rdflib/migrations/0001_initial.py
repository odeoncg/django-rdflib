from south.db import db
from django.db import models
import django_rdflib
from django_rdflib.models import *
from django_rdflib.utils import get_rdflib_config_string 
from rdflib.store.AbstractSQLStore import INTERNED_PREFIX
from django.conf import settings
import rdflib
from rdflib.store import Store


TABLE_PREFIX = INTERNED_PREFIX + django_rdflib.RDFLIB_STORE_IDENTIFIER_HASH

class Migration:
    
    def forwards(self, orm):
        
        # create the triple store using rdflib
        rdflib.plugin.register('PostgreSQLStore', Store, 'django_rdflib.PostgreSQLStore', 'PostgreSQL')
        store = rdflib.plugin.get('PostgreSQLStore', Store)(django_rdflib.RDFLIB_STORE_IDENTIFIER)
        store.open(get_rdflib_config_string(), create=True)
        
        # add missing id fields that Django expects where no other PK was declared
        db.add_column('%s_associativebox' % TABLE_PREFIX, 'id', orm['django_rdflib.AssociativeBox:id'])
        db.add_column('%s_literalproperties' % TABLE_PREFIX, 'id', orm['django_rdflib.LiteralProperties:id'])
        db.add_column('%s_relations' % TABLE_PREFIX, 'id', orm['django_rdflib.Relations:id'])

        # add the full text search columns and indices
        db.add_column('%s_literals' % TABLE_PREFIX, 'search_index', orm['django_rdflib.Literals:search_index'])
        db.execute('CREATE INDEX "%s_literals_search_index" ON "%s_literals" USING gin("search_index")' % (TABLE_PREFIX, TABLE_PREFIX))
        # update the FTS indices
        Literals.search_objects.update_index()
        # simple B-tree indices
        db.execute('CREATE INDEX "%s_identifiers_lexical_index" ON "%s_identifiers" ("lexical")' % (TABLE_PREFIX, TABLE_PREFIX))
    
    

    def backwards(self, orm):
        
        # Deleting model 'LiteralProperties'
        db.delete_table('%s_literalproperties' % TABLE_PREFIX)
        
        # Deleting model 'Identifiers'
        db.delete_table('%s_identifiers' % TABLE_PREFIX)
        
        # Deleting model 'Literals'
        db.delete_table('%s_literals' % TABLE_PREFIX)
        
        # Deleting model 'Relations'
        db.delete_table('%s_relations' % TABLE_PREFIX)
        
        # Deleting model 'NamespaceBinds'
        db.delete_table('%s_namespace_binds' % TABLE_PREFIX)
        
        # Deleting model 'AssociativeBox'
        db.delete_table('%s_associativebox' % TABLE_PREFIX)
        
    
    
    models = {
        'django_rdflib.associativebox': {
            'Meta': {'db_table': "'%s_associativebox'" % TABLE_PREFIX},
            'box_class': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ab_box_class'", 'to': "orm['django_rdflib.Identifiers']"}),
            'box_class_term': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'}),
            'context': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ab_context'", 'to': "orm['django_rdflib.Identifiers']"}),
            'context_term': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ab_member'", 'to': "orm['django_rdflib.Identifiers']"}),
            'member_term': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'})
        },
        'django_rdflib.identifiers': {
            'Meta': {'db_table': "'%s_identifiers'" % TABLE_PREFIX},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lexical': ('django.db.models.fields.TextField', [], {}),
            'term_type': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'})
        },
        'django_rdflib.literalproperties': {
            'Meta': {'db_table': "'%s_literalproperties'" % TABLE_PREFIX},
            'context': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'lp_context'", 'to': "orm['django_rdflib.Identifiers']"}),
            'context_term': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'}),
            'data_type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '3', 'db_index': 'True'}),
            'object': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'lp_object'", 'to': "orm['django_rdflib.Literals']"}),
            'predicate': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'lp_predicate'", 'to': "orm['django_rdflib.Identifiers']"}),
            'predicate_term': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'lp_subject'", 'to': "orm['django_rdflib.Identifiers']"}),
            'subject_term': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'})
        },
        'django_rdflib.literals': {
            'Meta': {'db_table': "'%s_literals'" % TABLE_PREFIX},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lexical': ('django.db.models.fields.TextField', [], {}),
            'search_index': ('fts._VectorField', [], {})
        },
        'django_rdflib.namespacebinds': {
            'Meta': {'db_table': "'%s_namespace_binds'" % TABLE_PREFIX},
            'prefix': ('django.db.models.fields.CharField', [], {'max_length': '20', 'primary_key': 'True'}),
            'uri': ('django.db.models.fields.TextField', [], {'db_index': 'True'})
        },
        'django_rdflib.relations': {
            'Meta': {'db_table': "'%s_relations'" % TABLE_PREFIX},
            'context': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relations_context'", 'to': "orm['django_rdflib.Identifiers']"}),
            'context_term': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relations_object'", 'to': "orm['django_rdflib.Identifiers']"}),
            'object_term': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'}),
            'predicate': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relations_predicate'", 'to': "orm['django_rdflib.Identifiers']"}),
            'predicate_term': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relations_subject'", 'to': "orm['django_rdflib.Identifiers']"}),
            'subject_term': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'})
        }
    }
    
    complete_apps = ['django_rdflib']
