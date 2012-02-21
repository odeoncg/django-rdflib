from django import forms
from rdflib.namespace import Namespace, RDF
from django_rdflib.settings import *
from django_rdflib.utils import *
from rdflib.term import BNode, URIRef, Literal
from pprint import pprint
from django.forms import CheckboxInput
from django.conf import settings
from userprofile.models import Profile
from userprofile.templatetags.display_helpers import fullname
from django_rdflib.widgets import CustomCheckboxInput

def get_bnode(value):
    if value not in ("", 'None', None):
        value_bnode = BNode(value)
        return value_bnode
    return None

def get_uri(value):
    if value not in ("", 'None', None):
        value_uri = URIRef(value)
        return value_uri
    return None




# global vars #
store, graph = get_rdflib_store_graph()

class ChangeForm(forms.Form):
    def __init__(self, user, site_ns_type, subject=None, literals_nodes=None, name_slug=None, *args, **kwargs):
        if user.is_staff:
            collator_choices = ((profile.user.id, fullname(profile)) for profile in Profile.objects.all())
        else:
            collator_choices = ((profile.user.id, fullname(profile)) for profile in Profile.objects.filter(user=user))
        collator_choices = list(collator_choices)
        if user.is_staff:
            collator_choices = [("", '==========Select=========='),] + collator_choices
        # FIELDS_OVERRIDE needs to be here! tests fail if moved outside of the init function
        FIELDS_OVERRIDE = {
            SITE_NS['collator']: forms.ChoiceField(widget=forms.Select(attrs={'class': 'no_add_new'}), choices=collator_choices, label="Collator"),
            SITE_NS['workspace']: forms.ChoiceField(widget=forms.Select(attrs={'class': 'no_add_new'}), choices=collator_choices, label="Workspace", required=not user.is_staff)
        }
        super(ChangeForm, self).__init__(*args, **kwargs)
        if name_slug:
            pred_list = order_predicates_list(get_predicates(site_ns_type, name_slug), PREDICATE_ORDER.get(site_ns_type, DEFAULT_PREDICATE_ORDER))
        else:
            pred_list = order_predicates_list(get_predicates(site_ns_type), PREDICATE_ORDER.get(site_ns_type, DEFAULT_PREDICATE_ORDER))
        
        for p in pred_list:
            p_str = unicode(p)
            object_type = object_type_for_predicate(p, site_ns_type)

            if FIELDS_OVERRIDE.has_key(p):
                self.fields[p_str]=FIELDS_OVERRIDE[p]
                if p in  (SITE_NS.collator, SITE_NS.workspace) and not user.is_staff:
                    self.fields[p_str].widget.attrs['class'] += 'hidden'
                continue

            if object_type == Literal:
                if is_boolean(p, site_ns_type):
                    self.fields[p_str]=forms.CharField(widget=CustomCheckboxInput(), label=camelcase_to_words(stringify(p_str)))
                else:
                    self.fields[p_str]=forms.CharField(widget=forms.Textarea, label=camelcase_to_words(stringify(p_str)))
            elif object_type == URIRef:
                choices = get_node_choices(p, site_ns_type, user)
                object_type = get_site_ns_type_for_predicate(site_ns_type, p_str)
                self.fields[p_str]=forms.TypedChoiceField(widget=forms.Select(attrs={"class": object_type}), choices=choices, coerce=get_uri, label=camelcase_to_words(stringify(p_str)))
            elif object_type == BNode:
                choices = get_node_choices(p, site_ns_type, user)
                object_type = get_site_ns_type_for_predicate(site_ns_type, p_str)
                self.fields[p_str]=forms.TypedChoiceField(widget=forms.Select(attrs={"class": object_type}), choices=choices, coerce=get_bnode, label=camelcase_to_words(stringify(p_str)))

            self.fields[p_str].required = p in REQUIRED_FIELDS.get(site_ns_type, [])
            
            if object_type != Literal:
                if SITE_NS[object_type] in NO_ADD_NEW and user.is_staff == False:
                    self.fields[p_str].widget.attrs={'class': 'no_add_new'}
        
        for p in pred_list:
            p_str = unicode(p)
            if (p in HIDDEN_FIELDS.get(site_ns_type, []) and not user.is_staff) or p in HIDDEN_FROM_ADMIN_FIELDS.get(site_ns_type, []):
                self.fields[p_str].widget.attrs['class'] += 'hidden'

        if subject:
            for p,o in literals_nodes[0]:
                p_str = unicode(p)
                self.fields[p_str].initial=unicode(o)
            
            for p,o in literals_nodes[1]:
                p_str = unicode(p)
                try:
                    self.fields[p_str].initial=unicode(o)
                except:
                    pass

