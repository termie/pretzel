from twisted.words.xish import xpath

from protocol import JabberProtocol, JabberProtocolFactory, STREAM_AUTHD_EVENT
from utility import IQRequest, IQStanza

NS_ROUTE = "http://term.ie/ns/xmpp/route"
NS_COMPONENT = "http://term.ie/ns/xmpp/component" 


class JabberComponentProxy(JabberProtocol):
    namespace = NS_COMPONENT

    ROUTE_ADDED = xpath.internQuery("/iq/route/add")
    ROUTE_REMOVED = xpath.internQuery("/iq/route/remove")
    
    # this is the routing bits
    def _handle(self, elm):
        self.send(elm)

    def _onElement(self, elm):
        #print "routing to", self.parent
        self.factory.handle(elm)


    #def addObserver(self, event, observerfn, *args, **kw):
    #    print "add observer!", event, observerfn
    #    JabberProtocol.addObserver(self, event, observerfn, *args, **kw)

    def _addForwardingObserver(self, event, observerfn, 
                               priority=0, *args, **kw):
        JabberProtocol.addObserver(self, event, observerfn, 
                                        priority, *args, **kw)
        self.addRoute(event, priority)

    def _removeForwardingObserver(self, event, observerfn):
        raise NotImplementedError

    def addRoute(self, event, priority=0):
        iq = IQRequest("set")
        r = iq.addElement("route", NS_ROUTE)
        a = r.addElement("add")
        a.addElement("xpath", content=event.queryStr)
        a.addElement("priority", content=priority)
        d = iq.send(self)
        
        def success(elm):
            self.routes[event] = str(elm.route.id)

        d.addCallback(success)

    #inherited callbacks
    def streamAuthenticated(self, elm):
        JabberProtocol.streamAuthenticated(self, elm)
        self.addObserver(self.ROUTE_ADDED, self.routeAdded)
        self.addObserver(self.ROUTE_REMOVED, self.routeRemoved)
        # we are going to switch to the forwarding observer style now
        self.addObserver = self._addForwardingObserver
        self.removeObverser = self._removeForwardingObserver
        self.handle = self._handle
        self.onElement = self._onElement

    # callbacks
    def routeAdded(self, elm):
        # just xpath for now
        q = elm.route.add.xpath
        p = elm.route.add.priority
        id = elm.id

        # the callback will basically just be to send 
        # the data to the remote host
        self.parent.addObserver(q, self.send, p)

        # add this route to our store of routes
        self.routes[id] = q

        # respond to the reques
        # TODO

    def routeRemoved(self, elm):
        # just xpath for now
        id = elm.route.remove.id

        self.parent.removeObserver(self.routes[id], self.send)

class JabberComponentListener(JabberProtocolFactory):
    protocol = JabberComponentProxy
    #protocol opts
    initiating = False

    
        
    def buildProtocol(self, addr):
        xs = JabberProtocolFactory.buildProtocol(self, addr)

        # the protocols are components, too, so we treat them like services
        xs.setServiceParent(self)
        xs.addObserver(STREAM_AUTHD_EVENT, self.streamAuthenticated, 0, xs=xs)
        
        return xs
    

    def onElement(self, elm):
        print "routing to", self.parent
        self.parent.handle(elm)

    def addObserver(self, *args, **kw):
        self.parent.addObserver(*args, **kw)

    def removeObserver(self, *args, **kw):
        self.parent.removeObserver(*args, **kw)
    
    #callbacks
    def streamAuthenticated(self, elm, xs):
        print "stream authd, adding as component", xs
        xs.setServiceParent(self.parent)


class JabberComponentClient(JabberProtocolFactory):
    protocol = JabberComponentProxy
    
    #protocol opts
    initiating = True
    
    protocols = None

    def __init__(self, *args, **kw):
        JabberProtocolFactory.__init__(self, *args, **kw)
        self.protocols = []

    def buildProtocol(self, addr):
        xs = JabberProtocolFactory.buildProtocol(self, addr)
        #xs.name = self.name

        # the protocols are components, too, so we treat them like services
        #xs.setServiceParent(self)

        return xs

    # this send the data to    
    def onElement(self, elm):
        self.parent.handle(elm)

    def addService(self, svc):
        JabberProtocolFactory.addService(self, svc)

    # XXX andy: all this for every service stuff is probably bad
    #           i expect we only want one client
    def handle(self, elm):
        for s in self.streamss:
            if isinstance(s, self.protocol):
                print 'routing to', s
                s.handle(elm)

    def addObserver(self, *args, **kw):
        for s in self.services:
            if isinstance(s, self.protocol):
                s.addObserver(*args, **kw)

    def removeObserver(self, *args, **kw):
        for s in self.services:
            if isinstance(s, self.protocol):
                s.removeObserver(*args, **kw)
