from twisted.application import internet, service
from twisted.internet import protocol, reactor, defer
from twisted.protocols import basic
from twisted.words.xish import xmlstream
from twisted.python import components
from twisted.words.xish import domish, xpath

from zope.interface import Interface, implements

# interfaces
class IJabberServerService(Interface):
    pass

class IJabberServerFactory(Interface):
    pass

class IJabberFeature(Interface):
    pass

class IJabberAuthenticationFeature(IJabberFeature):
    pass

# some slightly more general implementations of some things...
class IQStanza(domish.Element):
    def __init__(self, type="set", id=None, to=None, children=None):
        domish.Element.__init__(self, (None, "iq"))
        if id is not None:
            self["id"] = id
        else:
            self.addUniqueId()
        if to is not None:
            self["to"] = to
        self["type"] = type
        
        if children is not None:
            for c in children:
                self.addChild(c)

class IQRequest(IQStanza):
    def send(self, xs):
        # XXX andy: i didn't really like that this kept a
        #           reference to the stream, but i don't know
        #           if there was some other reason for there to
        #           be the "to" attibute in the send
        d = defer.Deferred()
        xs.addOnetimeObserver('/iq[@type="result",@id="%s"]'%(self['id']),
                              d.callback)
        xs.addOnetimeObserver('/iq[@type="error",@id="%s"]'%(self['id']),
                              d.errback)
        xs.send(self)

# some helper classes
class JabberUser(object)
    def __init__(self, domain, username=None, resource=None):
        self.domain = domain
        self.username = username
        self.resource = resource

    def __str__(self):
        o = []
        if self.username:
            o.append(self.username + "@")
        o.append(self.domain)
        if self.resource:
            o.append("/" + self.resource)
        return "".join(o)

# features
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
        self.xmlstream.addOnetimeObserver(xmlstream.STREAM_START_EVENT,
                                          self.streamStarted)

    def disassociateWithStream(self, xs):
        self.xmlstream.removeObserver(self.AUTH_FIELDS_REQUESTED_EVENT,
                                      self.authFieldsRequested)
        self.xmlstream.removeObserver(self.AUTH_FIELDS_PROVIDED_EVENT,
                                      self.authFieldsProvided)
        self.xmlstream = None
       
    #callbacks
    def streamStarted(self, elm):
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
        user = JabberUser(self.xmlstream.host, str(elm.query.username), str(elm.query.resource))
        
        resp = IQStanza(type="result", id=elm['id'])
        self.xmlstream.send(resp)
        
        # XXX andy: for now I am just makign a user class, 
        #           there is surely a better way to do this
        self.xmlstream.authenticated(user)

class IMFeature(object):
    implements(IJabberFeature)
    feature = "blah"

    ROSTER_REQUESTED_EVENT = \
        xpath.internQuery("""/iq[@type="get"]/query[@xmlns="jabber:iq:roster"]""")

    def associateWithStream(self, xs):
        self.xmlstream = xs
        self.xmlstream.addObserver(self.ROSTER_REQUESTED_EVENT,
                                   self.rosterRequested)

    def rosterRequested(self, elm):
        #raise NotImplementedError
        print "roster requested!"
        #return
        id = elm['id']
        msg = """<iq from="%s" type="result" id="%s" >
            <query xmlns="jabber:iq:roster">
            <item subscription="from" jid="termie@jabber.org" />
            <item subscription="to" jid="itkovian@jabber.org" >
            <group>.be</group>
            </item>
            <item subscription="both" jid="progrium@gmail.com" >
            <group>sf</group>
            </item>
            <item subscription="both" jid="halsted@gmail.com" >
            <group>sf</group>
            </item>
            <item subscription="both" jid="steven.wittens@gmail.com" >
            <group>.be</group>
            </item>
            <item ask="subscribe" subscription="none" jid="fserrier@gmail.com" >
            <group>.de</group>
            </item>
            <item subscription="both" jid="fserriere@gmail.com" >
            <group>.de</group>
            </item>
            <item subscription="both" jid="mateuszb@gmail.com" >
            <group>...</group>
            </item>
            <item subscription="both" jid="e-gandalf@jabber.org" >
            <group>...</group>
            </item>
            <item subscription="both" jid="elisa@jabber.ccc.de" >
            <group>.nl</group>
            </item>
            <item subscription="both" jid="elisa@jabber.xs4all.nl" >
            <group>.nl</group>
            </item>
            <item subscription="both" jid="gijskruitbosch@gmail.com" >
            <group>.nl</group>
            </item>
            <item subscription="both" jid="okke.formsma@gmail.com" >
            <group>.nl</group>
            </item>
            <item subscription="both" jid="ralphm@ik.nu" >
            <group>.nl</group>
            </item>
            </query>
            </iq>
        """%(str(self.xmlstream.user), id)
        self.xmlstream.send(msg)
        

