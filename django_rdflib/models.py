from django.db import models
from django.conf import settings
from rdflib.store.AbstractSQLStore import INTERNED_PREFIX
import django_rdflib
import fts


TABLE_PREFIX = INTERNED_PREFIX + django_rdflib.RDFLIB_STORE_IDENTIFIER_HASH + '_'

class NamespaceBinds(models.Model):
    prefix = models.CharField(max_length=20, primary_key=True)
    uri = models.TextField(db_index=True)
    
    class Meta:
        managed = False
        db_table = TABLE_PREFIX + 'namespace_binds'

class Identifiers(models.Model):
    """
    URIs and BNodes
    """
    id = models.AutoField(primary_key=True)
    term_type = models.CharField(max_length=1, db_index=True)
    lexical = models.TextField()

    class Meta:
        managed = False
        db_table = TABLE_PREFIX + 'identifiers'

class Literals(fts.SearchableModel):
    """
    Literals
    """
    id = models.AutoField(primary_key=True)
    lexical = models.TextField()

    search_objects = fts.SearchManager(fields=('lexical',))
    
    class Meta:
        managed = False
        db_table = TABLE_PREFIX + 'literals'

class Relations(models.Model):
    """
    triples where all the elements are URIs or BNodes
    """
    id = models.AutoField(primary_key=True)
    subject = models.ForeignKey(Identifiers, related_name='relations_subject', db_index=True, db_column='subject')
    subject_term = models.CharField(max_length=1, db_index=True)
    predicate = models.ForeignKey(Identifiers, related_name='relations_predicate', db_index=True, db_column='predicate')
    predicate_term = models.CharField(max_length=1, db_index=True)
    object = models.ForeignKey(Identifiers, related_name='relations_object', db_index=True, db_column='object')
    object_term = models.CharField(max_length=1, db_index=True)
    context = models.ForeignKey(Identifiers, related_name='relations_context', db_index=True, db_column='context')
    context_term = models.CharField(max_length=1, db_index=True)
    
    class Meta:
        managed = False
        db_table = TABLE_PREFIX + 'relations'

class LiteralProperties(models.Model):
    """
    triples where the object is a literal
    """
    id = models.AutoField(primary_key=True)
    subject = models.ForeignKey(Identifiers, related_name='lp_subject', db_index=True, db_column='subject')
    subject_term = models.CharField(max_length=1, db_index=True)
    predicate = models.ForeignKey(Identifiers, related_name='lp_predicate', db_index=True, db_column='predicate')
    predicate_term = models.CharField(max_length=1, db_index=True)
    object = models.ForeignKey(Literals, related_name='lp_object', db_index=True, db_column='object')
    context = models.ForeignKey(Identifiers, related_name='lp_context', db_index=True, db_column='context')
    context_term = models.CharField(max_length=1, db_index=True)
    data_type = models.IntegerField(db_index=True)
    language = models.CharField(max_length=3, db_index=True)
    
    class Meta:
        managed = False
        db_table = TABLE_PREFIX + 'literalproperties'

class AssociativeBox(models.Model):
    """
    triples where the predicate is rdf:type
    """
    id = models.AutoField(primary_key=True)
    member = models.ForeignKey(Identifiers, related_name='ab_member', db_index=True, db_column='member')
    member_term = models.CharField(max_length=1, db_index=True)
    box_class = models.ForeignKey(Identifiers, related_name='ab_box_class', db_index=True, db_column='class')
    box_class_term = models.CharField(max_length=1, db_index=True, db_column='class_term')
    context = models.ForeignKey(Identifiers, related_name='ab_context', db_index=True, db_column='context')
    context_term = models.CharField(max_length=1, db_index=True)
    
    class Meta:
        managed = False
        db_table = TABLE_PREFIX + 'associativebox'

