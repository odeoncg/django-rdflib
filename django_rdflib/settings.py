from rdflib.namespace import Namespace
import re

# used for creating a named graph
RDFLIB_DEFAULT_GRAPH_URI = 'http://testgraph.com'

# structure: [alias, URI]
CUSTOM_NAMESPACES = [
    ['site_ns', 'http://brancusi1.usc.edu/RDF/'],
    ['owl', 'http://www.w3.org/2002/07/owl#'],
    ['rdfs', 'http://www.w3.org/2000/01/rdf-schema#'],
    ['xlink', 'http://www.w3.org/1999/xlink'],
]
SITE_NS, OWL, RDFS, XLINK = [Namespace(ns[1]) for ns in CUSTOM_NAMESPACES]

#SITE_NS = bind_namespace('site_ns', 'http://brancusi1.usc.edu/RDF/')
#OWL = bind_namespace('owl', 'http://www.w3.org/2002/07/owl#')
#RDFS = bind_namespace('rdfs', 'http://www.w3.org/2000/01/rdf-schema#')

URL_ALIASES = {'brainPart': 'brain_part',
               'thesaurus': 'thesaurus_def',
               'thesaurusReference': 'thesaurus_ref',
               'ontology': 'ontology_viewer',
               'nomenclature': 'edit_rdf_object',
              }

BOOL_VALUES = {'True': True, 'False': False, 'On': True, 'on': True, 'Off': False, 'off': False}

DONT_UPDATE_INDEX = [
    'thesaurusComment',
    'thesaurusSynonym',
    'thesaurusSynonymGroup',
]

# for the forms
DEFAULT_PREDICATE_ORDER = [SITE_NS.name, SITE_NS.description, SITE_NS.workspace]
PREDICATE_ORDER = {
    'brainPart': [SITE_NS.name, SITE_NS.collator, SITE_NS.workspace],
    'thesaurus': [SITE_NS.entry, SITE_NS.preferred, SITE_NS.abbrev, SITE_NS.definition],
    'thesaurusReference': [SITE_NS.authors, SITE_NS.year],
}
REQUIRED_FIELDS = {
    'brainPart': [SITE_NS.name, SITE_NS.collator],
    'thesaurus': [SITE_NS.entry, SITE_NS.definition],
    'thesaurusReference': [SITE_NS.authors],
    'thesaurusSynonym': [SITE_NS.thesaurus],
}
HIDDEN_FIELDS = {
    'brainPart': [SITE_NS.collator],
    'thesaurusSynonym': [SITE_NS.synonymGroup],
}

HIDDEN_FROM_ADMIN_FIELDS = {
    'thesaurusSynonym': [SITE_NS.synonymGroup],
}

# defaults to SITE_NS.name
SLUG_GENERATOR_FIELD = {
    'thesaurus': SITE_NS.entry,
    'thesaurusReference': SITE_NS.authors,
}

# defaults to SITE_NS.name
LABEL_FIELD = {
    'thesaurus': lambda x: '%s %s' % (x['entry'], re.sub(r'\[\[(?:[^\[\]]*\|)?([^\[\]]+)\]\]', '(\\1)', x.get('reference', ''))),
    'thesaurusReference': SITE_NS.authors,
}

NO_ADD_NEW = [SITE_NS.collator, SITE_NS.collatorInvolvement, SITE_NS.grossConstituent, SITE_NS.nomenclature, SITE_NS.species]

# globals()['foo'] = 'bar'
