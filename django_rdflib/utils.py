import django_rdflib
from django_rdflib.settings import *
from models import *
import rdflib
from rdflib.graph import ConjunctiveGraph as Graph
from rdflib import plugin
from rdflib.store import Store, NO_STORE, VALID_STORE
from rdflib.namespace import Namespace, RDF, OWL
from rdflib.term import Literal, URIRef, BNode
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse, Http404
import gzip, os
from django.core.urlresolvers import reverse
from pprint import pprint
import types
import unicodedata
from django.utils.encoding import smart_unicode
from django.db import connections


quad_cache = []


def get_rdflib_config_string():
    return "host=%s,user=%s,password=%s,db=%s" % (settings.DATABASES['default']['HOST'], settings.DATABASES['default']['USER'], settings.DATABASES['default']['PASSWORD'], settings.DATABASES['default']['NAME'])

def get_rdflib_store_graph():
    """
    don't try to use global variables for the store and graph because they cache the values
    get them fresh to see the state of the system at a certain point in time
    """
    rdflib_store = rdflib.plugin.get('PostgreSQLStore', Store)(django_rdflib.RDFLIB_STORE_IDENTIFIER)
    rdflib_store.open(get_rdflib_config_string())
    rdflib_graph = Graph(rdflib_store, identifier = URIRef(RDFLIB_DEFAULT_GRAPH_URI))
    return rdflib_store, rdflib_graph

store, graph = get_rdflib_store_graph()

def process_field(field):
    if type(field) == str:
        res = field.decode('latin1')
    else:
        res = unicode(field)
        
    if res == 'N/A':
        res = ''
        
    res = res.replace('\\', '').strip()
    return res

def add_triple(subj, pred, obj):
    """
    add the triple if the object is not empty
    the object will be converted to a Literal if it's a string
    the subject and predicate are stored as is

    !!! no committing done, just caching. call commit_triples() to store the triples efficiently !!!
    """
    if not obj and type(obj) != bool:
        return
    if type(obj) in [str, unicode]:
        obj = process_field(obj)
        if not obj:
            return
        obj = Literal(obj)
    elif not isinstance(obj, (BNode, URIRef, Literal)):
        obj = Literal(unicode(obj))
    quad_cache.append([subj, pred, obj, graph.default_context])
    return [subj, pred, obj, graph.default_context]

def commit_triples():
    global quad_cache
    
    store.addN(quad_cache)
    graph.commit()
    quad_cache = []

def slugify(value):
    """
    Normalizes string, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    value = smart_unicode(value, errors='ignore')
    value = re.sub('[^\w\s-]', '', value).strip()
    return re.sub('[-\s]+', '-', value)

def create_slug(word, mold=unicode(SITE_NS['%s']), extra_slugs=None):
    """
    create unique slugs for subjects with a rdf:type
    """
    if extra_slugs is None:
        extra_slugs = []
    slug = slugify(word)
    slug_base = slug # used to create numbered variants
    index = 2 # initial number added to the slug
    while True:
        if AssociativeBox.objects.filter(member__lexical=(mold % slug)).count() == 0 and slug not in extra_slugs:
            # unique slug
            break
        slug = '%s-%d' % (slug_base, index)
        index += 1
    return slug

def bind_namespace(alias, ns):
    """
    returns the Namespace object
    """
    store, graph = get_rdflib_store_graph()
    graph.bind(alias, ns)
    graph.commit()
    return Namespace(ns)

def create_custom_namespaces():
    for alias, uri in CUSTOM_NAMESPACES:
        bind_namespace(alias, uri)

def delete_triples(triples):
    """
    triples = [[s1, p1, o1], [s2, o2, p2], ...]
    """
    store, graph = get_rdflib_store_graph()
    #quads = []
    #for s, p, o in triples:
        #quads.append([s, p, o, None])
    #batch = 100
    #while quads:
        #graph.removeN(quads[:batch])
        #del quads[:batch]
    for s, p, o in triples:
        graph.removeN([[s, p, o, None]])
    #store.gc()
    graph.commit()

def delete_same_type_triples(nsalias, ttype):
    """
    args:
        nsalias = namespace alias
        ttype = node type
    usage:
        to delete all the triples with the subject ?node where "?node rdf:type nsalias:ttype" do
        delete_same_type_triples(nsalias, ttype)
    """
    store, graph = get_rdflib_store_graph()

    # remove triples

    #q = """
    #PREFIX nstype: <%s>
    #PREFIX rdf: <%s>
    #SELECT ?s ?p ?o WHERE {
        #?s rdf:type nstype:%s .
        #?s ?p ?o .
    #}
    #""" % (store.namespace(nsalias), RDF, ttype)
    #for s, p, o in graph.query(q):
        #graph.remove((s, p, o))
    
    obj = URIRef(store.namespace(nsalias) + ttype)
    #print obj
    triples = []
    for s, _, _ in graph.triples((None, RDF.type, obj)):
        triples.append([s, None, None])
        triples.append([None, None, s])
    delete_triples(triples)

