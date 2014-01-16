""" Deployment of your django project.
"""

from fabric.api import *

env.hosts = ['127.0.0.1']
env.port = 22 #CHANGEME
env.user = 'test' #CHANGEME
env.password = prompt("SSH password?")

schemamigrate = prompt("Migrate schema? y/n")
if schemamigrate == 'y':
    schemamigrate = True
else:
    schemamigrate = False

new_translations = prompt("Check for translations? y/n")
if new_translations == 'y':
    new_translations = True
else:
    new_translations = False


def set_correct_file_permissions():
    """Everything should be owned by www-data."""
    with cd('/var/www/'):
        sudo('chown -R www-data:www-data tantejanniespostkamer')


def update_django_project():
    """Updates django project, installs new packages, migrates database, checks for translations."""
    with cd('/var/www/tantejanniespostkamer/project'):
        sudo('git pull')

    set_correct_file_permissions()

    with cd('/var/www/tantejanniespostkamer/project'):
        with prefix('source /var/www/tantejanniespostkamer/snailmail/bin/activate'):
            sudo('pip install -r requirements.txt')
            run('python manage.py syncdb')
            run('python manage.py migrate')
            if schemamigrate:
                sudo('python manage.py schemamigration snailmail --auto')
            run('python manage.py migrate snailmail')
            sudo('python manage.py collectstatic --noinput')
            if new_translations:
                sudo('python manage.py makemessages -l en -e=html,py')
                sudo('python manage.py makemessages -l nl -e=html,py')
                sudo('python manage.py compilemessages')

    set_correct_file_permissions()


def restart_services():
    sudo("service uwsgi restart")
    sudo("service nginx restart")


def deploy():
    update_django_project()
    restart_services()