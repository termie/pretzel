from twisted.words.xish import xpath
#locals
import xmlstream
from interfaces import IJabberAuthenticationFeature, implements
from protocol import JabberProtocol, JabberProtocolFactory

from utility import IQStanza
from features import NonSASLAuthenticationFeature

class ProxyJabberProtocol(JabberProtocol):
    def onDocumentStart(self, elm):
        self.parent.handle(elm)

class JabberClientToServerListener(JabberProtocolFactory):
    name = "c2s"
    resource = "component"

    protocol = ProxyJabberProtocol
    initiating = False
    namespace = "jabber:client"
    features = []
    #features = [NonSASLAuthenticationFeature()]
    #protocol = JabberClientToServerProtocol

    def handle(self, elm):
        print "passing client request to router"
        self.route(elm)
        #self.parent.handle(elm)

if __name__ == "__builtin__":
    from twisted.application import service, internet

    from proxy import JabberComponentClient
    #from router import JabberRouter

    application = service.Application("JabberC2S")
    col = service.IServiceCollection(application)

    router_proxy = JabberComponentClient()
    router_proxy.setServiceParent(col)

    auth = NonSASLAuthenticationFeature()

    router_proxy.features.append(auth)

    internet.TCPClient("localhost", 5269, router_proxy).setServiceParent(col)
    
    c2s = JabberClientToServerListener()
    c2s.setServiceParent(router_proxy)

    #c2s.features.append(NonSASLAuthenticationFeature())

    internet.TCPServer(5222, c2s).setServiceParent(col)
