from twisted.trial import unittest
import os

from pushr import contentmatch

class ContentMatchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = self.mktemp()
        os.mkdir(self.tmp)
        self.path = os.path.join(self.tmp, 'images.flickr.sha1')

    def check(self, want):
        f = file(self.path)
        got = f.read()
        f.close()
        self.assertEquals(got, want)

    def create(self, data):
        f = file(self.path, 'w')
        f.write(data)
        f.close()

    def test_isKnown_empty(self):
        c = contentmatch.ContentMatch(filename=self.path)
        got = c.isKnown(photo_id='1232')
        self.assertEquals(got, False)

    def test_isKnown_one(self):
        self.create('213214 7580434a941c0bd025575baf19f17057fb713ca4\n')
        c = contentmatch.ContentMatch(filename=self.path)
        got = c.isKnown(photo_id='213214')
        self.assertEquals(got, True)

    def test_isKnown_two(self):
        self.create('213214 7580434a941c0bd025575baf19f17057fb713ca4\n'
                    +'213215 782c340301f02620e04d18f6bc2876f7552f17db\n'
                    )
        c = contentmatch.ContentMatch(filename=self.path)
        got = c.isKnown(photo_id='213215')
        self.assertEquals(got, True)
        got = c.isKnown(photo_id='213214')
        self.assertEquals(got, True)

    def test_commit_empty(self):
        c = contentmatch.ContentMatch(filename=self.path)
        c.commit()
        self.failIf(os.path.exists(self.path))

    def test_create_one(self):
        c = contentmatch.ContentMatch(filename=self.path)
        c.add(photo_id='213214',
              sha1sum='7580434a941c0bd025575baf19f17057fb713ca4')
        c.commit()
        self.check('213214 7580434a941c0bd025575baf19f17057fb713ca4\n')

    def test_commit_double(self):
        c = contentmatch.ContentMatch(filename=self.path)
        c.add(photo_id='213214',
              sha1sum='7580434a941c0bd025575baf19f17057fb713ca4')
        c.commit()
        self.check('213214 7580434a941c0bd025575baf19f17057fb713ca4\n')
        c.commit()
        self.check('213214 7580434a941c0bd025575baf19f17057fb713ca4\n')
