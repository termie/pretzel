from twisted.words.xish import xmlstream

STREAM_CONNECTED_EVENT = xmlstream.STREAM_CONNECTED_EVENT
STREAM_START_EVENT = xmlstream.STREAM_START_EVENT
STREAM_END_EVENT = xmlstream.STREAM_END_EVENT
STREAM_ERROR_EVENT = xmlstream.STREAM_ERROR_EVENT

class XmlStream(xmlstream.XmlStream):
    pass

class XmlStreamFactory(xmlstream.XmlStreamFactory):
    protocol = XmlStream
    def buildProtocol(self, addr):
        self.resetDelay()
        xs = self.protocol()
        xs.factory = self
        for event, fn in self.bootstraps:
            xs.addObserver(event, fn)
        return xs