class PredicateForm(forms.Form):
    name = forms.CharField(required=True)
    value_type = forms.ChoiceField(widget=forms.Select(attrs={"onchange": "javascript:loadRdfObjects(this)"}), required=True)
    value = forms.CharField(widget=forms.Textarea(attrs={"class": 'hide'}), required=True)

    def __init__(self, *args, **kwargs):
        super(PredicateForm, self).__init__(*args, **kwargs)
        choices = [("", "==========Select=========="), ('text', 'Text')]
        for val in all_rdf_types():
            choices.append((stringify(val), stringify(val)))
        self.fields['value_type'].choices = choices

class RdfTypeForm(forms.Form):
    object_type = forms.CharField(required=True, help_text="rdf:type - e.g.: tastyBandersnatchiBrain")
    object_name = forms.CharField(required=True, help_text="You need to create an object for this new type.<br />\
                                  Enter its name in this field. (used for the URL token)")
    object_data_type = forms.BooleanField(required=False, help_text="Should the newly created object have its own unique URL instead of a random identifier? <br />\
                                          (like brain parts have %s/brain_parts/cerebral-cortex/)" % settings.SITE_ATTRIBUTES['hostname'])

class RenameRdfTypeForm(forms.Form):
    rdf_type = forms.CharField(required=True)

class RenamePredicateForm(forms.Form):
    predicate = forms.CharField(required=True)




from django_rdflib.utils import *
store, graph = get_rdflib_store_graph()

def get_node_choices(predicate, site_ns_type, user):
    """
    Returns the SelectField choices (URIRef(pred), unicode(o)) for a given predicate and site_ns_type.
    Tries to see what is the rdf:type of the objects for predicate and then generates the list based on this type.
    If there is no object for that type, generates the list based on other objects of the same site_ns_type value.
    """
    choices = [("", "==========Select==========")]
    value_type = get_site_ns_type_for_predicate(site_ns_type, predicate)
    if value_type.find('#') == -1:
        q = """
        PREFIX site_ns: <%s>
        PREFIX rdf: <%s>
        SELECT DISTINCT ?s WHERE {
            ?s rdf:type site_ns:%s .
            ?s ?p ?o .
        }
        ORDER BY ?s
        """ % (store.namespace('site_ns'), RDF, value_type)
        results = graph.query(q)
    else:
        results=None

    if results:
        labels = get_all_objects_labels(value_type)
        for o, in results:
            o_str = stringify(o)
            workspace = None
            # check workspace
            for s,p,ws in graph.triples([o, SITE_NS.workspace, None]):
                workspace = ws
                break
            if workspace:
                if workspace == str(user.id) or user.is_staff:
                    choices.append((unicode(o), labels.get(unicode(o), o_str)))
            else:
                choices.append((unicode(o), labels.get(unicode(o), o_str)))
    else:
        q = """
        PREFIX site_ns: <%s>
        PREFIX rdf: <%s>
        SELECT DISTINCT ?o WHERE {
            ?s rdf:type site_ns:%s .
            ?s <%s> ?o .
        }
        ORDER BY ?o 
        """ % (store.namespace('site_ns'), RDF, site_ns_type, predicate)
        results = graph.query(q)
        if results:
            for o, in results:
                o_str = stringify(o)
                choices.append((unicode(o), o_str))

    return choices
            
def object_type_for_predicate(p, site_ns_type):
    q = """                    
    PREFIX site_ns: <%s>
    PREFIX rdf: <%s>
    SELECT ?o WHERE {
        ?s rdf:type site_ns:%s .
        ?s <%s> ?o .
    }
    ORDER BY ?o
    LIMIT 1
    """ % (store.namespace('site_ns'), RDF, site_ns_type, p)

    for o, in graph.query(q):
        return type(o)
                
def is_boolean(p, site_ns_type):
    q = """                    
    PREFIX site_ns: <%s>
    PREFIX rdf: <%s>
    SELECT DISTINCT ?o WHERE {
        ?s rdf:type site_ns:%s .
        ?s <%s> ?o .
    }
    ORDER BY ?o
    """ % (store.namespace('site_ns'), RDF, site_ns_type, p)

    for o, in graph.query(q):
        if unicode(o) not in BOOL_VALUES.keys():
            return False

    return True
