from django import template
from django.core.urlresolvers import reverse

from django_rdflib.forms import HIDDEN_FIELDS

register = template.Library()

@register.filter
def get_add_url(field):
    if field.field.widget.attrs.has_key("class"):
        return reverse("add_rdf_object", args=[field.field.widget.attrs["class"],])
    else:
        return ''

def contains_hidden(parser, token):
    error_string = "%r tag must be of format {%%  contains_hidden for field as CONTAINS  %%}" % token.contents.split()[0]
    try:
        split = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(error_string)

    if len(split) == 5:
        return ContainsHiddenNode(split[2], split[4])
    else:
        raise template.TemplateSyntaxError(error_string)
register.tag(contains_hidden)

class ContainsHiddenNode(template.Node):
    def __init__(self, field, contains):
        self.field = template.Variable(field)
        self.contains = contains

    def render(self, context):
        field = self.field.resolve(context)
        contains = False
        try:
            if field.field.widget.attrs['class'].find('hidden') > -1:
                contains = True
        except:
            contains = False
            pass

        context[self.contains] = contains

        return ''
