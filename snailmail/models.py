from datetime import datetime

from django.core.mail import mail_admins
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _

class SnailUserManager(models.Manager):
    def user_that_can_receive_post(self, snail_user):
        country_preference_ids = ','.join(str(int(id)) for id in snail_user.country_prefs.values_list('id', flat=True))
        country_preference_ids = country_preference_ids.rstrip(',')

        sql = """SELECT su.id,
                        # post rating is calculated as follows:
                        # (number of sent posts) - (number of received posts) - (penalty for users with no post)
                        (
                            (
                              SELECT COUNT(*)
                              FROM snailmail_posthistory
                              WHERE from_user_id = su.id
                              AND received = 1
		                    )
                            -
		                    (
                              SELECT COUNT(*)
                              FROM snailmail_posthistory
                              WHERE to_user_id = su.id
                              AND received = 1
		                    )
		                    -
		                    (
		                        CASE WHEN EXISTS (
		                                            SELECT id
		                                            FROM snailmail_posthistory
		                                            WHERE from_user_id = su.id OR to_user_id = su.id
		                                            LIMIT 1
		                                         )
								    THEN 0
			                        ELSE 1000
			                    END
		                    )
                        ) AS post_rating,
                        # if user has not received any post their last_received_post_date is set so it is ranked last
                        COALESCE((
                            SELECT received_date
                            FROM snailmail_posthistory
                            WHERE to_user_id = su.id
                            AND received = 1
                            ORDER BY received_date
                            LIMIT 1
                        ), '2100-01-01 00:00:00') AS last_received_post_date
                        FROM snailmail_snailuser AS su
                        WHERE su.active = 1
                        AND su.id != %s
                        AND su.is_child = %s
                        AND su.country_id IN (%s)
                        AND su.id NOT IN
                            (	#user has never sent or received post from the other user
                                SELECT su.id
                                FROM snailmail_posthistory
                                WHERE (from_user_id = su.id AND to_user_id = %s) OR
                                      (from_user_id = %s AND to_user_id = su.id)
                            )
                        AND (  # address is not in more than the max nr of open posts
                                SELECT COUNT(*)
                                FROM snailmail_posthistory
                                WHERE to_user_id = su.id
                                AND received = 0
                            ) < %s
                        AND (   # user has sent at least one post to someone else
                                SELECT COUNT(*)
                                FROM snailmail_posthistory
                                WHERE from_user_id = su.id
                                AND received = 1
                            ) >= 1
                    ORDER BY post_rating DESC, last_received_post_date ASC, su.created_on ASC
                    LIMIT 1""" % (snail_user.id, snail_user.is_child, country_preference_ids, snail_user.id,
                                  snail_user.id, SnailUser.MAX_UNSENT_POST)

        viable_user = list(self.raw(sql))
        if len(viable_user) > 0:
            viable_user_id = viable_user[0].id
            to_snail_user = SnailUser.objects.get(pk=viable_user_id)
            posthistory = PostHistory(from_user=snail_user, to_user=to_snail_user)
            posthistory.save()

            return to_snail_user
        else:
            mail_admins('No viable user found', 'for user %s' % snail_user)
            return None

    def get_active_user_by_tjp_id_mail(self, tjp_id, email):
        try:
            return SnailUser.objects.filter(id=tjp_id[3:], email=email, active=True).get()
        except ObjectDoesNotExist:
            return None


class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    shortcut = models.CharField(max_length=3, unique=True)

    class Meta:
        verbose_name_plural = 'Countries'

    def __unicode__(self):
        return self.name


class SnailUser(models.Model):
    # maximum number of unset post a user can have before requesting another address
    MAX_UNSENT_POST = 5

    first_name = models.CharField(_('first_name'), max_length=100)
    last_name = models.CharField(_('last_name'), max_length=100, blank=True)
    address = models.CharField(_('address'), max_length=200)
    zipcode = models.CharField(_('zipcode'), max_length=6)
    city = models.CharField(_('city'), max_length=100)
    country = models.ForeignKey(Country, verbose_name=_('country'))
    website = models.URLField(_('website_blog'), blank=True)
    email = models.EmailField(_('user_email'), db_index=True, unique=True)
    country_prefs = models.ManyToManyField(Country, related_name='country_prefs', verbose_name=_('country_preferences'))
    post_history = models.ManyToManyField('self', through='PostHistory', symmetrical=False, related_name='posts')
    profile_text = models.TextField(_('profile_text'), blank=True)
    created_on = models.DateTimeField(default=datetime.now)
    active = models.BooleanField(_('active'), db_index=True, default=True)
    is_child = models.BooleanField(_('is_child'), db_index=True, default=False)

    objects = SnailUserManager()

    def _get_received_post_count(self):
        return self.to_user.filter(received=True).count()

    received_post_count = property(_get_received_post_count)

    def _get_sent_post_count(self):
        return self.from_user.filter(received=True).count()

    sent_post_count = property(_get_sent_post_count)

    @property
    def tjp_id(self):
        return 'TJP{0}'.format(self.id)

    def get_address(self):
        return '%s \n %s \n %s %s %s' % (
            self.first_name + ' ' + self.last_name, self.address, self.zipcode, self.city, self.country.name)

    def get_full_name(self):
        fullname = self.first_name

        if self.last_name:
            fullname += ' ' + self.last_name

        return fullname

    def get_profile(self):
        profile_text = ''

        if self.profile_text:
            profile_text += self.profile_text + '\n'

        if self.website:
            profile_text += self.website + '\n'

        return profile_text

    def can_send_post(self):
        """Determines if a user can receive a new address, depends on amount of unsent post the user has."""
        max_unreceived_open = self.from_user.filter(received=False).count() < 2
        max_unsent_post = self.sent_post_count >= 2 and \
                          self.from_user.filter(received=False).count() < self.MAX_UNSENT_POST

        return max_unreceived_open or max_unsent_post

    class Meta:
        ordering = ['-created_on']

        index_together = [['id', 'active']]

    def __unicode__(self):
        return u"%s: %s %s" % (self.tjp_id, self.first_name, self.last_name)


class PostHistory(models.Model):
    """PostHistory stores everything related to the snail mail a user sends to another user."""
    from_user = models.ForeignKey(SnailUser, db_index=True, related_name='from_user')
    to_user = models.ForeignKey(SnailUser, db_index=True, related_name='to_user')
    received = models.BooleanField(db_index=True, default=False)
    received_date = models.DateTimeField(db_index=True, blank=True, null=True)
    message = models.TextField(_('note_from_receiver'), blank=True)
    created_on = models.DateTimeField(_('date_created'), default=datetime.now)
    reminder_sent = models.BooleanField(_('reminder_sent_to_user'), default=False)
    sender_has_sent_post = models.BooleanField(_('sender_has_sent_post'), default=False)
    receiver_not_received = models.BooleanField(_('receiver_not_received'), default=False)
    notes = models.TextField(_('notes'), blank=True)

    class Meta:
        ordering = ['-created_on']
        verbose_name_plural = 'Post histories'

        unique_together = ('from_user', 'to_user')
        index_together = (('from_user', 'received'),
                          ('to_user', 'received'),
                          ('to_user', 'received', 'received_date'))

    def __unicode__(self):
        return u"%s %s, received: %s, received_date: %s" % (self.from_user, self.to_user,
                                                            self.received, self.received_date)