import os
import site

site.addsitedir('/var/www/tantejanniespostkamer/snailmail/lib/python2.7/site-packages')

os.environ['DJANGO_SETTINGS_MODULE'] = 'tantejanniespostkamer.settings'

import django.core.handlers.wsgi

application = django.core.handlers.wsgi.WSGIHandler()
