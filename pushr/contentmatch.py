"""
Keep track of what flickr photo ID matches what actual file content.
"""

import os, errno

class ContentMatch(object):
    known_photos = None
    tmpFile = None
    dirty = None

    def __init__(self, **kw):
        self.filename = kw.pop('filename')
        super(ContentMatch, self).__init__(**kw)

    def _tmpPath(self):
        id_ = id(self)
        if id_ < 0:
            id_ += 2**32
        return '%s.%d.%d.tmp' % (self.filename,
                                 os.getpid(),
                                 id_)

    def _openRead(self):
        if self.known_photos is not None:
            return

        known_photos = set()
        try:
            old = file(self.filename)
        except IOError, e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise
        else:
            try:
                for line in old:
                    line = line.strip('\n')
                    photo_id, sha1sum = line.split(None, 1)
                    known_photos.add(photo_id)
            finally:
                old.close()

        self.known_photos = known_photos

    def _openWrite(self):
        if self.tmpFile is None:
            tmp = file(self._tmpPath(), 'w')
            known_photos = set()

            try:
                old = file(self.filename)
            except IOError, e:
                if e.errno == errno.ENOENT:
                    pass
                else:
                    raise
            else:
                try:
                    for line in old:
                        line = line.strip('\n')
                        photo_id, sha1sum = line.split(None, 1)
                        known_photos.add(photo_id)
                        print >>tmp, '%s %s' % (photo_id, sha1sum)
                finally:
                    old.close()

            self.tmpFile, self.dirty, self.known_photos = tmp, 0, known_photos

    def add(self, photo_id, sha1sum):
        self._openWrite()
        if photo_id in self.known_photos:
            return

        self.known_photos.add(photo_id)
        print >>self.tmpFile, '%s %s' % (photo_id, sha1sum)
        self.dirty += 1

    def commit(self):
        if self.tmpFile is None:
            return

        tmpFile, self.tmpFile = self.tmpFile, None
        tmpFile.flush()
        os.fsync(tmpFile.fileno())
        tmpFile.close()
        self.dirty = None
        os.rename(self._tmpPath(), self.filename)

    LAZY_COMMIT_THRESHOLD = 10
    def flush(self):
        if (self.dirty is not None
            and self.dirty > self.LAZY_COMMIT_THRESHOLD):
            self.commit()
        else:
            if self.tmpFile is not None:
                self.tmpFile.flush()

    def isKnown(self, photo_id):
        self._openRead()
        return photo_id in self.known_photos
