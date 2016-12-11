import argparse
from datetime import time
import os.path

from tornado import ioloop, web, websocket
from tornado.web import url
import json
json_encoder = lambda obj: obj.isoformat() if isinstance(obj, time) else None

deviceSockets = {}
admins = []
devices = {}


class AdminSocketHandler(websocket.WebSocketHandler):
    
    def check_origin(self, origin):
        return True

    def open(self, *args, **kwargs):
        print("admin connection")
        admins.append(self)
        payload = [{"action": "ADDUP",
                    "data": devices[device_id]} for device_id in devices]
        self.write_message(json.dumps(payload, default=json_encoder))

    def on_close(self):
        if self in admins:
            print("Admin connection closed!")
            admins.remove(self)

    def on_message(self, message):
        data = json.loads(json.loads(message))  # Wat.
        device_id = data.get('id')

        if device_id:
            if not device_id in devices:
                devices[device_id] = data

        print("sending message to admins")
        for a in admins:
            payload = [{"action": "ADDUP",
                        "data": devices[device_id]} for device_id in devices]
            a.write_message(json.dumps(payload, default=json_encoder))


class DeviceSocketHandler(websocket.WebSocketHandler):
    
    def check_origin(self, origin):
        return True

    def open(self, *args, **kwargs):
        self.id = self.get_argument("id")
        print("device connection", self.id)
        if self.id and not devices.get("id"):
            deviceSockets[self.id] = self

    def on_close(self):
        print("Device connection closed!")
        del(devices[self.id])
        del(deviceSockets[self.id])

        payload = [{"action": "DELETE",
                   "data": {"device_id": self.id}}]
        for a in admins:
            a.write_message(json.dumps(payload, default=json_encoder))

    def on_message(self, message):
        data = json.loads(json.loads(message))  # Wat.
        device_id = data.get('id')

        if device_id:
            if not device_id in devices:
                devices[device_id] = data

        payload = [{"action": "ADDUP",
                    "data": devices[device_id]}]
        for a in admins:
            print(payload)
            a.write_message(json.dumps(payload, default=json_encoder))

class ApiHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        print("API get")
        self.finish()
        id = self.get_argument("id")
        value = self.get_argument("value")
        data = {"id": id, "value" : value}
        data = json.dumps(data)
        for c in cl:
            c.write_message(data)

    @web.asynchronous
    def post(self):
        pass

class AdminHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        self.render("index.html", devices=devices)
        

class DeviceHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        self.finish()

        for a in admins:
            a.write_message(json.dumps(devices))


class DeviceProfileHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, id):
        self.render("device.html", device=devices[id])

    @web.asynchronous
    def delete(self, id):
        self.finish()
        if id in devices.keys():
            del(devices[id])

        for a in admins:
            a.write_message(json.dumps(devices))

handlers = [
    url(r'/', AdminHandler, name="home"),
    (r'/adminws', AdminSocketHandler),
    (r'/devicews', DeviceSocketHandler),
    (r'/api', ApiHandler),
    url(r'/device', DeviceHandler),
    url(r'/device/(.*)', DeviceProfileHandler, name="device"),
]

settings = dict(
    template_path=os.path.join(os.path.dirname(__file__), "templates")
)
app = web.Application(handlers, **settings)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Server to manage plant watering devices")
    parser.add_argument("--port",
                        type=int,
                        help="Port to listen for incoming websocket connections",
                        default=8888)
    args = parser.parse_args()
    
    app.listen(args.port)
    
ioloop.IOLoop.instance().start()