def delete_subject(subject):
    store, graph = get_rdflib_store_graph()
    delete_triples([[subject, None, None]])
    graph.commit()

def garbage_collection():
    store, graph = get_rdflib_store_graph()
    store.gc()
    graph.commit()

def empty_store():
    """
    !!! deletes everything !!!
    """
    store, graph = get_rdflib_store_graph()
    store.empty()
    graph.commit()

def update_index():
    """
    update the FTS index
    """
    Literals.search_objects.update_index()

def stringify(param):
    p_str = unicode(param)
    return p_str.strip('/')[p_str.strip('/').rfind('/') + 1:]

def get_data_type_for_site_ns_type(site_ns_type):
    """
    Get BNode/URIRef for a SITE_NS.type
    """

    store, graph = get_rdflib_store_graph()
    q = """                    
        PREFIX site_ns: <%s>
        PREFIX rdf: <%s>
        SELECT ?s WHERE {
            ?s rdf:type site_ns:%s .
        }
        ORDER BY ?s
        LIMIT 1
    """ % (store.namespace('site_ns'), RDF, site_ns_type)
    for s, in graph.query(q):
        return type(s)
    return None

def get_all_slugs_for_site_ns_type(site_ns_type):
    store, graph = get_rdflib_store_graph()
    slugs = []
    for s in get_objects_for_site_ns_type(site_ns_type):
        s_str = str(s)
        slugs.append(stringify(s_str))

    return slugs

def get_objects_for_site_ns_type(site_ns_type):
    store, graph = get_rdflib_store_graph()
    objects = []
    q = """
    PREFIX site_ns: <%s>
    PREFIX rdf: <%s>
    SELECT DISTINCT ?s WHERE {
        ?s rdf:type site_ns:%s .
        ?s ?p ?o .
    } ORDER BY ?s
    """ % (store.namespace('site_ns'), RDF, site_ns_type)
    for s, in graph.query(q):
        objects.append(s)

    return objects

def get_objects_for_site_ns_type_and_link_dict(site_ns_type, user=None):
    store, graph = get_rdflib_store_graph()
    objects_dict = {}
    q_start = """
    PREFIX site_ns: <%s>
    PREFIX rdf: <%s>
    SELECT DISTINCT ?s WHERE {
        ?s rdf:type site_ns:%s .
        ?s ?p ?o .
    """ % (store.namespace('site_ns'), RDF, site_ns_type)
    
    q_mid = ""
    if user:
        q_mid = """
            ?s site_ns:workspace "%s" .
        """ % (user.id)
    
    q_end = """
    } ORDER BY ?s
    """
    q = q_start + q_mid + q_end
    for s, in graph.query(q):
        if user:
            objects_dict[stringify(s).replace('-', ' ')] = reverse('edit_ws_object', args=[site_ns_type, stringify(s)])
        else:
            objects_dict[stringify(s).replace('-', ' ')] = reverse('edit_rdf_object', args=[site_ns_type, stringify(s)])

    return objects_dict, len(graph.query(q))

