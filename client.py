import argparse
from datetime import date, datetime, time, timedelta
import functools
import json
import threading
import time as timemod

from tornado import escape
from tornado import gen
from tornado import httpclient
from tornado import httputil
from tornado import ioloop
from tornado import websocket

json_encoder = lambda obj: obj.isoformat() if isinstance(obj, time) else None


APPLICATION_JSON = 'application/json'

DEFAULT_CONNECT_TIMEOUT = 60
DEFAULT_REQUEST_TIMEOUT = 60


class WebSocketClient():
    """Base for web socket clients.
    """
 
    def __init__(self, *, connect_timeout=DEFAULT_CONNECT_TIMEOUT,
                 request_timeout=DEFAULT_REQUEST_TIMEOUT):

        self.connect_timeout = connect_timeout
        self.request_timeout = request_timeout

    def connect(self, url):
        """Connect to the server.
        :param str url: server URL.
        """

        headers = httputil.HTTPHeaders({'Content-Type': APPLICATION_JSON})
        request = httpclient.HTTPRequest(url=url,
                                         connect_timeout=self.connect_timeout,
                                         request_timeout=self.request_timeout,
                                         headers=headers)
        ws_conn = websocket.WebSocketClientConnection(ioloop.IOLoop.current(),
                                                      request)
        ws_conn.connect_future.add_done_callback(self._connect_callback)

    def send(self, data):
        """Send message to the server
        :param str data: message.
        """
        if not self._ws_connection:
            raise RuntimeError('Web socket connection is closed.')

        self._ws_connection.write_message(escape.utf8(json.dumps(data, default=json_encoder)))

    def close(self):
        """Close connection.
        """
        if not self._ws_connection:
            raise RuntimeError('Web socket connection is already closed.')

        self._ws_connection.close()

    def _connect_callback(self, future):
        if future.exception() is None:
            self._ws_connection = future.result()
            self._on_connection_success()
            self._read_messages()
        else:
            self._on_connection_error(future.exception())

    @gen.coroutine
    def _read_messages(self):
        while True:
            msg = yield self._ws_connection.read_message()
            if msg is None:
                self._on_connection_close()
                break

            self._on_message(msg)

    def _on_message(self, msg):
        """This is called when new message is available from the server.
        :param str msg: server message.
        """
        pass

    def _on_connection_success(self):
        """This is called on successful connection to the server.
        """
        pass

    def _on_connection_close(self):
        """This is called when server closed the connection.
        """
        pass

    def _on_connection_error(self, exception):
        """This is called in case if connection to the server could
        not established.
        """
        pass


class TestWebSocketClient(WebSocketClient):

    def _on_message(self, msg):
        print(msg)

    def _on_connection_success(self):
        print("connection success!")
        self.send_status_update()

    def _on_connection_close(self):
        print('Connection closed!')

    def _on_connection_error(self, exception):
        print('Connection error: %s', exception)

    def send_status_update(self):
        global config
        self.send(json.dumps(config, default=json_encoder))


class WebSocketThread(threading.Thread):
    def __init__(self, url):
        threading.Thread.__init__(self)
        self.url = url

    def run(self):
        global config
        
        connectStr = "%s?id=%s" % (self.url, config.get('id'))
        deviceclient.connect(connectStr)

        try:
            ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            deviceclient.close()


class WateringThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        return
        while True:
            """
            if config["start"] <= datetime.now().time() <= config["end"]:
                deviceclient.send_status_update(json.loads({"id": config["id"],
                                                      "status": "Watering"}))
            """
            data = {
                config["id"]: {
                    "id": config["id"],
                    "status": "Ready"
                }
            }
            data["device_1"]["status"] = "Watering"
            deviceclient.send_status_update(data)
            timemod.sleep(3)
            data["device_1"]["status"] = "Ready"
            deviceclient.send_status_update(data)
            break
            

config = {}
deviceclient = TestWebSocketClient()

def updateConfig(config_path):
    global config

    with open(config_path, 'r') as fin:
        data = fin.read()
        config = json.loads(data)

    if not config.get('id'):
        raise RuntimeError('Missing id string')

    if config.get('start') and config.get('duration'):
        start = datetime.strptime(config['start'], '%H:%M:%S')
        config['end'] = (start + timedelta(seconds=config['duration'])).time()

    config['status'] = 'Ready'

        
def main(args):
    updateConfig(args.config)

    thread1 = WebSocketThread(args.server_url)
    thread2 = WateringThread()

    thread1.start()
    thread2.start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Client plant watering device")
    parser.add_argument("--config",
                        type=str,
                        help="Path to config file",
                        default="config.cfg")
    parser.add_argument("--server_url",
                        type=str,
                        help="Address for server's websocket listener",
                        default="ws://localhost:8888/devicews")
    args = parser.parse_args()
    
    main(args)