class JabberServerProtocol(xmlstream.XmlStream):

    host = "term.ie"
    user = None

    features = [NonSASLAuthenticationFeature(),
                IMFeature()]

    initialized = False


    def connectionMade(self):
        # XXX andy: theoretically we don't want to allow anything but
        #           authenticators to fire until after the remote entity
        #           is authenticated
        xmlstream.XmlStream.connectionMade(self)
        
        # initiate the connectionz0r
        self.bootstraps = [
                (xmlstream.STREAM_CONNECTED_EVENT, self.streamConnected),
                (xmlstream.STREAM_START_EVENT, self.streamStarted),
                (xmlstream.STREAM_END_EVENT, self.streamEnded),
                (xmlstream.STREAM_ERROR_EVENT, self.streamErrored),
                ]

        for event, fn in self.bootstraps:
            self.addObserver(event, fn)

        # load up the authentication features
        for f in self.features:
            if IJabberAuthenticationFeature.implementedBy(f.__class__):
                f.associateWithStream(self)

    def send(self, obj):
        if not self.initialized:
            self.transport.write("""<?xml version="1.0"?>\n""")
            self.initialized = True
        xmlstream.XmlStream.send(self, obj)

    #callbacks
    def streamConnected(self, elm):
        print "stream connected"

    def streamStarted(self, elm):
        print "stream started, i should respond?"
        self.send("""<stream:stream xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' from='term.ie' id='44B3CD66'>""")
    
    def streamEnded(self, elm):
        print "stream ended"

    def streamErrored(self, elm):
        print "stream errored"

    def authenticated(self, user):
        """some user has authenticated, let's load the rest of the features"""
        self.user = user
        for f in self.features:
            if IJabberAuthenticationFeature.implementedBy(f.__class__):
                f.disassociateWithStream(self)
            else:
                f.associateWithStream(self)
        # XXX andy: the factory probably does something cool here



    # some meaningless debug stuff
    def dataReceived(self, data):
        #print "data", data
        xmlstream.XmlStream.dataReceived(self, data)
    def onElement(self, element):
        try:
            #print "elem", str(element.toXml())
            xmlstream.XmlStream.onElement(self, element)
        except Exception, e:
            print "Exception!", e
            raise e
    def onDocumentEnd(self):
        print "document end?"
    def connectionLost(self, reason):
        print "LOST!", reason
        xmlstream.XmlStream.connectionLost(self, reason)
        pass

class JabberServerFactoryFromService(xmlstream.XmlStreamFactory):
    implements(IJabberServerFactory)

    protocol = JabberServerProtocol
    
    def __init__(self, service):
        xmlstream.XmlStreamFactory.__init__(self)
        self.service = service


    def buildProtocol(self, addr):
        self.resetDelay()
        xs = self.protocol()
        xs.factory = self
        for event, fn in self.bootstraps:
            xs.addObserver(event, fn)
        return xs


components.registerAdapter(JabberServerFactoryFromService,
                           IJabberServerService,
                           IJabberServerFactory)


class JabberServerService(service.Service):
    """ this is going to hold all the brain bits"""
    implements(IJabberServerService)


if __name__ == "__builtin__":
    application = service.Application('jabz0r')
    j = JabberServerService()
    col = service.IServiceCollection(application)
    internet.TCPServer(5222, IJabberServerFactory(j)).setServiceParent(col)

