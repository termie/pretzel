from twisted.words.xish import xpath


from interfaces import IJabberAuthenticationFeature, implements
from utility import IQStanza, IQRequest
import xmlstream
from protocol import STREAM_AUTHD_EVENT

class NonSASLAuthenticationFeature(object):
    """JEP-0078"""
    
    implements(IJabberAuthenticationFeature)
    
    feature = "some_feature_id"
    
    # event triggers
    AUTH_FIELDS_REQUESTED_EVENT = \
        xpath.internQuery("""/iq[@type="get"]/query[@xmlns="jabber:iq:auth"]""")
    AUTH_FIELDS_PROVIDED_EVENT = \
        xpath.internQuery("""/iq[@type="set"]/query[@xmlns="jabber:iq:auth"]""")

    def associateWithStream(self, xs):
        """do all the things necessary to register ourselves 
           with the xmlstream
        """
        self.xmlstream = xs
        if not self.xmlstream.initiating:
            self.xmlstream.addOnetimeObserver(xmlstream.STREAM_START_EVENT,
                                              self.streamStarted)

    def disassociateWithStream(self, xs):
        if not self.xmlstream.initiating:
            self.xmlstream.removeObserver(self.AUTH_FIELDS_REQUESTED_EVENT,
                                          self.authFieldsRequested)
            self.xmlstream.removeObserver(self.AUTH_FIELDS_PROVIDED_EVENT,
                                          self.authFieldsProvided)
        self.xmlstream = None
       
    #actions
    def authenticate(self):
        return self.provideAuthFields()

    def checkSupported(self, *args):
        """return a deferred, callback with self on success, errback"""
        return self.requestAuthFields()

    def requestAuthFields(self):
        iq = IQRequest("get")
        q = iq.addElement("query", "jabber:iq:auth")
        q.addElement("username", content=self.xmlstream.name)
        d = iq.send(self.xmlstream)
        d.addCallback(lambda _: self)
        return d

    def provideAuthFields(self):
        iq = IQRequest("set")
        iq.addElement("query", "jabber:iq:auth")
        iq.query.addElement("username", content=self.xmlstream.name)
        iq.query.addElement("digest", content="9f5e1dbdf5b65451bf6502eeda6eaa359319007c")
        if hasattr(self.xmlstream, "resource"):
            iq.query.addElement("resource", content=self.xmlstream.resource)
    
        d = iq.send(self.xmlstream)
        return d
        pass

    #callbacks
    def streamStarted(self, elm):
        if not self.xmlstream.initiating:
            self.xmlstream.addObserver(self.AUTH_FIELDS_REQUESTED_EVENT,
                                    self.authFieldsRequested)
            self.xmlstream.addObserver(self.AUTH_FIELDS_PROVIDED_EVENT,
                                    self.authFieldsProvided)
            

    def authFieldsRequested(self, elm):
        """return the types of auth fields that are supported"""

        print "auth fields requested!"
        resp = IQStanza(type="result", id=elm['id'])
        q = resp.addElement("query", "jabber:iq:auth")
        q.addElement("username", content=str(elm.query.username))
        q.addElement("digest")
        q.addElement("password")
        q.addElement("resource")

        self.xmlstream.send(resp)

    def authFieldsProvided(self, elm):
        """authenticate the user or return an error"""
        # XXX andy: theoretically this defers the actual authentication to
        #           the factory/service
        print "auth fields provided!"
        #user = JabberUser(self.xmlstream.host, str(elm.query.username), str(elm.query.resource))
        

        resp = IQStanza(type="result", id=elm['id'])
        self.xmlstream.send(resp)
        self.xmlstream.dispatch(None, STREAM_AUTHD_EVENT)
        
        # XXX andy: for now I am just makign a user class, 
        #           there is surely a better way to do this
        #self.xmlstream.authenticated()

