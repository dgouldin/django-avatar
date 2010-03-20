import urllib

from django.conf import settings
from django.utils.hashcompat import md5_constructor

from django.contrib.auth.models import User

from avatar import AVATAR_DEFAULT_URL, AVATAR_GRAVATAR_DEFAULT

def get_default_avatar_url(user=None, size=80):
    base_url = getattr(settings, 'STATIC_URL', None)
    if not base_url:
        base_url = getattr(settings, 'MEDIA_URL', '')
    # We'll be nice and make sure there are no duplicated forward slashes
    ends = base_url.endswith('/')
    begins = AVATAR_DEFAULT_URL.startswith('/')
    if ends and begins:
        base_url = base_url[:-1]
    elif not ends and not begins:
        return '%s/%s' % (base_url, AVATAR_DEFAULT_URL)
    return '%s%s' % (base_url, AVATAR_DEFAULT_URL)

def get_primary_avatar(user, size=80):
    if not isinstance(user, User):
        try:
            user = User.objects.get(username=user)
        except User.DoesNotExist:
            return None
    avatars = user.avatar_set.order_by('-date_uploaded')
    primary = avatars.filter(primary=True)
    if primary.count() > 0:
        avatar = primary[0]
    elif avatars.count() > 0:
        avatar = avatars[0]
    else:
        avatar = None
    if avatar:
        if not avatar.thumbnail_exists(size):
            avatar.create_thumbnail(size)
    return avatar

def get_primary_avatar_url(user, size=80):
    avatar = get_primary_avatar(user, size=size)
    if avatar:
        return avatar.avatar_url(size)
    else:
        return None

def get_gravatar_url(user, size=80):
    params = {'s': str(size)}
    if AVATAR_GRAVATAR_DEFAULT:
        params['d'] = AVATAR_GRAVATAR_DEFAULT
    return "http://www.gravatar.com/avatar/%s/?%s" % (
        md5_constructor(user.email).hexdigest(),
        urllib.urlencode(params))
