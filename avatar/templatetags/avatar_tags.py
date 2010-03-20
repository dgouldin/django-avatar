from django import template
from django.utils.translation import ugettext as _
from django.utils.importlib import import_module
from django.core.urlresolvers import reverse

from django.contrib.auth.models import User

from avatar import AVATAR_LOADERS
from avatar.util import get_default_avatar_url

register = template.Library()

def avatar_url(user, size=80):
    for loader_path in AVATAR_LOADERS:
        path_parts = loader_path.split('.')
        funcname = path_parts.pop()
        module_path = '.'.join(path_parts)
        module = import_module(module_path)
        url = getattr(module, funcname)(user, size)
        if url:
            return url
    return '' # no avatar found
register.simple_tag(avatar_url)

def avatar(user, size=80):
    if not isinstance(user, User):
        try:
            user = User.objects.get(username=user)
            alt = unicode(user)
            url = avatar_url(user, size)
        except User.DoesNotExist:
            url = get_default_avatar_url()
            alt = _("Default Avatar")
    else:
        alt = unicode(user)
        url = avatar_url(user, size)
    return """<img src="%s" alt="%s" width="%s" height="%s" />""" % (url, alt,
        size, size)
register.simple_tag(avatar)

def primary_avatar(user, size=80):
    """
    This tag tries to get the default avatar for a user without doing any db
    requests. It achieve this by linking to a special view that will do all the 
    work for us. If that special view is then cached by a CDN for instance,
    we will avoid many db calls.
    """
    alt = unicode(user)
    url = reverse('avatar_render_primary', kwargs={'user' : user, 'size' : size})
    return """<img src="%s" alt="%s" width="%s" height="%s" />""" % (url, alt,
        size, size)
register.simple_tag(primary_avatar)

def render_avatar(avatar, size=80):
    if not avatar.thumbnail_exists(size):
        avatar.create_thumbnail(size)
    return """<img src="%s" alt="%s" width="%s" height="%s" />""" % (
        avatar.avatar_url(size), str(avatar), size, size)
register.simple_tag(render_avatar)
