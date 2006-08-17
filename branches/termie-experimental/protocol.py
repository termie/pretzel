from twisted.words.xish import xmlstream
from interfaces import IJabberAuthenticationFeature
from twisted.internet import defer

from twisted.words.protocols.jabber.xmlstream import STREAM_AUTHD_EVENT

from component import JabberComponent

STREAM_CONNECTED_EVENT = xmlstream.STREAM_CONNECTED_EVENT
STREAM_START_EVENT = xmlstream.STREAM_START_EVENT
STREAM_END_EVENT = xmlstream.STREAM_END_EVENT
STREAM_ERROR_EVENT = xmlstream.STREAM_ERROR_EVENT

class JabberProtocol(JabberComponent, xmlstream.XmlStream):
    features = None
    bootstraps = None

    connected = False
    initialized = False
    initiating = False # whether i started this connection
    namespace = None
    authenticated = False
    
    otherHost = None
    thisHost = None
    sid = None
    version = (1, 0)

    def __init__(self, *args, **kw):
        JabberComponent.__init__(self, *args, **kw)
        xmlstream.XmlStream.__init__(self, *args, **kw)
        if not self.features: 
            self.features = []

        if not self.bootstraps:
            self.bootstraps = [
                (STREAM_CONNECTED_EVENT, self.streamConnected),
                (STREAM_START_EVENT, self.streamStarted),
                (STREAM_END_EVENT, self.streamEnded),
                (STREAM_ERROR_EVENT, self.streamErrored),
                (STREAM_AUTHD_EVENT, self.streamAuthenticated),
                ]


    def connectionMade(self, *args, **kw):
        for event, fn in self.bootstraps:
            self.addObserver(event, fn)
        
        #load up the authentication features
        for f in self.features:
            if IJabberAuthenticationFeature.implementedBy(f.__class__):
                f.associateWithStream(self)

        xmlstream.XmlStream.connectionMade(self, *args, **kw)
    
    def onElement(self, elm):
        handled = self.dispatch(elm)
        if not handled:
            self.parent.handle(elm)

    def send(self, obj):
        if not self.initialized:
            self.transport.write("""<?xml version="1.0"?>\n""")
            self.initialized = True
        xmlstream.XmlStream.send(self, obj)

    def startStream(self):
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
        print "attempting to authenticate"
        auth_features = [f for f in self.features 
                         if IJabberAuthenticationFeature.implementedBy(f.__class__)]
        print "auth_features", auth_features
        supported = defer.Deferred()
        for f in auth_features:
            supported.addErrback(f.checkSupported)
        #supported.addErrback(self._authenticationNotSupported)
        def auth(a):
            return a.authenticate()

        supported.addCallback(auth)
        #supported.addErrback(self._authenticationFailed)
        
        #trigger this thing
        supported.errback(defer.fail)

        return supported
    
    #callbacks
    def streamConnected(self, elm):
        print "stream connected"
        self.connected = True
        # load up the authentication features
        for f in self.features:
            if IJabberAuthenticationFeature.implementedBy(f.__class__):
                f.associateWithStream(self)

        # if we are the initiating entity, we send the first stream header
        if self.initiating:
            self.startStream()

    def streamStarted(self, elm):
        print "stream started"
        if not self.initiating:
            self.startStream()
        else:
            d = self.authenticate()
            def authd(a):
                return self.dispatch(None, STREAM_AUTHD_EVENT)

            d.addCallback(authd)

    def streamEnded(self, elm):
        print "stream ended"

    def streamErrored(self, elm):
        print "stream errored"

    def streamAuthenticated(self, elm):
        print "stream authenticated!"
        self.authenticated = True
        for f in self.features:
            if IJabberAuthenticationFeature.implementedBy(f.__class__):
                f.disassociateWithStream(self)
            else:
                f.associateWithStream(self)
        # XXX andy: the factory probably does something cool here

class JabberProtocolFactory(JabberComponent, xmlstream.XmlStreamFactory):
    protocol = JabberProtocol
    
    streams = None

    features = None
    bootstraps = None
    initiating = None
    namespace = None

    thisHost = None
    otherHost = None
    

    def rawIn(self, d):
        print "RECV", repr(d)

    def rawOut(self, d):
        print "SEND", repr(d)

    def __init__(self, *args, **kw):
        #JabberComponent.__init__(self, *args, **kw)
        xmlstream.XmlStreamFactory.__init__(self, *args, **kw)
        if not self.bootstraps: 
            self.bootstraps = []
        if not self.features: 
            self.features = []
        if not self.streams:
            self.streams = []

        print "init bootstarps", self.__class__.__name__, self.bootstraps

    def handle(self, elm):
        print "routing to", self.parent
        self.parent.handle(elm)

    def buildProtocol(self, addr):
        self.resetDelay()
        xs = self.protocol()

        # load up a bunch of protocol stuff
        print "bootstarps", self.bootstraps
        for event, fn in self.bootstraps:
            xs.bootstraps.append((event, fn))

        for f in self.features:
            xs.features.append(f)

        if self.initiating is not None:
            xs.initiating = self.initiating
        if self.namespace is not None:
            xs.namespace = self.namespace
        if self.thisHost is not None:
            xs.thisHost = self.thisHost
        if self.otherHost is not None:
            xs.otherHost = self.otherHost
        #xs.setServiceParent(self)

        xs.factory = self
        self.streams.append(xs)

        xs.rawDataInFn = self.rawIn
        xs.rawDataOutFn = self.rawOut

        return xs 


