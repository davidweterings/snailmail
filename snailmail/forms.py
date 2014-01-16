import re

from django import forms
from django.forms import ModelForm
from django.utils.translation import ugettext as _

from snailmail.models import SnailUser

TJP_RE = re.compile(r'^TJP(?i)\d+')

class SubscribeForm(ModelForm):
    class Meta:
        model = SnailUser
        exclude = ['send_post', 'can_receive_post', 'created_on', 'post_history', 'active']


class SendForm(forms.Form):
    id = forms.RegexField(label=_('tjp_id'), min_length=4, regex=TJP_RE) #TODO: maybe create custom TJP form field
    email = forms.EmailField()

    def clean(self):
        cleaned_data = super(SendForm, self).clean()
        tjp_id = cleaned_data.get('id')
        email = cleaned_data.get('email')
        if tjp_id and email:
            valid_user = SnailUser.objects.get_active_user_by_tjp_id_mail(tjp_id, email)
            if not valid_user:
                msg = _('user_not_found')
                self._errors['id'] = self.error_class([msg])
                self._errors['email'] = self.error_class([msg])

                del cleaned_data['id']
                del cleaned_data['email']

        return cleaned_data


class ReceivedForm(forms.Form):
    id = forms.RegexField(label=_('tjp_id'), min_length=4, regex=TJP_RE)
    email = forms.EmailField()
    sender_id = forms.RegexField(min_length=4, regex=TJP_RE)
    message = forms.CharField(widget=forms.Textarea)

    def clean(self):
        cleaned_data = super(ReceivedForm, self).clean()
        tjp_id = cleaned_data.get('id')
        email = cleaned_data.get('email')
        sender_id = cleaned_data.get('sender_id')

        if tjp_id and email and sender_id:
            valid_user = SnailUser.objects.get_active_user_by_tjp_id_mail(tjp_id, email)
            if not valid_user:
                msg = _('user_not_found')
                self._errors['id'] = self.error_class([msg])
                self._errors['email'] = self.error_class([msg])

                del cleaned_data['id']
                del cleaned_data['email']
            sender_id = sender_id[3:]
            posthistory = valid_user.to_user.filter(from_user_id=sender_id, received=False)
            if not posthistory:
                msg = _('no_post_found_between_users')
                self._errors['id'] = self.error_class([msg])
                self._errors['sender_id'] = self.error_class([msg])

                del cleaned_data['id']
                del cleaned_data['sender_id']

        return cleaned_data