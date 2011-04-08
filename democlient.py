import zmq
import tornado.ioloop
import tornado.web

class MainHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.write("Hello Wold")
        self.finish()

application = tornado.web.Application([
    (r"/.*", MainHandler),
])

if __name__ == "__main__":
    application.listen(80)
    tornado.ioloop.IOLoop.instance().start()
