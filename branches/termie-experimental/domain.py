from component import JabberComponent

class JabberDomainHandler(JabberComponent):



if __name__ == "__builtin__":
    from twisted.application import service, internet

    from proxy import JabberComponentClient
    #from router import JabberRouter

    application = service.Application("JabberDomainHandler")
    col = service.IServiceCollection(application)

    router_proxy = JabberComponentClient()
    router_proxy.setServiceParent(col)

    router_proxy.features.append(NonSASLAuthenticationFeature())

    internet.TCPClient("localhost", 5269, router_proxy).setServiceParent(col)
    
    domain_handler = JabberClientToServerListener()
    domain_handler.setServiceParent(router_proxy)
    domain_handler.name = "term.ie"    


