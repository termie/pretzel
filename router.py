from twisted.words.xish import xpath, utility
from component import JabberComponent


class JabberRouter(JabberComponent):

    routes = None

    # this is probably just a helper for the router
    # to speed things up if we already know where to go
    NAMED_ROUTE = xpath.internQuery("""/route""")

    def __init__(self, *args, **kw):
        JabberComponent.__init__(self, *args, **kw)
        self.bootstraps = [
                (self.NAMED_ROUTE, self.onNamedRoute)
                ]
        #self.routes = []

    def startService(self):
        JabberComponent.startService(self)
        for event, fn in self.bootstraps:
            self.addObserver(event, fn)

    def onNamedRoute(self, elm):
        print "i know where to go"
        pass
    
    def onElement(self, elm):
        print "routing element", elm.toXml()
        JabberComponent.onElement(self, elm)   
    
if __name__ == "__builtin__":
    from twisted.application import service, internet

    from proxy import JabberComponentListener
    from features import NonSASLAuthenticationFeature

    application = service.Application("JabberRouter")
    col = service.IServiceCollection(application)

    router = JabberRouter()
    router.setServiceParent(col)

    component_listener = JabberComponentListener()
    component_listener.setServiceParent(router)

    component_listener.features.append(NonSASLAuthenticationFeature())

    internet.TCPServer(5269, component_listener).setServiceParent(component_listener)
    
