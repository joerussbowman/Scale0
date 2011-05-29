#!/usr/bin/env python
#
# -*- coding: utf-8 -*-
#
# Copyright 2011 Joseph Bowman 
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys
import calendar
import time
import zmq
import uuid
import tnetstrings
from zmq.eventloop import ioloop, zmqstream

class Dispatcher():
    def __init__(self, 
            client_socket_uri="tcp://127.0.0.1:8080", 
            worker_xrep_socket_uri="tcp://127.0.0.1:8081",
            pub_socket_uri="tcp://127.0.0.1:8082",
            my_id=str(uuid.uuid4()),
            routers=2, heartbeat=1, liveness=3):

        self.my_id = my_id
        self.heartbeat_interval = heartbeat * 1000
        self.heartbeat_liveness = liveness

        """ Workers info would look something like
        {
            "worker1": { "connection": "tcp://127.0.0.1:55555", "services": ["web"], "last_pong": int(time.time())}
            "worker2": { "connection": "tcp://127.0.0.1:55555", "services": ["web"], "last_pong": int(time.time())}
            "worker3": { "connection": "tcp://127.0.0.1:55555", "services": ["news", "mail"], "last_pong": int(time.time())}
        }
        Eventually I'll move it to an object with getter and setters which
        can use something like gaeutilities event to notify the main
        application when a worker is added. That way requests don't
        get dropped. 

        *id is usually a uuid, but really as long as they are unique Scale0 should not care.
        """

        self.workers = {} 
        self.LRU = []
        self.pings = []

        self.context = zmq.Context.instance()
        self.loop = ioloop.IOLoop.instance()

        self.worker_xrep_socket = self.context.socket(zmq.XREP)
        self.worker_xrep_socket.setsockopt(zmq.IDENTITY, "%s-worker" % self.my_id)
        self.worker_xrep_socket.bind(worker_xrep_socket_uri)
        
        self.worker_xrep_stream = zmqstream.ZMQStream(self.worker_xrep_socket, self.loop)
        self.worker_xrep_stream.on_recv(self.worker_handler)


        # Trying to move to PUB for getting messages to Workers
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.setsockopt(zmq.IDENTITY, "%s_broker_pub" % self.my_id)
        self.pub_socket.bind(pub_socket_uri)
        
        self.pub_stream = zmqstream.ZMQStream(self.pub_socket, self.loop)
        # self.loop.add_handler(self.worker_xrep_socket, self.worker_handler, zmq.POLLIN)
        ioloop.PeriodicCallback(self.send_pings, self.heartbeat_interval, self.loop).start()
        ioloop.PeriodicCallback(self.send_pub, self.heartbeat_interval, self.loop).start()

        self.loop.start()

    def worker_handler(self, message):
        """ worker_handler handles messages from worker sockets. Messages
        are 3+ part ZeroMQ multipart messages. (worker_id, command, request).

        worker_id is supplied as part of the ROUTER socket requirements and is
        used to send replies back.

        command is mapped to functions. This allows an undefined method error
        to be thrown if the command isn't an acceptable method. Also just
        easier to maintain the code if each command is it's own method.

        request is the rest of the message, can be multiple parts and Scale0
        will generally ignore it except to pass it on.
        """
        sock = self.worker_xrep_stream

        # message = sock.recv_multipart()
        getattr(self, message[1].lower())(sock, message)

    def send_pings(self):
        """ pings are the heartbeat check to determine if the workers listed
        in the LRU queue are still available. A socket is created and the ping
        is sent to the listener socket on the worker. The worker will reply
        with a pong back to the worker_response_socket.
        """
        if len(self.LRU) > 0:
            ping_time = str(time.time())
            #ping_sock = self.context.socket(zmq.XREQ)
            for worker in self.LRU:
                #ping_sock.connect(self.workers[worker]["connection"])
                self.workers[worker]["socket"].send_multipart(["PING", ping_time])
                self.pings.append("%s_%s" % (worker, ping_time))
            #ping_sock.close()

    def send_pub(self):
        """ Test method for validating pub/sub is working """
        self.pub_socket.send_multipart(["PING", ""])

    def pong(self, sock, message):
        """ pong is a reply to a ping for a worker in the LRU queue. """
        (worker_id, command, request) = message
        print "got ping for %s" % worker_id
        self.workers[worker_id]["last_pong"] = float(request)
        self.pings.remove("%s_%s" %(worker_id, request))
        print self.pings


    def heartbeat(self, sock, message):
        """ For heartbeat we just shoot the request right back at the sender.
        Don't even bother to parse anything to save time.
        """
        sock.send_multipart(message)

    def ready(self, sock, message):
        """ ready is the worker informing Scale0 it can accept more jobs.
        """

        (worker_id, command, request) = message
        (uri, services) = request.split(" ", 2)
        socket = self.context.socket(zmq.XREQ)
        socket.connect(uri)
        self.workers[worker_id] = {"connection": uri,
            "services": services.split(","),
            "last_pong": time.time(),
            "socket": socket}
        self.LRU.append(worker_id)
        sock.send_multipart([worker_id, "OK", ""])
        print "Worker %s READY" % uri

if __name__ == "__main__":
    Dispatcher()
