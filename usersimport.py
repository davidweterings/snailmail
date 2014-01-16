import os
import sys
from datetime import datetime

"""Imports existing data from excel to database"""
CURRENT = os.path.dirname(__file__)
sys.path.insert(0, os.path.realpath(os.path.join(CURRENT, '.')))
sys.path.insert(1, os.path.realpath(os.path.join(CURRENT, '.', 'tantejanniespostkamer')))

os.environ['DJANGO_SETTINGS_MODULE'] = "tantejanniespostkamer.settings"

from xlrd import *
from snailmail.models import *

wb = open_workbook('data.xls', formatting_info=True)

users_ws = wb.sheet_by_name('Inschrijvingen')


for user in range(users_ws.nrows):
    if user == 0: continue
    user_id_cell = users_ws.cell(user, 0)
    tjp_id = user_id_cell.value.encode('utf-8')
    if tjp_id == '': continue
    id = int(tjp_id[3:])

    bgx = users_ws.cell_xf_index(user, 0)
    is_child = False
    if bgx == 41:
        is_child = True

    email = users_ws.cell(user, 1).value
    if email == '': continue
    fullname = users_ws.cell(user, 2).value.encode('utf-8')
    fullname = fullname.split(' ', 1)
    first_name = fullname[0]
    if len(fullname) > 1:
        last_name = fullname[1]
    else:
        last_name = ' '
    address = users_ws.cell(user, 3).value.encode('utf-8')
    tempzipcode = str(users_ws.cell(user, 4).value)
    if '.0' in tempzipcode:
        zipcode = tempzipcode[:-2]
    else:
        zipcode = tempzipcode.replace(' ', '')

    city = users_ws.cell(user, 5).value.encode('utf-8')
    country = users_ws.cell(user, 6).value.encode('utf-8')
    nl = Country.objects.get(id=1)
    be = Country.objects.get(id=2)
    if 'Neder' in country:
        country = nl
    else:
        country = be

    print users_ws.cell(user, 7).value
    website = users_ws.cell(user, 7).value.encode('utf-8')
    if 'geen' in website.lower():
        website = ''

    profile_text = users_ws.cell(user, 8).value.encode('utf-8')
    cprefs = users_ws.cell(user, 0).value.encode('utf-8')

    snailuser = SnailUser()
    snailuser.id = id
    snailuser.is_child = is_child
    snailuser.email = email
    snailuser.first_name = first_name
    snailuser.last_name = last_name
    snailuser.address = address
    snailuser.zipcode = zipcode
    snailuser.city = city
    snailuser.country = country
    if website:
        snailuser.website = website
    if profile_text:
        snailuser.profile_text = profile_text

    snailuser.save()

    if cprefs == 'NL':
        snailuser.country_prefs.add(nl)
    elif cprefs == 'BE':
        snailuser.country_prefs.add(be)
    else:
        snailuser.country_prefs.add(nl)
        snailuser.country_prefs.add(be)

    snailuser.save()
    print "Saved user %s" % tjp_id

print "Saved users, now post histories!"

post_ws = wb.sheet_by_name('Verzendlijst')

PostHistory.objects.all().delete()

for ph in range(post_ws.nrows):
    if ph == 0: continue
    from_user_id = 0
    to_user_id = 0
    for cols in range(post_ws.ncols):
        if cols == 0:
            from_user_id = int(post_ws.cell(ph, cols).value)
        elif cols == 1:
            continue
        else:
            if cols % 2 == 0:
                to_user_cell = post_ws.cell(ph, cols).value
                if not to_user_cell:
                    break
                to_user_id = int(to_user_cell)
                cols += 1
                received = str(post_ws.cell(ph, cols).value.encode('utf-8'))
                received_ph = False
                received_date = None
                created_on = datetime.now()
                if received is 'X' or not received:
                    received_ph = True
                    received_date = datetime.now()
                else:
                    created_on = datetime.strptime(received, "%d-%m-%Y")

                post_history = PostHistory()
                post_history.from_user_id = from_user_id
                post_history.to_user_id = to_user_id
                post_history.received = received_ph
                if received_date:
                    post_history.received_date = received_date
                post_history.created_on = created_on
                post_history.notes = 'Geimporteerd'
                post_history.save()

                print "Saved post history from %s to %s received: %s created_on: %s \n row %s col %s" % (
                    from_user_id, to_user_id, post_history.received, post_history.created_on, ph, cols)

print "Done creating posthistories"
