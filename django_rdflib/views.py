from django.utils import simplejson
from django_rdflib.settings import *
from django import forms
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.conf import settings
from django.core.urlresolvers import reverse
from rdflib.term import BNode, URIRef, Literal
from django.forms.fields import TypedChoiceField
from pprint import pprint
from django_rdflib.utils import *
from django_rdflib.forms import *
from userprofile.models import Profile
from misc.data_migration import *
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from workspaces.utils import *

@login_required
def change_form(request, site_ns_type, name_slug=None, template='django_rdflib/change_form.html', extra_vars={}):
    store, graph = get_rdflib_store_graph()
    
    if SITE_NS[site_ns_type] in NO_ADD_NEW and not request.user.is_staff:
        raise Http404

    url_alias = URL_ALIASES.get(site_ns_type, None)
    if request.REQUEST.has_key("_popup"):
        is_popup = True
    else:
        is_popup= False

    page_title = camelcase_to_words(site_ns_type)
    get_next = request.GET.get('next', '') 
    if get_next != '':
        redirect_urls = get_next.split(",")
    else:
        redirect_urls = []

    if name_slug:
        subject = get_subject(site_ns_type, name_slug)
        for s,p,o in graph.triples((subject, SITE_NS['collator'], None)):
            if unicode(o) != unicode(request.user.id) and not request.user.is_staff:
                raise Http404
            break
    else:
        subject = None

    if subject:
        literals, nodes = get_literals_and_nodes(subject)
        literals_nodes = (literals, nodes)
    else:
        literals_nodes = None
        literals = nodes = None

    if request.method == 'POST':
        if name_slug:
            form = ChangeForm(request.user, site_ns_type, subject, literals_nodes, name_slug, request.POST)
        else:
            form = ChangeForm(request.user, site_ns_type, subject, literals_nodes, None, request.POST)

        if form.is_valid():
            subject = handle_rdf_form(request, site_ns_type, subject, form)

            if site_ns_type not in DONT_UPDATE_INDEX:
                update_index()

            redirect_name_slug = stringify(subject)

            if url_alias:
                redirect_url = "%s" % reverse(url_alias, args=[redirect_name_slug])
            else:
                redirect_url = reverse('edit_rdf_object', args=[site_ns_type, redirect_name_slug])

            if is_popup:
                return HttpResponse('<script type="text/javascript">opener.dismissAddAnotherPopup(window, "%s", "%s");</script>' % (subject, stringify(subject)))

            return HttpResponseRedirect(redirect_url)
        else:
            print __file__, form.errors
    else:
        if name_slug:
            form = ChangeForm(request.user, site_ns_type, subject, literals_nodes, name_slug)
        else:
            form = ChangeForm(request.user, site_ns_type, subject, literals_nodes)


    custom_context = rdf_representation(request, site_ns_type, subject, form, literals_nodes)
    custom_context.update(locals())

    return render_to_response(template, custom_context, context_instance=RequestContext(request))

@staff_member_required
def change_form_protected(*args, **kwargs):
    return change_form(*args, **kwargs)

def add_pred(request, site_ns_type, name_slug):
    url_alias = URL_ALIASES.get(site_ns_type, None)
    if request.method == 'POST':
        nb = request.POST.get('form_count', '')
        if nb:
            for i in range(1, int(nb) + 1):
                form = PredicateForm(request.POST, prefix=i)
                if form.is_valid():
                    form_data = form.cleaned_data
                    if (form_data['name'] == '') or \
                        (form_data['value_type'] == '') or \
                        (form_data['value'] == ''):
        
                        pass
                    else:
                        subject = get_subject(site_ns_type, name_slug)
                        add_predicate(subject, form_data, site_ns_type)
                        messages.add_message(request, messages.SUCCESS, 'The new field was created successfuly.')

        if url_alias:
            redirect_url = "%sedit/" % reverse(url_alias, args=[name_slug])
        else:
            redirect_url = reverse('edit_rdf_object', args=[site_ns_type, name_slug])

        return HttpResponseRedirect(redirect_url)
    else:
        form = PredicateForm(prefix="1")

    return render_to_response('django_rdflib/add_pred.html', locals(), context_instance=RequestContext(request))

@staff_member_required
def add_pred_protected(*args, **kwargs):
    return add_pred(*args, **kwargs)