def get_objects_for_site_ns_type_count(site_ns_type, user=None):
    store, graph = get_rdflib_store_graph()
    q_start = """
    PREFIX site_ns: <%s>
    PREFIX rdf: <%s>
    SELECT DISTINCT ?s WHERE {
        ?s rdf:type site_ns:%s .
        ?s ?p ?o .
    """ % (store.namespace('site_ns'), RDF, site_ns_type)
    
    q_mid = ""
    if user:
        q_mid = """
            ?s site_ns:workspace "%s" .
        """ % (user.id)
    
    q_end = """
    } ORDER BY ?s
    """
    q = q_start + q_mid + q_end

    return len(graph.query(q))

def create_subject(site_ns_type, name, DataType=None):
    if not DataType:
        DataType = get_data_type_for_site_ns_type(site_ns_type)

    if DataType == BNode:
        subject = BNode()
    else:
        url_alias = URL_ALIASES.get(site_ns_type, None)
        if url_alias:
            new_name_slug = create_slug(name, '%s%s' % (settings.SITE_NAME, reverse(url_alias, args=['%s'])))
            subject = URIRef('%s%s' % (settings.SITE_NAME, reverse(url_alias, args=[new_name_slug])))
        else:
            new_name_slug = create_slug(name)
            subject = SITE_NS[new_name_slug]
    
    if DataType:
        add_triple(subject, RDF.type, SITE_NS[site_ns_type])
        #add_triple(subject, SITE_NS.name, name)
        commit_triples()
    
    return subject

def get_site_ns_type_for_subject(subject):
    """
    Returns the site_ns:type as string for the subject
    """
    store, graph = get_rdflib_store_graph()
    subj_type = None
    for s,p,o in graph.triples((subject, RDF.type, None)):
        subj_type = o
    return str(stringify(subj_type))

def get_site_ns_type_for_predicate(site_ns_type, pred):
    """
    Returns the site_ns:type as string for an object that is referenced with the given predicate 
    in the given site_ns_type objects.
    If it can not find an object to check type, it returns the value based on the predicate
    """
    pred_type = pred
    store, graph = get_rdflib_store_graph()
    q = """                    
        PREFIX site_ns: <%s>
        PREFIX rdf: <%s>
        SELECT ?type WHERE {
            ?s <%s> ?o .
            ?s rdf:type site_ns:%s .
            ?o rdf:type ?type
        }
        ORDER BY ?o
        LIMIT 1
    """ % (store.namespace('site_ns'), RDF, pred, site_ns_type)
    for pred_type, in graph.query(q):
        pred_type
    return stringify(pred_type)

def subject_exists(subject):
    """
    Checks if the given subject has an rdf:type.
    If it doesnt checks if it is refered as 's' or 'o' in an (s,p,o) triple
    """
    store, graph = get_rdflib_store_graph()
    for s,p,o in graph.triples((subject, None, None)):
        return True
    for s,p,o in graph.triples((None, None, subject)):
        return True
    return False

def all_rdf_types(user=None):
    """
    Returns a list with all rdf:type as strings
    """
    store, graph = get_rdflib_store_graph()
    rdf_types = []
    q_start = """                    
        PREFIX site_ns: <%s>
        PREFIX rdf: <%s>
        SELECT DISTINCT ?o WHERE {
            ?s rdf:type ?o .
    """ % (store.namespace('site_ns'), RDF)
    
    q_mid = ""
    if user:
        q_mid = """
            ?s site_ns:workspace "%s" .
        """ % (user.id)
    
    q_end = """
        }
        ORDER BY ?o
    """

    q = q_start + q_mid + q_end
    for rdf_type_el, in graph.query(q):
        rdf_types.append(rdf_type_el)
    return rdf_types

    
def get_subject(site_ns_type, name_slug):
    DataType = get_data_type_for_site_ns_type(site_ns_type)
    if DataType == BNode:
        subject = BNode(name_slug)
    else:
        url_alias = URL_ALIASES.get(site_ns_type, None)
        if url_alias:
            if url_alias == 'edit_rdf_object':
                subject = URIRef('%s%s' % (settings.SITE_NAME, reverse(url_alias, args=[site_ns_type, name_slug])))
            else:
                subject = URIRef('%s%s' % (settings.SITE_NAME, reverse(url_alias, args=[name_slug])))
        else:
            subject = SITE_NS[name_slug]
    if not subject_exists(subject) or get_site_ns_type_for_subject(subject) != site_ns_type:
        print __file__, subject_exists(subject), get_site_ns_type_for_subject(subject), DataType, subject
        raise Http404

    return subject

