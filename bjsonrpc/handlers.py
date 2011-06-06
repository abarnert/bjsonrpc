"""
    bjson/handlers.py
    
    Asynchronous Bidirectional JSON-RPC protocol implementation over TCP/IP
    
    Copyright (c) 2010 David Martinez Marti
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions
    are met:
    1. Redistributions of source code must retain the above copyright
       notice, this list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.
    3. Neither the name of copyright holders nor the names of its
       contributors may be used to endorse or promote products derived
       from this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
    ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
    TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
    PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL COPYRIGHT HOLDERS OR CONTRIBUTORS
    BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
    CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.

"""
import re
from types import MethodType
from bjsonrpc.exceptions import  ServerError

class BaseHandler(object):
    """
        Base Class to publish remote methods. It is instantiated by *Connection*.
        
        Example::
        
            class MyHandler(bjson.handlers.BaseHandler):
                def _setup(self):
                    # Initailize here.
                    self.c = 0
                    
                def echo(self,text): 
                    print text
                    self.c += 1
                    
                def getcount(self): return c
        
        Other members:
        
        **public_methods_pattern**
            RegEx string that returns True if the method name is suitable for
            publishing. Defaults to r'^[a-z]\w+$'
        
        **nonpublic_methods**
            List of string containing names that shouldn't be published (even 
            if they are in the format required by the RegEx). Defaults to
            ["close","_factory","add_method","get_method"]
            
    """
    
    public_methods_pattern = r'^[a-z]\w+$'
    # Pattern to know which methods should be automatically published
    
    nonpublic_methods = [
        "close",
        "_factory",
        "add_method",
        "get_method",
        ] 
    # List of method names that never should be published    
    
    @classmethod
    def _factory(cls, *args, **kwargs):
        """
            *New in bjsonrpc v0.2.1*
            
            Classmethod aimed to create flavoured instances of BaseHandler.
            When you create a new connection you may want to give the constructor
            a set of specific arguments. Use this classmethod to do that:
            
                conn = bjsonrpc.connect(handler_factory=MyHandler._factory("my flavoured one"))
                
            Later, whenever the class is instantiated, the BaseHandler.setup 
            method will receive the arguments passed to factory.
            
            The original idea for this feature is from Paul Pietkiewicz *(pawel.pietkiewicz (at) gmail.com)*
        """
        def handler_factory(connection):
            handler = cls(connection, *args, **kwargs)
            return handler
        return handler_factory
    
    def __init__(self, connection, *args, **kwargs):
        self._conn = connection
        
        if hasattr(self._conn,"connection"): 
            self._conn = self._conn.connection
        if hasattr(self._conn,"_conn"): 
            self._conn = self._conn._conn
            
        self._methods = {}
        for mname in dir(self):
            if re.match(self.public_methods_pattern, mname):
                function = getattr(self, mname)
                if isinstance(function, MethodType):
                    self.add_method(function)
            
        self._setup(*args,**kwargs)
        
    def _setup(self,*args,**kwargs):
        """
            Empty method to ease inheritance. Overload it with your needs, it
            will be called after __init__.
        """
        pass 
        
    def _shutdown(self):
        """
            Internal method called when the handler is going to be destroyed.
            You should add cleanup code here. Remember to call the parent
            function.
        """
        pass # In the future, here we could have some internal clean-up code.
        
    def close(self):
        """
            Cleans some variables before the object is freed. close is called
            manually from connection whenever a handler is going to be deleted.
        """
        self._methods = {}

    def add_method(self, *args, **kwargs):
        """
            Porcelain for publishing methods into the handler. Is used by the
            constructor itself to publish all non-private functions.
        """
        for method in args:
            if method.__name__ in self.nonpublic_methods: 
                continue
            try:
                assert(method.__name__ not in self._methods)
            except AssertionError:
                raise NameError, "Method with name %s already in the class methods!" % (method.__name__)
            self._methods[method.__name__] = method
            
        for name, method in kwargs.iteritems():
            if method.__name__ in self.nonpublic_methods: 
                continue
            try:
                assert(name not in self._methods)
            except AssertionError:
                raise NameError, "Method with name %s already in the class methods!" % (method.__name__)
                
            self._methods[name] = method

    def get_method(self, name):
        """
            Porcelain for resolving method objects from their names. Used by
            connections to get the apropiate method object.
        """
        if name not in self._methods:
            raise ServerError("Unknown method %s" % repr(name))
            
        return self._methods[name]
        

class NullHandler(BaseHandler):
    """
        Null version of BaseHandler which has nothing in it. Use this when you
        don't want to publish any function.
    """
    pass

