import calendar
import time
import zmq
import uuid
import tnetstrings
from zmq.eventloop import ioloop, zmqstream

class Worker():
    def __init__(self, connect_to, listen_on="tcp://127.0.0.1:9080"):
        """ The worker connects to a socket to communicate with the Dispatcher
        in the Broker. This allows the Dispatcher to manage it's LRU queue using
        the worker. A listener socket is instatiated. This is the socket that the
        Router in the Broker will make requests to. 
        """
        self.my_id = str(uuid.uuid4())
        self.context = zmq.Context.instance()
        self.loop = ioloop.IOLoop.instance()
        self.listen_on = listen_on

        self.broker_socket = self.context.socket(zmq.XREQ)
        self.broker_socket.setsockopt(zmq.IDENTITY, "broker-%s" % self.my_id)
        self.broker_socket.connect(connect_to)
        self.broker_stream = zmqstream.ZMQStream(self.broker_socket, self.loop)

        self.listener_socket = self.context.socket(zmq.XREP)
        self.listener_socket.setsockopt(zmq.IDENTITY, "listener-%s" % self.my_id)
        self.listener_socket.bind(self.listen_on)
        self.listener_stream = zmqstream.ZMQStream(self.listener_socket, self.loop)

        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.setsockopt(zmq.IDENTITY, "worker_sub_%s" % self.my_id)
        self.sub_socket.connect("tcp://127.0.0.1:8082")
        self.sub_socket.setsockopt(zmq.SUBSCRIBE,"PING")
        self.sub_stream = zmqstream.ZMQStream(self.sub_socket, self.loop)

        self.heartbeat_stamp = None
        self.heartbeats = []


        """ self.connection_state can be 1 of 3 ints
        0: not connected (not in LRU queue on broker)
        1: connection pending (READY sent)
        2: connected (OK recieved, in LRU queue)
        """
        self.connection_state = 0 
        
        self.broker_stream.on_recv(self.broker_handler)
        self.listener_stream.on_recv(self.listener_handler)
        self.sub_stream.on_recv(self.sub_handler)
        # self.loop.add_handler(self.broker_socket, self.broker_handler, zmq.POLLIN)
        # self.loop.add_handler(self.listener_socket, self.listener_handler, zmq.POLLIN)

        ioloop.DelayedCallback(self.connect, 1000, self.loop).start()
        ioloop.PeriodicCallback(self.send_heartbeat, 1000, self.loop).start()

        self.loop.start()

    def send_heartbeat(self):
        self.heartbeat_stamp = str(time.time())
        print 'sending heartbeat %s' % self.heartbeat_stamp
        self.heartbeats.append(self.heartbeat_stamp)
        self.broker_socket.send_multipart(["HEARTBEAT", self.heartbeat_stamp])

    def broker_handler(self, msg):
        (command, request) = msg
        if command == "OK":
            self.connect_state = 2
            print 'In LRU Queue'
        if command == "HEARTBEAT":
            if request == self.heartbeat_stamp:
                print 'Got valid heartbeat %s' % request
            else:
                print "Heartbeat timestamp mismatch %s" % request
            self.heartbeats.remove(request)
            print self.heartbeats

    def listener_handler(self, msg):
        (sock_id, command, request) = msg
        if command == "PING":
            print 'got ping %s' % request
            self.broker_socket.send_multipart(["PONG", request])
        else:
            print "Recieved message from broker"
            self.connect() # always reconnect
            (service, request) = sock.recv_multipart()
            print "Request service %s, Request: %s" % (service, request)

    def sub_handler(self, msg):
        """ Trying to move to pub/sub for getting messages to workers. """
        print "SUB MSG %s" % msg
                
    def connect(self):
        print 'Running connect test'
        if self.connection_state < 1:
            print 'connecting to broker'
            self.broker_socket.send_multipart(["READY", 
                "%s test" % (self.listen_on)])
            self.connection_state = 1

if __name__ == "__main__":
    Worker("tcp://127.0.0.1:8081")
