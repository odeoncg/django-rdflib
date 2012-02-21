from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('django_rdflib.views',
                       url(r'^new/$', 'add_rdf_type_protected', name="add_rdf_type"),
                       url(r'^all/$', 'all_rdf_page_protected', name="all_rdf_page"),
                       url(r'^load_objects/(?P<site_ns_type>[^\/]+)/$', 'load_objects_protected', name="load_objects"),
                       url(r'^(?P<site_ns_type>[^\/]+)/$', 'rdf_type_page', name="rdf_type_page"),
                       url(r'^(?P<site_ns_type>[^\/]+)/new/$', 'change_form_protected', name="add_rdf_object"),
                       url(r'^(?P<site_ns_type>[^\/]+)/delete/$', 'delete_rdf_type', name="delete_rdf_type"),
                       url(r'^(?P<site_ns_type>[^\/]+)/rename/$', 'rename_rdf_type', name="rename_rdf_type"),
                       url(r'^(?P<site_ns_type>[^\/]+)/rdf_type_choices/$', 'rdf_type_choices_protected', name="rdf_type_choices"),
                       url(r'^(?P<site_ns_type>[^\/]+)/(?P<name_slug>[^\/]+)/$', 'change_form_protected', name="edit_rdf_object"),
                       url(r'^(?P<site_ns_type>[^\/]+)/(?P<name_slug>[^\/]+)/predicates/$', 'predicates_page', name="predicates_page"),
                       url(r'^(?P<site_ns_type>[^\/]+)/(?P<name_slug>[^\/]+)/add_field/$', 'add_pred_protected', name="add_pred"),
                       url(r'^(?P<site_ns_type>[^\/]+)/(?P<name_slug>[^\/]+)/add_field/new_form/$', 'add_pred_form_protected', name="add_pred_form"),
                       url(r'^(?P<site_ns_type>[^\/]+)/(?P<name_slug>[^\/]+)/delete/$', 'delete_rdf_protected', name="delete_rdf"),
                       url(r'^(?P<site_ns_type>[^\/]+)/(?P<name_slug>[^\/]+)/(?P<pred>[^\/]+)/rename_predicate/$', 'rename_predicate', name="rename_predicate"),
)
