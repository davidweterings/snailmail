from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import render

from django.utils.translation import ugettext as _

from snailmail.forms import *
from snailmail.models import SnailUser, PostHistory

from tantejanniespostkamer import settings
from snailmail.mailer import Mailer


def index(request):
    return render(request, 'snailmail/index.html')


def subscribe(request):
    if request.method == 'POST':
        form = SubscribeForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            message = _('subscribed_email') % {'id': new_user.tjp_id, 'first_name': new_user.first_name}
            Mailer.send_html_mail(settings.CONTACT_EMAIL, new_user.email, _('subscribe_subject'), message)

            # find a new address for this user
            to_user = SnailUser.objects.user_that_can_receive_post(new_user)

            if to_user:
                address_msg = _('new_address_email') % {'first_name': new_user.first_name,
                                                        'address': to_user.get_address(),
                                                        'profile': to_user.get_profile()}

                Mailer.send_html_mail(settings.CONTACT_EMAIL, new_user.email, _('new_address_subject'), address_msg)

            return render(request, 'snailmail/subscribed.html', {'thanks': _('thanks_received')})
    else:
        form = SubscribeForm()

    return render(request, 'snailmail/subscribe.html', {'form': form})


def sendpost(request):
    if request.method == 'POST':
        form = SendForm(request.POST)
        if form.is_valid():
            user_id = int(form.cleaned_data['id'][3:])
            user = SnailUser.objects.get(id=user_id)

            if user.can_send_post():
                # find a new address
                to_user = SnailUser.objects.user_that_can_receive_post(user)
                if to_user:
                    address_msg = _('new_address_email') % {
                        'first_name': user.first_name,
                        'address': to_user.get_address(),
                        'profile': to_user.get_profile()}

                    Mailer.send_html_mail(settings.CONTACT_EMAIL, user.email, _('new_address_subject'), address_msg)

                message = _('send_post_success')
            else:
                addresses = ''
                for ph in user.from_user.filter(received=False):
                    addresses = addresses + ph.to_user.get_address() + '\n\n'

                message = _('too_many_open_addresses') % {'addresses': addresses}

            return render(request, 'snailmail/send.html', {'message': message})
    else:
        form = SendForm()

    return render(request, 'snailmail/send.html', {'form': form})


def receivedpost(request):
    if request.method == 'POST':
        form = ReceivedForm(request.POST)
        if form.is_valid():
            to_id = form.cleaned_data['id'][3:]
            from_id = form.cleaned_data['sender_id'][3:]
            posthistory = PostHistory.objects.get(from_user_id=from_id, to_user_id=to_id, received=False)
            posthistory.received = True
            posthistory.received_date = datetime.now()
            posthistory.message = form.cleaned_data['message']
            posthistory.save()

            from_user = posthistory.from_user
            to_user = posthistory.to_user

            thank_msg = _('received_post_sender_message') % {'first_name': from_user.first_name,
                                                             'to_user_name': to_user.get_full_name(),
                                                             'message': posthistory.message}

            Mailer.send_html_mail(settings.CONTACT_EMAIL, from_user.email, _('received_post_thanks_subject'),
                                  thank_msg)

            message = _('post_received_success')
            return render(request, 'snailmail/received.html', {'message': message})
    else:
        form = ReceivedForm()

    return render(request, 'snailmail/received.html', {'form': form})


def custom_error_view(request):
    return HttpResponse(_('general_error'))