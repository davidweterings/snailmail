from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.utils.translation import ugettext as _
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from tantejanniespostkamer import settings
from snailmail.models import SnailUser, Country, PostHistory
from snailmail.mailer import Mailer

class PostHistorySentInline(admin.StackedInline):
    model = PostHistory
    fk_name = 'from_user'
    extra = 0


class PostHistoryReceivedInline(admin.StackedInline):
    model = PostHistory
    fk_name = 'to_user'
    extra = 0


class SnailUserAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'sent_post_count', 'received_post_count',
                       'post_histories_received_text', 'post_histories_sent_text')
    fieldsets = [
        ('Snailmail Info', {'fields': ['id', 'email', 'sent_post_count', 'received_post_count']}),
        ('NAW', {'fields': ['first_name', 'last_name', 'address', 'zipcode', 'city', 'country', 'website']}),
        ('Other', {'fields': ['country_prefs', 'profile_text', 'is_child', 'active']}),
        ('Post histories text', {'fields': ['post_histories_received_text', 'post_histories_sent_text']}),
    ]
    list_display = ('tjp_id', 'email', 'show_received_count', 'show_sent_count')
    list_filter = ['active', 'is_child']
    search_fields = ['id', 'email']
    date_hierarchy = 'created_on'

    '''
    Add the sent and received post count to the overview
    '''
    def queryset(self, request):
        qs = super(SnailUserAdmin, self).queryset(request)
        qs = qs.extra(select={
            'sent_count': 'SELECT COUNT(*) ' +
                          'FROM snailmail_posthistory ' +
                          'WHERE snailmail_posthistory.from_user_id = snailmail_snailuser.id ' +
                          'AND snailmail_posthistory.received = 1'
        })
        qs = qs.extra(select={
            'received_count': 'SELECT COUNT(*) ' +
                              'FROM snailmail_posthistory ' +
                              'WHERE snailmail_posthistory.to_user_id = snailmail_snailuser.id ' +
                              'AND snailmail_posthistory.received = 1'
        })

        return qs

    def show_received_count(self, inst):
        return inst.received_count

    show_received_count.admin_order_field = 'received_count'

    def show_sent_count(self, inst):
        return inst.sent_count

    show_sent_count.admin_order_field = 'sent_count'

    def post_histories_sent_text(self, inst):
        post_histories_text = '\n\n'.join(str(ph) for ph in inst.from_user.all())

        return post_histories_text

    def post_histories_received_text(self, inst):
        post_histories_text = '\n\n'.join(str(ph) for ph in inst.to_user.all())

        return post_histories_text


def send_reminder(modeladmin, request, queryset):
    for ph in queryset:
        from_user = ph.from_user
        to_user = ph.to_user

        reminder_msg_from = _('reminder_message_from') % {'first_name': from_user.first_name,
                                                          'date_sent': ph.created_on.strftime('%d-%m-%Y'),
                                                          'first_name_to': to_user.first_name}

        reminder_msg_to = _('reminder_message_to') % {'first_name': to_user.first_name,
                                                      'date_sent': ph.created_on.strftime('%d-%m-%Y'),
                                                      'first_name_from': from_user.first_name}

        Mailer.send_html_mail(settings.CONTACT_EMAIL, from_user.email, _('reminder_from_subject'), reminder_msg_from)
        Mailer.send_html_mail(settings.CONTACT_EMAIL, to_user.email, _('reminder_to_subject'), reminder_msg_to)


    queryset.update(reminder_sent=True)


send_reminder.short_description = _('send_reminder_email')


class PostHistoryAdmin(admin.ModelAdmin):
    list_select_related = True
    list_filter = ['received', ('created_on', DateFieldListFilter), 'from_user__is_child', 'reminder_sent']

    list_display = ('from_user', 'to_user', 'received', 'created_on', 'reminder_sent')

    actions = [send_reminder]


class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'shortcut')

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(SnailUser, SnailUserAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(PostHistory, PostHistoryAdmin)

