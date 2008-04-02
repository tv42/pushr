import md5, urllib, urlparse, mimetools, mimetypes, httplib
from xml.etree import ElementTree
import simplejson

class FlickrError(Exception):
    """Flickr API failed"""

    def __str__(self):
        return '%s: %r' % (self.__doc__, self.args[0])

class FlickrAPI(object):
    api_key = None
    shared_secret = None

    def __init__(self, **kw):
        self.api_key = kw.pop('api_key')
        self.shared_secret = kw.pop('shared_secret')
        super(FlickrAPI, self).__init__(**kw)

    def sign(self, **kw):
        m = md5.new()
        m.update(self.shared_secret)
        params = kw.items()
        params.sort()
        for k,v in params:
            m.update(k)
            m.update(str(v))
        return m.hexdigest()

    def callRemote(self, method, **kw):
        kw['api_key'] = self.api_key
        kw['api_sig'] = self.sign(**kw)

        return self._callRemote(method, **kw)

    def _callRemote(self, method, **kw):
        kw.update(dict(
                method=method,
                format='json',
                nojsoncallback=1,
                ))
        query = urllib.urlencode(kw)
        url = 'http://api.flickr.com/services/rest/?%s' % query
        c = urllib.urlopen(url)
        obj = simplejson.load(c)
        c.close()
        if obj['stat'] != 'ok':
            raise FlickrError(obj)
        return obj

    def getFrobURL(self, frob, mode='write'):
        data = dict(
            api_key=self.api_key,
            perms=mode,
            frob=frob,
            )
        data['api_sig'] = self.sign(**data)
        query = urllib.urlencode(data)
        return urlparse.urlunsplit([
            'http',
            'flickr.com',
            '/services/auth/',
            query,
            '',
            ])

    def getToken(self, frob):
        r = self.callRemote('flickr.auth.getToken', frob=frob)
        return r

    def upload(self,
               fp,
               auth_token,
               filename=None,
               title=None,
               description=None,
               tags=None,
               is_public=None,
               is_friend=None,
               is_family=None):
        kw = {}
        if title is not None:
            kw['title'] = title
        if description is not None:
            kw['description'] = description
        if tags is not None:
            kw['tags'] = tags
        if is_public is not None:
            kw['is_public'] = is_public
        if is_friend is not None:
            kw['is_friend'] = is_friend
        if is_family is not None:
            kw['is_family'] = is_family

        kw['async'] = '1'
        kw['api_key'] = self.api_key
        kw['auth_token'] = auth_token
        kw['api_sig'] = self.sign(**kw)

        boundary = mimetools.choose_boundary()
        parts = []
        for k,v in kw.items():
            parts.append('\r\n'.join([
                'Content-Disposition: form-data; name="%s"' % k,
                '',
                v,
                ]))

        if filename is None:
            filename = 'upload.jpg'
        photoData = ('\r\n--'+boundary+'\r\n'
                     +'Content-Disposition: form-data; name="photo"; filename="%s"\r\n' % filename
                     +'Content-Type: image/jpeg\r\n'
                     +'\r\n'
                     +fp.read()
                     )

        data = ('--'+boundary+'\r\n'
                +('\r\n--%s\r\n'%boundary).join(parts)
                +photoData
                +'\r\n--%s--\r\n'%boundary
                )

        c = httplib.HTTPConnection('api.flickr.com')
        c.request('POST',
                  '/services/upload/',
                  data,
                  {
            'Content-Type': 'multipart/form-data; boundary=%s' % boundary,
            })
        response = c.getresponse()
        if response.status != 200:
            raise RuntimeError('TODO pretty error handling')
        tree = ElementTree.parse(response)
        c.close()
        ticket = tree.findtext('ticketid')
        if ticket is None:
            print 'No ticket'
            print ElementTree.tostring(tree)
        return ticket

    def checkTickets(self, *tickets):
        tickets = set(tickets)
        ticketstring = ','.join([str(tkt) for tkt in tickets])
        response = self.callRemote('flickr.photos.upload.checkTickets',
                                   tickets=ticketstring)
        tree = ElementTree.fromstring(response)

        for ticket in tree.findall('ticket'):
            ticket_id = ticket.attrib['id']
            if ticket_id not in tickets:
                # unexpected response, ignore
                continue

            if ticket.attrib['complete'] == '0':
                # just skip unfinished tickets
                continue
            elif ticket.attrib['complete'] == '1':
                # complete
                photo_id = ticket.attrib['photoid']
                yield (ticket_id, photo_id)
                tickets.remove(ticket_id)
            elif ticket.attrib['complete'] == '2':
                # failed
                yield (ticket_id, None)
                tickets.remove(ticket_id)
            else:
                raise RuntimeError('Bad response from FlickrAPI: '
                                   +'checkTickets output: %r'
                                   % ElementTree.tostring(ticket))

    def people_findByUsername(self, username):
        r = self._callRemote(
            'flickr.people.findByUsername',
            api_key=self.api_key,
            username=username,
            )
        r = r['user']
        r['username'] = r['username']['_content']
        return r

    def people_getPublicPhotos(
        self,
        user_id,
        **kw
        ):
        r = self._callRemote(
            'flickr.people.getPublicPhotos',
            api_key=self.api_key,
            user_id=user_id,
            **kw
            )
        r = r['photos']
        return r

    def photos_getSizes(self, photo_id):
        r = self._callRemote(
            'flickr.photos.getSizes',
            api_key=self.api_key,
            photo_id=photo_id,
            )
        r = r['sizes']
        return r
