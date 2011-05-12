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
import zmq
import uuid
from zmq import devices
from multiprocessing import Process

class Worker():
    """
    Normally these would be separate programs, these are included for testing
    purposes right now. The goal is that this could eventually grow into a
    class that others can use in their applications.

    Not really focused on that now. Right now just trying things out to see
    how they work.
    """
    def __init__(self, connect_to):
        self.my_id = str(uuid.uuid4())
        self.context = zmq.Context()
        self.broker_socket = context.socket(zmq.XREQ)

        broker_socket.setsockopt(zmq.IDENTITY, self.zmq_id)
        broker_socket.connect(connect_to)

        poller = zmq.Poller()
        poller.register(broker_socket, zmq.POLLIN)

        while True:
            sock = dict(poller.poll())

            if sock.get(broker_socket) == zmq.POLLIN:
                multi_message = work_receiver.recv_multipart()
                message = json.loads(multi_message[1])
                # This worker just adds a reply with the same content
                # as the request. This way we can verify the replies
                # are matching.
                message["reply"] = "%s" % (message["request"])

                broker_socket.send_json(message)

class Dispatcher():
    def __init__(self, client_socket, worker_socket, router_socket,
            my_id=str(uuid.uuid4())):
        self.my_id = my_id
        self.context = zmq.Context()

        self.client_socket = context.socket(zmq.XREP)
        self.worker_socket = context.socket(zmq.XREP)
        self.router_socket = context.socket(zmq.XREP)

        self.LRU = []
        self.WQ = []

        self.client_socket.setsockopt(zmq.IDENTITY, "%s-C" % self.my_id)
        self.worker_socket.setsockopt(zmq.IDENTITY, "%s-W" % self.my_id)
        self.router_socket.setsockopt(zmq.IDENTITY, "%s-R" % self.my_id)

        #TODO should pass ip and ports to Dispatcher. Maybe router ipc as well
        self.client_socket.bind("tcp://127.0.0.1:8080" % self.my_id)
        self.worker_socket.bind("tpc://127.0.0.1:8081" % self.my_id)
        self.router_socket.bind("ipc:///var/tmp/%s-R" % self.my_id)
    

            
    




