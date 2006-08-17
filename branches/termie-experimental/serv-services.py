from twisted.application import internet, service
from twisted.internet import protocol, reactor, defer
from twisted.protocols import basic
from twisted.words.xish import xmlstream
from twisted.python import components
from twisted.words.xish import domish, xpath


from zope.interface import Interface, implements

#interfaces
class IJabberComponent(service.IService, service.IServiceCollection):
    pass
class IJabberFeature(Interface):
    pass
class IJabberAuthenticationFeature(IJabberFeature):
    def checkSupported(self, *args):
        """return a deferred, callback with self on success"""
    def authenticate(self):
        """return a deffered, callback with self on success"""
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
# XXX andy: replace me with jid stuff
class JabberUser(object):
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


#features
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
        if not self.xmlstream.initiating:
            self.xmlstream.removeObserver(self.AUTH_FIELDS_REQUESTED_EVENT,
                                          self.authFieldsRequested)
            self.xmlstream.removeObserver(self.AUTH_FIELDS_PROVIDED_EVENT,
                                          self.authFieldsProvided)
        self.xmlstream = None
       
    #actions
    def authenticate(self):
        self.requestAuthFields()

    def checkSupported(self, *args):
        """return a deferred, callback with self on success, errback"""

    def requestAuthFields(self):
        #iq = IQRequest("get", to=self.xmlstream.otherHost
        pass

    def provideAuthFields(self):
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
        user = JabberUser(self.xmlstream.host, str(elm.query.username), str(elm.query.resource))
        
        resp = IQStanza(type="result", id=elm['id'])
        self.xmlstream.send(resp)
        
        # XXX andy: for now I am just makign a user class, 
        #           there is surely a better way to do this
        self.xmlstream.authenticated(user)



class JabberComponent(service.MultiService):
    implements(IJabberComponent)

    def __init__(self, thisHost):
        service.MultiService.__init__(self)
        self.thisHost = thisHost


class JabberProtocol(xmlstream.XmlStream):
    features = [NonSASLAuthenticationFeature()]

    initialized = False
    intiating = False # whether i started this connection
    otherHost = None
    namespace = "jabber:client"

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

    #actions
    def startStream(self, elm):
        sh = "<stream:stream xmlns:stream='http://etherx.jabber.org/streams'"
        sh += " xmlns='%s'" % self.namespace

        if self.initiating and self.otherHost:
            sh += " to='%s'" % self.otherHost.encode('utf-8')
        elif not self.initiating:
            if self.thisHost:
                sh += " from='%s'" % self.thisHost.encode('utf-8')
            if self.sid:
                sh += " id='%s'" % self.sid

        if self.version >= (1, 0):
            sh += " version='%d.%d'" % (self.version[0], self.version[1])

        sh += '>'
        self.send(sh)

    def authenticate(self):
        auth_features = [f for f in self.features 
                         if IJabberAuthenticationFeature.implementedBy(f)]
        supported = defer.Deferred()
        for f in auth_features:
            supported.addErrback(f.checkSupported)
        #supported.addErrback(self._authenticationNotSupported)
        def auth(a):
            return a.authenticate()

        supported.addCallback(auth)
        #supported.addErrback(self._authenticationFailed)
        return supported


    #callbacks
    def streamConnected(self, elm):
        print "stream connected"

    def streamStarted(self, elm):
        print "stream started, i should respond?"
        if not self.initiating:
            self.send("""<stream:stream xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' from='term.ie' id='44B3CD66'>""")
        else:
            d = self.authenticate()
            d.addCallback(self.authenticated)
    
    def streamEnded(self, elm):
        print "stream ended"

    def streamErrored(self, elm):
        print "stream errored"

    def authenticated(self, *args):
        """some user has authenticated, let's load the rest of the features"""
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



class JabberRemoteComponentProxyProtocol(JabberProtocol):
    def connectionMade(self):
        JabberProtocol.connectionMade(self)
        print "connectioNmade"

class JabberRemoteComponentProxy(JabberComponent):
    """this needs to initiate an xmlstream, and authenticate"""
    protocol = JabberRemoteComponentProxyProtocol
    streams = None

    def __init__(self, thisHost, otherHost, port, timeout=30, bindAddress=None):
        JabberComponent.__init__(self, thisHost)
        service.MultiService.__init__(self)
        self._clientCreator = protocol.ClientCreator(reactor, self.protocol)
        self.streams = {}
        self.otherHost = otherHost
        self.port = port
        self.timeout = timeout
        self.bindAddress = bindAddress

    def startFactory(self):
        print "staraaaaaaaat"
        JabberComponent.startService(self)

    def addService(self, svc):
        """should initiate a new connection to remote server"""
        f = svc.startService
        def wrappedStart():
            d = self._clientCreator.connectTCP(self.host, self.port, 
                                               self.timeout, self.bindAddress)
            d.addCallback(self._protocolSucceeded, svc)
            d.addErrback(self._protocolErrored, svc)
            f()

        wrappedStart.func_name = "startService"
        svc.startService = wrappedStart
        service.MultiService.addService(self, svc)

    def removeService(self, svc):
        """should kill the remote connection"""
        service.MultiService.removeService(self, svc)
        #self.stream[svc].endDocument()

    def _protocolSucceeded(self, p, svc):
        p.thisHost = self.thisHost
        p.otherHost = self.otherHost
        p.initiating = True
        self.streams[svc] = p

    def _protocolErrored(self, reason, svc):
        print "sucks", reason


class JabberCentralRouter(JabberComponent):
    pass



class JabberServerToServerListener(xmlstream.XmlStream):
    def connectionMade(self):
        xmlstream.XmlStream.connectionMade(self)
        print "sizzzllee"

    def onElement(self, elm):
        xmlstream.XmlStream.onElement(self, elm)
        print "elllm", elm.toXml()

class JabberServerToServerClient(xmlstream.XmlStream):
    def connectionMade(self):
        xmlstream.XmlStream.connectionMade(self)
        print "connectionMade"

    def onElement(self, elm):
        xmlstream.XmlStream.onElement(self, elm)
        print "elllm", elm.toXml()

class JabberServerToServerClientFactory(JabberComponent, xmlstream.XmlStreamFactory):
    protocol = JabberServerToServerClient

    def buildProtocol(self, addr):
        self.resetDelay()
        xs = self.protocol()
        xs.factory = self
        return xs

class JabberServerToServerListenerFactory(JabberComponent, xmlstream.XmlStreamFactory):
    protocol = JabberServerToServerListener

    def buildProtocol(self, addr):
        self.resetDelay()
        xs = self.protocol()
        xs.factory = self
        return xs

    
if __name__ == "__builtin__":
    application = service.Application("testComp")
    col = service.IServiceCollection(application)

    center = JabberCentralRouter("localhost")

    center.setServiceParent(col)
        

    baseListener = JabberServerToServerListenerFactory("localhost")
    baseListener.setServiceParent(center)
    internet.TCPServer(5269, baseListener).setServiceParent(center)
    
    proxy = JabberRemoteComponentProxy("localhost", "localhost", 5269)
    proxy.setServiceParent(col)


    #cl = JabberServerToServerClientFactory("localhost")
    #cl.setServiceParent(proxy)
    
    
