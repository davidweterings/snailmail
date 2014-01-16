from django.conf.urls import patterns, url

from snailmail import views

urlpatterns = patterns('',
                       url(r'^$', views.index, name='index'),
                       url(r'^subscribe/$', views.subscribe, name='subscribe'),
                       url(r'^sendpost/$', views.sendpost, name='sendpost'),
                       url(r'^receivedpost/$', views.receivedpost, name='receivedpost')
)

handler500 = 'snailmail.views.custom_error_view'