def get_predicates(site_ns_type, name_slug=None):
    store, graph = get_rdflib_store_graph()
    predicates_list = []

    if name_slug:
        subject = get_subject(site_ns_type, name_slug)
    q = """                    
    PREFIX site_ns: <%s>
    PREFIX rdf: <%s>
    SELECT DISTINCT ?p WHERE {
        ?s rdf:type site_ns:%s .
        ?s ?p ?o .
    }
    ORDER BY ?p 
    """ % (store.namespace('site_ns'), RDF, site_ns_type)
    
    for p in graph.query(q):
        try:
            predicates_list.append(p[0])
        except Exception, e:
            pass
    
    return predicates_list

def add_predicate(subject, form_data, site_ns_type=None):
    slug = slugify(form_data['name'])
    predicate = SITE_NS[slug]
    if form_data['value_type'] == 'text':
        obj = Literal(form_data['value'])
    else:
        obj = get_subject(form_data['value_type'], stringify(form_data['value']))
    
    # check if the predicate already exists and delete it
    existing_obj = None
    for _, _, o in graph.triples((subject, predicate, None)):
        existing_obj = o
        str_existing_obj = unicode(existing_obj)
        break
    must_add_triple = False
    if existing_obj:
        if str_existing_obj != unicode(obj):
            delete_triples([[subject, predicate, existing_obj]])
            must_add_triple = True
    else:
        must_add_triple = True

    if must_add_triple:
        add_triple(subject, predicate, obj)

    commit_triples()
    return True

def get_literals_and_nodes(subject):
    store, graph = get_rdflib_store_graph()
    literals = []
    nodes = []
    for s, p, o in graph.triples((subject, None, None)):
        if (not isinstance(o, Literal)):
            nodes.append([p,o])
        else:
            literals.append([p,o])
    return literals, nodes

def get_all_objects_labels(site_ns_type):
    label_gen = LABEL_FIELD.get(site_ns_type, 'name')
    labels = {}
    data = items_of_rdf_type(SITE_NS[site_ns_type])
    for s in data:
        if hasattr(label_gen, '__call__'):
            label = label_gen(data[s])
        else:
            label = data[s].get(label_gen, data[s]['slug'])
        labels[s] = label
    return labels

def order_predicates_list(pred_list, order_list):
    existing_order_preds = []
    for pred in order_list:
        if pred in pred_list:
            existing_order_preds.append(pred)

    for pred in existing_order_preds:
        pred_pos_in_pred_list = pred_list.index(pred)
        pred_pos_in_order_list = existing_order_preds.index(pred)
        del pred_list[pred_pos_in_pred_list]
        pred_list.insert(pred_pos_in_order_list, pred)
    
    return pred_list

def order_literals_nodes_list(pred_list, order_list):
    existing_order_preds = []
    pred_list_keys = []
    for item in pred_list:
        if item[0] not in pred_list_keys:
            pred_list_keys.append(item[0])

    for pred in order_list:
        if pred in pred_list_keys:
            existing_order_preds.append(pred)

    i = 1
    while i < len(pred_list):
        for pred in existing_order_preds:
            for item in pred_list:
                try:
                    pred_pos_in_pred_list = pred_list.index([pred, item[1]])
                    pred_pos_in_order_list = existing_order_preds.index(pred)
                    del pred_list[pred_pos_in_pred_list]
                    pred_list.insert(pred_pos_in_order_list, [pred, item[1]])
                    break
                except:
                    pass
        i += 1

    return pred_list

def get_label(subject):
    store, graph = get_rdflib_store_graph()
    label = None
    for s,p,o in graph.triples((subject, SITE_NS.name, None)):
        label = o
    if not label:
        label = stringify(subject)

    return label

def smart_truncate(content, length=100, suffix='...'):
    """
    By "smart" I mean that it will not cutoff words in the middle instead it will cut off on spaces. 
    For instance, not "this is rea...", instead "this is really..."
    """
    if len(content) <= length:
        return content
    else:
        return ' '.join(content[:length+1].split(' ')[0:-1]) + suffix

