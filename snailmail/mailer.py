from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

class Mailer(object):
    """Mailer class is responsible for sending emails."""
    @staticmethod
    def send_html_mail(self, from_email, to_email, subject, message):
        """Sends an HTML email, replaces newlines with break lines and strips tags for a text only alternative."""
        html_content = message.replace('\n', '<br />\n')
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        msg.attach_alternative(html_content, 'text/html')
        msg.send()

