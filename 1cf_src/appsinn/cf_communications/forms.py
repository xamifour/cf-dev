# cf-dev/cf_src/appsinn/gmtisp_communications/forms.py
from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import TermsAndConditions

class TermsAndConditionsForm(forms.ModelForm):

    class Meta:
        model = TermsAndConditions
        fields = ['organization', 'locations', 'title', 'version', 'effective_date', 'content', 'notes']
        widgets = {
            'content': CKEditor5Widget(config_name='default'),
            'notes': forms.Textarea(attrs={
                'rows': 10,
                'cols': 78,
                'placeholder': 'Paste your notes here...',
            }),
        }