def camelcase_to_words(s):
    from django.template.defaultfilters import capfirst
    return capfirst(re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', ' \\1', s).strip())

def camelcase(value):
    from string import capitalize
    return "".join([capitalize(w) for w in re.split(re.compile("[\W_]*"), value)])

def items_of_rdf_type(rdf_type, extra_po=[]):
    """
    rdf_type: a complete URI like SITE_NS.foo
    extra_po: list of extra pred-obj pairs like [[pred1, obj1], [pred2, obj2], ...] that apply to the subject
              (full URIs required)

    returns a dict
    """
    store, graph = get_rdflib_store_graph()
    res = {}
    extra=''
    for p, o in extra_po:
        if isinstance(o, URIRef):
            extra += '?s <%s> <%s> .\n' % (p, o)
        elif isinstance(o, Literal):
            extra += '?s <%s> "%s" .\n' % (p, o)
        else:
            raise Exception, 'can\'t search by bnode in SPARQL, fool'
    q = """
    PREFIX rdf: <%s>
    SELECT ?s ?p ?o WHERE {
        ?s rdf:type <%s> .
        %s
        ?s ?p ?o .
    }
    """ % (RDF, rdf_type, extra)
    for s, p, o in graph.query(q):
        s_str, p_str, o_str = [unicode(x) for x in [s, p, o]]
        slug = s_str.strip('/')
        pos = slug.rfind('/')
        if pos != -1:
            slug = slug[pos+1:]
        p_str = p_str.strip('/')
        last_slash = p_str.rfind('/')
        if last_slash != -1:
            p_str = p_str[last_slash+1:]
        if p:
            if not res.has_key(s_str):
                res[s_str] = {'subject': s_str, 'slug': slug}
            if not res[s_str].has_key(p_str):
                res[s_str][p_str] = o_str
    return res

def create_prefix_name(value):
    from rdflib.namespace import RDF, _XSD_NS

    prefix_name = ''
    rdf = RDF
    _xsd_ns = _XSD_NS
    for custom_namespace in CUSTOM_NAMESPACES:
        if unicode(value).find(custom_namespace[1]) > -1:
            prefix_name = "%s:%s" % (custom_namespace[0], unicode(value).replace(custom_namespace[1], ''))
            break

    if not prefix_name:
        if unicode(value).find(unicode(rdf)) > -1:
            prefix_name = "%s:%s" % ('rdf', unicode(value).replace(unicode(rdf), ''))
        elif unicode(value).find(unicode(_xsd_ns)) > -1:
            prefix = '_xsd_ns'
            prefix_name = "%s:%s" % ('_xsd_ns', unicode(value).replace(unicode(_xsd_ns), ''))

    return prefix_name

def delete_rdf_type_triples(site_ns_type):
    triples_list = []
    instances = get_objects_for_site_ns_type(site_ns_type)
    for item in instances:
        for s, p, o in graph.triples((item, None, None)):
            triples_list.append([s, p, o])

        for s, p, o in graph.triples((None, None, item)):
            triples_list.append([s, p, o])

    delete_triples(triples_list)
    if site_ns_type not in DONT_UPDATE_INDEX:
        update_index()

def rename_rdf_type_triples(site_ns_type, field):
    triples_list = []
    for s, p, o in graph.triples((None, RDF.type, SITE_NS[site_ns_type])):
        triples_list.append([s, p, o])

    delete_triples(triples_list)

    object_type = camelcase(field)
    subject = SITE_NS[object_type]
    new_triples_list = []
    for item in triples_list:
        add_triple(item[0], item[1], subject)

    commit_triples()

    if site_ns_type not in DONT_UPDATE_INDEX:
        update_index()

def rename_predicate_func(site_ns_type, name_slug, pred, field):
    triples_list = []

    for s,p,o in graph.triples((None, SITE_NS[pred], None)):
        triples_list.append([s, p, o])

    delete_triples(triples_list)

    new_pred_slug = camelcase(field)
    new_pred = SITE_NS[new_pred_slug]
    for item in triples_list:
        add_triple(item[0], new_pred, item[2])

    commit_triples()

    if site_ns_type not in DONT_UPDATE_INDEX:
        update_index()




