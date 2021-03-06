import datetime
import os.path
import subprocess

from django.db import models
from django.core.files.base import ContentFile
from django.utils.translation import ugettext as _
from django.utils.hashcompat import md5_constructor
from django.utils.encoding import smart_str

from django.contrib.auth.models import User

try:
    from cStringIO import StringIO
    dir(StringIO) # Placate PyFlakes
except ImportError:
    from StringIO import StringIO

try:
    from PIL import Image
    dir(Image) # Placate PyFlakes
except ImportError:
    import Image

from avatar import AVATAR_STORAGE_DIR, AVATAR_RESIZE_METHOD, \
                   AVATAR_MAX_AVATARS_PER_USER, AVATAR_THUMB_FORMAT, \
                   AVATAR_HASH_USERDIRNAMES, AVATAR_HASH_FILENAMES, \
                   AVATAR_THUMB_QUALITY, AVATAR_USE_IMAGEMAGICK, \
                   AVATAR_IMAGEMAGIC_CONVERT

def avatar_file_path(instance=None, filename=None, size=None, ext=None, new=False):
    tmppath = [AVATAR_STORAGE_DIR]
    if AVATAR_HASH_USERDIRNAMES:
        tmp = md5_constructor(instance.user.username).hexdigest()
        tmppath.extend([tmp[0], tmp[1], instance.user.username])
    else:
        tmppath.append(instance.user.username)
    
    if not filename:
        # Filename already stored in database
        filename = instance.avatar.name
    else:
        filename = filename
        # File doesn't exist yet
        if AVATAR_HASH_FILENAMES:
            (root, oldext) = os.path.splitext(filename)
            filename = md5_constructor(smart_str(filename)).hexdigest()
            filename = filename + oldext
    if size:
        tmppath.extend(['resized', str(size)])
    tmppath.append(os.path.basename(filename))
    filename = os.path.join(*tmppath)

    # ext overrides current extension
    (root, oldext) = os.path.splitext(filename)
    if ext and ext != oldext:
        filename = root + "." + ext
        if new:
            # file does not yet exist, avoid filename collision
            if instance is not None:
                filename = instance.avatar.storage.get_available_name(filename)
            else:
                pass # Not sure how to avoid collisions without storage

    return filename

def find_extension(format):
    format = format.lower()

    if format == 'jpeg':
        format = 'jpg'

    return format

class Avatar(models.Model):
    user = models.ForeignKey(User)
    primary = models.BooleanField(default=False)
    avatar = models.ImageField(max_length=1024, upload_to=avatar_file_path, blank=True)
    date_uploaded = models.DateTimeField(default=datetime.datetime.now)
    
    def __unicode__(self):
        return _(u'Avatar for %s') % self.user
    
    def save(self, force_insert=False, force_update=False):
        avatars = Avatar.objects.filter(user=self.user).exclude(id=self.id)
        if AVATAR_MAX_AVATARS_PER_USER > 1:
            if self.primary:
                avatars = avatars.filter(primary=True)
                avatars.update(primary=False)
        else:
            avatars.delete()
        super(Avatar, self).save(force_insert, force_update)
    
    def thumbnail_exists(self, size):
        return self.avatar.storage.exists(self.avatar_name(size))
    
    def create_thumbnail(self, size, quality=None):
        try:
            orig = self.avatar.storage.open(self.avatar.name, 'rb').read()
            image = Image.open(StringIO(orig))
            args = [AVATAR_IMAGEMAGIC_CONVERT, '-']
        except IOError:
            return # What should we do here?  Render a "sorry, didn't work" img?
        quality = quality or AVATAR_THUMB_QUALITY
        (w, h) = image.size
        if w != size or h != size:
            if w > h:
                diff = (w - h) / 2
                if AVATAR_USE_IMAGEMAGICK:
                    args.extend(['-crop', '%dx%d+%d+%d' % (w, h, diff, 0)])
                else:
                    image = image.crop((diff, 0, w - diff, h))
            elif h > w:
                diff = (h - w) / 2
                if AVATAR_USE_IMAGEMAGICK:
                    args.extend(['-crop', '%dx%d+%d+%d' % (w, h, 0, diff)])
                else:
                    image = image.crop((0, diff, w, h - diff))
            if AVATAR_USE_IMAGEMAGICK:
                args.extend(['-resize', '%dx%d' % (size, size)])
            else:
                image = image.resize((size, size), AVATAR_RESIZE_METHOD)
            if image.mode != "RGB":
                if AVATAR_USE_IMAGEMAGICK:
                    args.extend(['-colorspace', 'RGB'])
                else:
                    image = image.convert("RGB")

            thumb = StringIO()
            if AVATAR_USE_IMAGEMAGICK:
                args.extend(['-quality', str(quality), '%s:-' % AVATAR_THUMB_FORMAT])
                proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                thumb_contents = proc.communicate(input=orig)[0]
                thumb.write(thumb_contents)
            else:
                image.save(thumb, AVATAR_THUMB_FORMAT, quality=quality)
            thumb_file = ContentFile(thumb.getvalue())
        else:
            thumb_file = ContentFile(orig)
        thumb = self.avatar.storage.save(self.avatar_name(size, new=True), thumb_file)
    
    def avatar_url(self, size):
        return self.avatar.storage.url(self.avatar_name(size))
    
    def avatar_name(self, size, new=False):
        ext = find_extension(AVATAR_THUMB_FORMAT)
        return avatar_file_path(
            instance=self,
            size=size,
            ext=ext,
            new=new,
        )
