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
            routers=2):

        self.my_id = my_id

        """ LRU Queue would look something like
        [
        {"connection": "tcp://127.0.0.1:55555", "services": ["web"]}
        {"connection": "tcp://127.0.0.1:55556", "services": ["web"]}
        {"connection": "tcp://127.0.0.1:44444", "services": ["news", "mail"]}
        ]
        Eventually I'll move it to an object with getter and setters which
        can use something like gaeutilities event to notify the main
        application when a worker is added. That way requests don't
        get dropped. 
        """

        self.LRU = []

        self.context = zmq.Context()

        self.worker_socket = self.context.socket(zmq.XREP)
        self.worker_socket.setsockopt(zmq.IDENTITY, "%s-worker" % self.my_id)
        self.worker_socket.bind(worker_socket_uri)

        poller = zmq.Poller()
        poller.register(self.worker_socket, zmq.POLLIN)

        while True:
            sock = dict(poller.poll())
            print 'poll'

            if sock.get(self.worker_socket) == zmq.POLLIN:
                print "Worker connection"
                # from the worker we are expecting a multipart message,
                # part0 = protocol command, part1 = request
                message_parts = self.worker_socket.recv_multipart()
                (worker_id, command, request) = message_parts
                if command.upper() == "PING":
                    # PING is "uri services time"
                    # services are comma delimited
                    (uri, services, worker_time) = request.split(" ", 3)
                    # TODO: validate time here
                    self.LRU.append({"connection": uri, 
                        "services": services.split(",")})
                    self.worker_socket.send_multipart([worker_id, "PONG", "%s" % calendar.timegm(time.gmtime())])
                    print "Worker %s PING" % uri

if __name__ == "__main__":
    Dispatcher()