def add_pred_form(request, site_ns_type, name_slug):
    prefix = request.GET.get('prefix', None)
    if prefix:
        form = PredicateForm(prefix=prefix)
        

    return render_to_response('django_rdflib/add_pred_form.html', locals(), context_instance=RequestContext(request))
    
@staff_member_required
def add_pred_form_protected(*args, **kwargs):
    return add_pred_form(*args, **kwargs)

def rdf_type_choices(request, site_ns_type):
    prefix = request.GET.get('prefix', '1')
    labels = get_all_objects_labels(site_ns_type)
    choices = []
    for obj in get_objects_for_site_ns_type(site_ns_type):
        choices.append((obj, labels.get(unicode(obj), stringify(obj))))
    rdf_objects = forms.ChoiceField(choices=choices).widget.render('%s-value' % prefix, None, attrs={'id': "id_%s-value" % prefix})
    return render_to_response('django_rdflib/rdf_type_choices.html', locals(), context_instance=RequestContext(request))

@staff_member_required
def rdf_type_choices_protected(*args, **kwargs):
    return rdf_type_choices(*args, **kwargs)

def delete_rdf(request, site_ns_type, name_slug):
    store, graph = get_rdflib_store_graph()
    url_alias = URL_ALIASES.get(site_ns_type, None)
    if url_alias:
        subject = URIRef('%s%s' % (settings.SITE_NAME, reverse(url_alias, args=[name_slug])))
    else:
        subject = SITE_NS[name_slug]
    if not subject_exists(subject):
        subject = BNode(name_slug)
    if not subject_exists(subject):
        raise Http404
    
    page_title = camelcase_to_words(site_ns_type)
    
    if request.method == 'POST':
        triples_list = []
        for s,p,o in graph.triples((None, None, subject)):
            triples_list.append([s, p, o])
        delete_triples(triples_list)
        delete_subject(subject)
        messages.add_message(request, messages.SUCCESS, 'The %s object was deleted successfuly.' % site_ns_type)

        if site_ns_type not in DONT_UPDATE_INDEX:
            update_index()
        return HttpResponseRedirect('/')
    form = forms.Form()
    return render_to_response('django_rdflib/delete_rdf.html', locals(), context_instance=RequestContext(request))

@staff_member_required
def delete_rdf_type(request, site_ns_type):
    store, graph = get_rdflib_store_graph()
    page_title = camelcase_to_words(site_ns_type)
    if request.method == 'POST':
        delete_rdf_type_triples(site_ns_type)

        return HttpResponseRedirect(reverse('all_rdf_page'))

    form = forms.Form()

    return render_to_response('django_rdflib/delete_rdf_type.html', locals(), context_instance=RequestContext(request))

@staff_member_required
def rename_rdf_type(request, site_ns_type):
    store, graph = get_rdflib_store_graph()
    type_words = camelcase_to_words(site_ns_type)
    page_title = type_words
    if request.method == 'POST':
        form = RenameRdfTypeForm(request.POST)
        if form.is_valid():
            rename_rdf_type_triples(site_ns_type, form.cleaned_data['rdf_type'])

        return HttpResponseRedirect(reverse('all_rdf_page'))
    else:
        form = RenameRdfTypeForm(initial={'rdf_type': type_words})

    return render_to_response('django_rdflib/rename_rdf_type_and_predicate.html', locals(), context_instance=RequestContext(request))

@staff_member_required
def delete_rdf_protected(*args, **kwargs):
    return delete_rdf(*args, **kwargs)

def add_rdf_type(request):
    if request.method == 'POST':
        form = RdfTypeForm(request.POST)
        if form.is_valid():
            form_data = form.cleaned_data
            object_type = slugify(form_data['object_type'])
            object_name = form_data['object_name']
            object_data_type = form_data['object_data_type']
            if object_data_type:
                data_type = URIRef
            else:
                data_type = BNode

            subject = create_subject(object_type, object_name, data_type)
            commit_triples()

            messages.add_message(request, messages.SUCCESS, 'The new object and the associated object type were created successfuly. You can now edit the object and add new fields to it, or add more objects of this type.')

            return HttpResponseRedirect(reverse('edit_rdf_object', args=[object_type, stringify(subject)]))

    else:
        form = RdfTypeForm(initial={'object_data_type': True})

    return render_to_response('django_rdflib/add_rdf_type.html', locals(), context_instance=RequestContext(request))

