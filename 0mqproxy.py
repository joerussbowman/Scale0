import os
import zmq
import logging
import tornado.ioloop
import tornado.web
import tornado.httpserver
from tornado.options import define
from tornado.options import options

define("http_port", default=80, help="run on the given port", type=int)
define("zmq_port", default=8080, help="run on the given port", type=int)
define("debug", default=False, help="turn debugging on or off")

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/*", MainHandler),
        ]
        settings = dict(
                        static_path=os.path.join(os.path.dirname(__file__), "static"),
                        debug=options.debug,
                        )
        tornado.web.Application.__init__(self, handlers, ** settings)

        # set up zmq PUSH socket
        context = zmq.Context()
        sender = context.socket(zmq.PUSH)
        sender.bind("tcp://*:%s" % options.zmq_port)

class MainHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        logging.error(self.request)
        self.write("Hello Wold")
        self.finish()

def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.http_port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
