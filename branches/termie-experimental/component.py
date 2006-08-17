from twisted.application import service
from twisted.words.xish.utility import EventDispatcher

from utility import gen_id, RoutedStanza
from interfaces import IJabberComponent, implements

class JabberComponent(service.MultiService, EventDispatcher):
    implements(IJabberComponent)
    name = None
    components = None

    def __init__(self, *args, **kw):
        service.MultiService.__init__(self, *args, **kw)
        EventDispatcher.__init__(self, *args, **kw)
        self.components = {}

    def startService(self, *args, **kw):
        print "starting service,", self.__class__.__name__
        service.MultiService.startService(self, *args, **kw)
        #for event, fn in self.bootstraps:
        #    self.addObserver(event, fn)

    def addService(self, svc):
        service.MultiService.addService(self, svc)
        if IJabberComponent.implementedBy(svc.__class__):
            self.components[svc.name] = svc
        print "added service,", svc.name

    # XXX andy: probably totally have to adjust this
    def route(self, elm, to=None, from_=None, id=None):
        from_ = from_ or self.name
        if to is not None:
            if self.namedServices.has_key(to):
                self.namedServices[to].handle(elm)
            else:
                rs = RoutedStanza(elm, to=to, from_=from_, id=id)
                self.parent.handle(rs)
        else:
            self.parent.handle(elm)

                


    def handle(self, elm):
        self.onElement(elm)

    def onElement(self, elm):
        self.dispatch(elm)
 
    
        
