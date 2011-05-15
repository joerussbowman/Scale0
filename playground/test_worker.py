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

        """ self.connection_state can be 1 of 3 ints
        0: not connected (not in LRU queue on broker)
        1: connection pending (PING sent)
        2: connected (PONG recieved, in LRU queue)
        """
        self.connection_state = 0 

        while True:
            if self.connection_state < 1:
                self.connect()
            sock = dict(poller.poll())

            if sock.get(self.broker_socket) == zmq.POLLIN:
                print "Recieved message from broker"
                (broker_id, command, request) = self.broker_socket.recv_multipart()
                if command == "PONG":
                    self.connection_state = 2
                    print 'Got PONG, connected'

            if sock.get(self.listener_socket) == zmq.POLLIN:
                print "Recieved message from broker"
                self.connect() # always connect first
                (service, request) = self.listener_socket.recv_multipart()
                print "Request service: %s, Request: %s" % (service, request)
                
    def connect(self):
        if self.connection_state < 1:
            print 'connecting to broker'
            self.broker_socket.send_multipart(["PING", 
                "%s test %s" % (self.listen_on, calendar.timegm(time.gmtime()))])
            self.connection_state = 1

if __name__ == "__main__":
    Worker("tcp://127.0.0.1:8081")
