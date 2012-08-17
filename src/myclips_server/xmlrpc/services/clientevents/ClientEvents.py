'''
Created on 17/ago/2012

@author: Francesco Capozzo
'''
from myclips_server.xmlrpc.services.Service import Service
import xmlrpclib
from myclips.listeners.EventsManagerListener import EventsManagerListener
import myclips_server

class ClientEvents(Service):
    '''
    Manage client registration of myclips's event listeners
    
    The client must implement a xmlrpc end-point with at-least the following
    methods:
    
        - .ping(string aReverseToken) : True
            Called to check server-client connection and validate the reverse token
            and the listener
            
        - .notify(string aReverseToken, string anEventName, *args, **kwargs) : None
            Called when events are fired.
            
        - .close(string aReverseToken) : None
            Called before the unregister process is completed to nofity
            the client's listener
    
    '''

    _NAME = "ClientEvents_MyClipsEvents"
    _TYPE = "ClientEvents"
    __API__ = Service.__API__ + ['register', 'unregister']
        
        
    def getListeners(self, aSessionToken):
        
        try:
            listeners = self._broker.Sessions.getProperty(aSessionToken, "ClientEvents_MyClipsEvents.listeners")
        except KeyError:
            listeners = {}
            self._broker.Sessions.setProperty(aSessionToken, "ClientEvents_MyClipsEvents.listeners", listeners )
            
        return listeners
    
    def onSessionDestroy(self, aSessionToken):
        someListeners = self.getListeners(aSessionToken)
        for aListenerName in someListeners.keys():
            self.unregister(aSessionToken, aListenerName)
        
    def register(self, aSessionToken, aListenerName, aListenerAddress, aReverseToken, *eventsName):
        '''
        Register a xmlrpc end-point of the client as a myclips's event listener
        If a listener with the same identifier is already registered,
        it will be unregister and then replaced
        
        The registration protocol requires the client end-point to
        reply to a <client-end-point>.ping(aReverseToken) method call
        before the registration is completed
        
        Standard event names for MyClips's Network Engine are:
        
            action-performed, debug-options-changed, fact-asserted, 
            fact-retracted, network-reset-post, network-reset-pre, 
            network-ready, network-reset-post, network-reset-pre, 
            network-shutdown, node-activated, node-activated-left, 
            node-activated-right, node-added, node-linked, node-removed, 
            node-shared, node-unlinked, rule-activated, rule-added, 
            rule-deactivated, rule-fired, rule-removed, strategy-changed
            
        More info about event's args and meanings are available in the myclips's documentation
        
        
        @param aSessionToken: a token for a valid session
        @type aSessionToken: string
        @param aListenerName: the identifier of the listener after the registration
        @type aListenerName: string
        @param aListenerAddress: the url of the xmlrpc server of the client where events will be forwarded
        @type aListenerAddress: string
        @param aReverseToken: a <secret-code> the server will send with data to identify a valid transmission 
        @type aReverseToken: mixed
        @param eventsName: a list of event names to register for
        @type eventsName: list of strings 
        '''        
        
        someListeners = self.getListeners(aSessionToken)
        if someListeners.has_key(aListenerName):
            self.unregister(aSessionToken, aListenerName)
        
        theListener = xmlrpclib.Server(aListenerAddress, allow_none=True)
        theListener.ping(aReverseToken)
        
        theListener = ClientListener(aReverseToken, theListener, list(eventsName))
        
        theNetwork = self._broker.Engine.getNetwork(aSessionToken)
        theListener.install(theNetwork.eventsManager)
            
        someListeners[aListenerName] = theListener
    
    def unregister(self, aSessionToken, aListenerName):
        '''
        Unregister a listener
        
        @param aSessionToken: a token for a valid session
        @type aSessionToken: string
        @param aListenerName: a valid listener identifier
        @type aListenerName: string
        '''
        
        someListeners = self.getListeners(aSessionToken)
        try:
            theListener = someListeners.pop(aListenerName)
            try:
                theListener.uninstall()
            except:
                pass
            theListener.close()
        except:
            pass
        
        
class ClientListener(EventsManagerListener):
    """
    Forwarder for a remove client listener
    """
    def __init__(self, theReverseToken, theServer, theEvents=None):
        self._theReverseToken = theReverseToken
        self._theServer = theServer
        EventsManagerListener.__init__(self, dict([ (aEvent, self.forward) for aEvent in (theEvents or []) ]))
        
    
    def forward(self, eventName, *args, **kwargs):
        try:
            self._theServer.notify(self._theReverseToken, eventName, *args, **kwargs)
        except:
            myclips_server.logger.info("A listener could be not valid anymore: %s", self)
            
    def close(self):
        try:
            self._theServer.close(self._theReverseToken)
        except:
            myclips_server.logger.info("A listener could be not valid anymore: %s", self)
    
    def notify(self, eventName, *args, **kargs):
        '''
        Override Observer.notify to add the event name as
        first arg in the list if *args
        '''
        args = [eventName] + list(args)
        EventsManagerListener.notify(self, eventName, *args, **kargs)
        
    def __repr__(self, *args, **kwargs):
        return "<ClientListener: %s>"%repr(self._theServer)
        