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
import tnetstrings
from zmq import devices
from  multiprocessing import Process

class Worker():
    """
    Normally these would be separate programs, these are included for testing
    purposes right now. The goal is that this could eventually grow into a
    class that others can use in their applications.

    Not really focused on that now. Right now just trying things out to see
    how they work.
    """
    def __init__(self, connect_to):
        """ The worker connects to a socket to communicate with the Dispatcher
        in the Broker. This allows the Dispatcher to manage it's LRU queue using
        the worker. A listener socket is instatiated. This is the socket that the
        Router in the Broker will make requests to. 
        """
        self.my_id = str(uuid.uuid4())
        self.context = zmq.Context()
        self.broker_socket = context.socket(zmq.REQ)
        self.listener_socket = context.socket(zmq.XREP)

        self.broker_socket.setsockopt(zmq.IDENTITY, self.zmq_id)
        self.broker_socket.connect(connect_to)

        poller = zmq.Poller()
        poller.register(broker_socket, zmq.POLLIN)
        poller.register(listener_socket, zmq.POLLIN)

        while True:
            sock = dict(poller.poll())

            if sock.get(broker_socket) == zmq.POLLIN:
                multi_message = work_receiver.recv_multipart()
                message = json.loads(multi_message[1])
                # This worker just adds a reply with the same content
                # as the request. This way we can verify the replies
                # are matching.
                #
                #TODO: pretty sure I need to reassemble the request message
                message["reply"] = "%s" % (message["request"])

                self.listener_socket.send_json(message)


      # sender, conn_id, service, body = msg.split(' ', 3)


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

        # LRU Queue would look something like
        # [
        # {"connection": "tcp://127.0.0.1:55555", "services": ["web"]}
        # {"connection": "tcp://127.0.0.1:55556", "services": ["web"]}
        # {"connection": "tcp://127.0.0.1:44444", "services": ["news", "mail"]}
        # ]
        # Eventually I'll move it to an object with getter and setters which
        # can use something like gaeutilities event to notify the main
        # application when a worker is added. That way requests don't
        # get dropped.
        self.LRU = []

        self.context = zmq.Context()

        self.client_socket = self.context.socket(zmq.XREP)
        self.worker_socket = self.context.socket(zmq.XREP)
        self.dispatcher_socket = self.context.socket(zmq.PUSH)  
        self.router_response_socket = self.context.socket(zmq.SUB)   

        self.client_socket.setsockopt(zmq.IDENTITY, "%s-client" % self.my_id)
        self.worker_socket.setsockopt(zmq.IDENTITY, "%s-worker" % self.my_id)
        self.dispatcher_socket.setsockopt(zmq.IDENTITY, 
                "%s-dispatcher" % self.my_id)
        self.router_response_socket.setsockopt(zmq.IDENTITY, 
                "%s-router" % self.my_id)

        self.client_socket.bind(client_socket_uri)
        self.worker_socket.bind(worker_socket_uri)
        self.dispatcher_uri = "%s/%s_dispatcher" % (dispatcher_socket_base, 
            self.my_id)
        self.dispatcher_socket.bind(self.dispatcher_uri)
        self.router_response_uri = "%s/%s_router_response" % (
            router_response_socket_base, self.my_id)
        self.router_response_socket.bind(self.router_response_uri)

        poller = zmq.Poller()
        poller.register(self.worker_socket, zmq.POLLIN)
        poller.register(self.client_socket, zmq.POLLIN)

        # get the routers started before we start the loop
        print 'Starting %s routers' % routers

        router = 0
        while (router < routers):
            Process(target=Router, args=(self.context, 
                self.dispatcher_uri,
                self.router_response_uri)).start()
            router = router + 1

        print "Routers started, starting Dispatcher loop"

        while True:
            print "In main Dispatcher loop"
            sock = dict(poller.poll())
            print 'poll' 

#            if sock.get(self.worker_socket) == zmq.POLLIN:
#                print "Worker connection"
                # from the worker we are expecting a multipart message,
                # part0 = protocol command, part1 = request
#                message_parts = worker_socket.recv_multipart()
#                (command, request) = message_parts
#                if command.upper() == "PING":
#                    # PING is "uri services time"
#                    # services are comma delimited
#                    (uri, services, time) = request.split(" ", 3)
#                    # TODO: validate time here
#                    self.LRU.append({"connection": uri, 
#                        "services": services.split(",")})
#                    print "Worker %s PING" % uri
#
#            if sock.get(self.client_socket) == zmq.POLLIN:
#                # from the client we are expecting a multipart message
#                # part0 = service, part1 = request
#                (service, request) = client_socket.recv_multipart()
#                # (service, request) = message_parts
#                connection = None
#                for i in LRU:
#                    if service in i["services"]:
#                        connection = i["connection"]
#                        LRU.remove(i)
#                        break
#                # TODO: Here would be where to plug in something
#                # if conn == None so that new listeners can be checked for
#                dispatcher_socket.send_multipart([connection, 
#                    "%s %s" % (service, request)])

            print 'end loop cycle'

class Router():
    """ stub of how I think it will work, stopping this and going
    to just manage everything with the dispatcher at first. This is getting a
    bit complicated and I want to stop and do one thing at a time"""

    def __init__(self, context, 
            dispatcher_socket_uri,
            router_response_socket_uri,
            my_id=str(uuid.uuid4())):

        self.context = context
        self.my_id = my_id

        self.dispatcher_socket = context.socket(zmq.PULL)
        self.dispatcher_socket.setsockopt(zmq.IDENTITY, "%s-router" % self.my_id)
        self.dispatcher_socket.connect(dispatcher_socket_uri)

        self.response_socket = context.socket(zmq.XREP)
        self.dispatcher_socket.setsockopt(zmq.IDENTITY, 
            "%s-router-response" % self.my_id)

        poller = zmq.Poller()
        poller.register(self.dispatcher_socket, zmq.POLLIN)

        while True:
            sock = dict(poller.poll())

            if sock.get(dispatcher_socket) == zmq.POLLIN:
                (connection, request) = work_receiver.recv_multipart()
                self.context.socket(zmq.REQ).connect(connection).send(request)

if __name__ == "__main__":
    Dispatcher()