@staff_member_required
def add_rdf_type_protected(*args, **kwargs):
    return add_rdf_type(*args, **kwargs)

def all_rdf_page(request):
    from thesaurus.settings import URL_ALIASES_THESAURUS

    rdf_types = all_rdf_types()
    rdf_types_list_ordered = []
    for obj in rdf_types:
        # stringify returns the last node in a URI 
        if stringify(obj) not in rdf_types_list_ordered:
            rdf_types_list_ordered.append(stringify(obj))

    rdf_types_list_ordered.sort(key=lambda x: x.lower())
    all_rdf_dict = {}
    for obj in rdf_types_list_ordered:
        rdf_obj_count = get_objects_for_site_ns_type_count(stringify(obj))
        all_rdf_dict[stringify(obj)] = (reverse('rdf_type_page', args=[stringify(obj)]), rdf_obj_count)

    sorted_dict_vals = sorted(all_rdf_dict.iterkeys(), key=lambda x: x.lower())
    vals_and_add_new = []
    max_item_size = 0
    for item in sorted_dict_vals:
        url_alias = URL_ALIASES_THESAURUS.get(item, None)
        if url_alias:
            add_new_link = reverse(url_alias)
        else:
            add_new_link = reverse('add_rdf_object', args=[item])

        if (item, add_new_link) not in vals_and_add_new:
            vals_and_add_new.append((item, add_new_link))

        if len(item) > max_item_size:
            max_item_size = len(item)

    return render_to_response('django_rdflib/all_rdf_page.html', locals(), context_instance=RequestContext(request))

@staff_member_required
def all_rdf_page_protected(*args, **kwargs):
    return all_rdf_page(*args, **kwargs)

@staff_member_required
def rdf_type_page(request, site_ns_type):
    all_objects_dict, rdf_obj_count = get_objects_for_site_ns_type_and_link_dict(site_ns_type)
    sorted_dict_vals = sorted(all_objects_dict.iterkeys(), key=lambda x: x.lower())

    return render_to_response('django_rdflib/rdf_type_page.html', locals(), context_instance=RequestContext(request))

def load_objects(request, site_ns_type):
    all_objects = get_objects_for_site_ns_type(site_ns_type)
    all_objects_dict = {}
    for obj in all_objects:
        all_objects_dict[get_label(obj)] = reverse('edit_rdf_object', args=[site_ns_type, stringify(obj)])

    return render_to_response('django_rdflib/load_objects.html', locals(), context_instance=RequestContext(request))

@staff_member_required
def load_objects_protected(*args, **kwargs):
    return load_objects(*args, **kwargs)

@staff_member_required
def predicates_page(request, site_ns_type, name_slug):
    subject = get_subject(site_ns_type, name_slug)
    predicates_list = []
    #for s,p,o in graph.triples((subject, None, None)):
        #if (camelcase_to_words(stringify(p)), reverse('rename_predicate', args=[site_ns_type, name_slug, stringify(p)])) not in predicates_list:
            #predicates_list.append((camelcase_to_words(stringify(p)), reverse('rename_predicate', args=[site_ns_type, name_slug, stringify(p)])))

    pred_list = order_predicates_list(get_predicates(site_ns_type), PREDICATE_ORDER.get(site_ns_type, DEFAULT_PREDICATE_ORDER))
    for pred in pred_list:
        predicates_list.append((camelcase_to_words(stringify(pred)), reverse('rename_predicate', args=[site_ns_type, name_slug, stringify(pred)])))
    return render_to_response('django_rdflib/predicates_page.html', locals(), context_instance=RequestContext(request))

@staff_member_required
def rename_predicate(request, site_ns_type, name_slug, pred):
    store, graph = get_rdflib_store_graph()
    pred_words = camelcase_to_words(pred)
    page_title = pred_words
    if request.method == 'POST':
        form = RenamePredicateForm(request.POST)
        if form.is_valid():
            rename_predicate_func(site_ns_type, name_slug, pred, form.cleaned_data['predicate'])

        return HttpResponseRedirect(reverse('predicates_page', args=[site_ns_type, name_slug]))
    else:
        form = RenamePredicateForm(initial={'predicate': page_title})

    return render_to_response('django_rdflib/rename_rdf_type_and_predicate.html', locals(), context_instance=RequestContext(request))
