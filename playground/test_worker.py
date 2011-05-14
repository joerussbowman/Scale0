import calendar
import time
import zmq
import uuid
import tnetstrings
from zmq import devices

class Worker():
    def __init__(self, connect_to, listen_on="tcp://127.0.0.1:9080"):
        """ The worker connects to a socket to communicate with the Dispatcher
        in the Broker. This allows the Dispatcher to manage it's LRU queue using
        the worker. A listener socket is instatiated. This is the socket that the
        Router in the Broker will make requests to. 
        """
        self.my_id = str(uuid.uuid4())
        self.context = zmq.Context()
        self.listen_on = listen_on

        self.broker_socket = self.context.socket(zmq.XREQ)
        self.broker_socket.setsockopt(zmq.IDENTITY, "broker-%s" % self.my_id)
        self.broker_socket.connect(connect_to)

        self.listener_socket = self.context.socket(zmq.XREP)
        self.listener_socket.setsockopt(zmq.IDENTITY, "listener-%s" % self.my_id)
        self.listener_socket.bind(self.listen_on)

        poller = zmq.Poller()
        poller.register(self.broker_socket, zmq.POLLIN)
        poller.register(self.listener_socket, zmq.POLLIN)

        self.connected = False

        while True:
            if not self.connected:
                print 'connecting'
                self.connect()
            sock = dict(poller.poll())

            if sock.get(self.broker_socket) == zmq.POLLIN:
                self.connect() # always connect first
                (service, request) = work_receiver.recv_multipart()
                print "Request service: %s, Request: %s" % (service, request)
                
    def connect(self):
        if not self.connected:
            self.broker_socket.send_multipart(["PING", 
                "%s test %s" % (self.listen_on, calendar.timegm(time.gmtime()))])
            self.connected = True

if __name__ == "__main__":
    Worker("tcp://127.0.0.1:8081")
