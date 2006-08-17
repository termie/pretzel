from twisted.words.xish import domish
from twisted.internet import defer

import md5
import time

def gen_id():
    return nd5.new(time.time()).hexdigest()[:6]

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
        xs.addOnetimeObserver('/iq[@type="result"][@id="%s"]'%(self['id']),
                              d.callback)
        xs.addOnetimeObserver('/iq[@type="error"][@id="%s"]'%(self['id']),
                              d.errback)
        xs.send(self)
        return d



class RoutedStanza(domish.Element):
    def __init__(self, elm, to=None, from_=None, id=None):
        domish.Element.__init__(self, (None, "route"))
        if id is not None:
            self["id"] = id
        else:
            self.addUniqueId()
        if to is not None:
            self["to"] = to
        
        if from_ is not None:
            self["from"] = from_

        self.addChild(elm)
