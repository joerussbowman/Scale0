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
from zmq import devices
from zmq.eventloop import ioloop

class Dispatcher():
    """ The Dispatcher will accept requests on the client_socket,
    then pull a worker from the LRU Queue and pass it to a Router
    which will then send the request to the Worker. Once it's gotten
    a response it will pass that response back to the Dispatcher who
    will send it to the Client. 

    Workers adding themselves to the LRU Queue is a separate from requests
    being sent to them. A Worker can immediately add itself back to the Queue
    upon receiving a request if it so chooses, allowing for Workers to support
    more than a single request at a time. It is the Workers responsibility to
    inform the Broker it should be added to the Queue.
    """
    def __init__(self, 
            client_socket_uri="tcp://127.0.0.1:8080", 
            worker_socket_uri="tcp://127.0.0.1:8081", 
            dispatcher_socket_base="ipc:///var/tmp/",
            router_response_socket_base="ipc:///var/tmp/",
            my_id=str(uuid.uuid4()),
            routers=2, heartbeat=1, liveness=3):

        self.my_id = my_id
        self.heartbeart_interval = heartbeat * 1000
        self.heartbeat_liveness = liveness

        """ LRU Queue would look something like
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

        self.LRU = {} 

        self.context = zmq.Context()

        self.worker_socket = self.context.socket(zmq.XREP)
        self.worker_socket.setsockopt(zmq.IDENTITY, "%s-worker" % self.my_id)
        self.worker_socket.bind(worker_socket_uri)

        self.loop = ioloop.IOLoop.instance()

        self.loop.add_handler(self.worker_socket, self.worker_handler, zmq.POLLIN)
        ioloop.PeriodicCallback(self.send_pings, 1000, self.loop).start()

        self.loop.start()

    def worker_handler(self, sock, events):
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

        message = sock.recv_multipart()
        getattr(self, message[1].lower())(sock, message)

    def send_pings(self):
        ping_time = str(time.time())
        for worker in self.LRU:
            self.worker_socket.send_multipart([worker, "PING", ping_time])

    def pong(self, sock, message):
        """ pong is a reply to a ping for a worker in the LRU queue. """
        (worker_id, command, request) = message
        self.LRU[worker_id]["last_pong"] = float(request)
        print "received pong for %s, updated queue" % worker_id
        print str(self.LRU)


    def heartbeat(self, sock, message):
        """ For heartbeat we just shoot the request right back at the sender.
        Don't even bother to parse anything to save time.
        """
        sock.send_multipart(sock.recv_multipart())

    def ready(self, sock, message):
        """ ready is the worker informing Scale0 it can accept more jobs.
        """

        (worker_id, command, request) = message
        (uri, services) = request.split(" ", 2)
        self.LRU[worker_id] = {"connection": uri,
            "services": services.split(","),
            "last_pong": time.time()}
        sock.send_multipart([worker_id, "OK", ""])
        print "Worker %s READY" % uri

if __name__ == "__main__":
    Dispatcher()
