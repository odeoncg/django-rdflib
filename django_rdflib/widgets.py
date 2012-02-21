from django import forms
from django.forms.util import flatatt
from django.utils.encoding import StrAndUnicode, force_unicode
from django.utils.safestring import mark_safe

class CustomCheckboxInput(forms.CheckboxInput):
	def __init__(self, attrs=None, check_test=lambda s: s != 'False' and bool(s)):
        # check_test is a callable that takes a value and returns True
        # if the checkbox should be checked for that value.
		check_test = lambda s: s != 'False' and bool(s)
		super(CustomCheckboxInput, self).__init__(attrs, check_test)

	def render(self, name, value, attrs=None):
		final_attrs = self.build_attrs(attrs, type='checkbox', name=name)
		try:
			result = self.check_test(value)
		except: # Silently catch exceptions
			result = False

		if result:
			final_attrs['checked'] = 'checked'

		if value not in ('', True, False, 'True', 'False', None):
			# Only add the 'value' attribute if a value is non-empty.
			final_attrs['value'] = force_unicode(value)

		return mark_safe(u'<input%s />' % flatatt(final_attrs))
