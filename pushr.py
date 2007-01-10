import xmlrpclib, md5, urllib, urlparse, mimetools, mimetypes, httplib
from elementtree import ElementTree

class FlickrAPI(object):
    api_key = None
    shared_secret = None

    def __init__(self, **kw):
        self.api_key = kw.pop('api_key')
        self.shared_secret = kw.pop('shared_secret')
        super(FlickrAPI, self).__init__(**kw)

        self.xmlrpc = xmlrpclib.ServerProxy(uri='http://api.flickr.com/services/xmlrpc/')

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

        self._callRemote(method, **kw)

    def _callRemote(self, method, **kw):
        fn = getattr(self.xmlrpc, method)
        return fn(kw)

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
