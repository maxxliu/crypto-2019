import zmq
import threading
import time
import logging
from message import Message
import json
logging.basicConfig(level=logging.DEBUG)

class Messenger:
    def __init__(self):
        self._publishers = set()

    def unsubscribe(self, http_url):
        logging.debug("Unsubscribe to %s" % self.http_to_tcp(http_url))
        self._publishers.remove(http_url)
        self._sub_socket.disconnect(self.http_to_tcp(http_url))

    def subscribe(self, http_url):
        if http_url in self._publishers or http_url == self._http_url: return
        self._publishers.add(http_url)
        logging.debug("%s Subscribe to %s" % (self._http_url, self.http_to_tcp(http_url)))
        self._sub_socket.connect(self.http_to_tcp(http_url))
        #let the publisher know we subscribed, so we get bi-directional subscription
        socket = self._context.socket(zmq.REQ)
        socket.connect(self.http_to_rep(http_url))
        socket.send_string(self._http_url)
        socket.disconnect(self.http_to_rep(http_url))

    def start_register(self, blockchain):
        while True:
            s = self._rep_socket.recv() #recv as pub
            if len(s):
                self.subscribe(s.decode("utf-8"))
                self._rep_socket.send_string('')
            time.sleep(0.01) #10ms

    def start_subscriber(self, blockchain):
        '''
        whenever the node (as sub) receive a msg from other node (pub)
        add the msg to the queue and let the blockchain thread handle the job
        '''
        while True:
            s = self._sub_socket.recv() #recv as sub
            if len(s):
                logging.debug("RECEIVED MSG: [%s]" % s)
                blockchain.push_message(s.decode('utf-8'))
        logging.error("!!!Subscriber Stopped!!!")

    def http_to_rep(self, http_url):
        return self.http_to_tcp(http_url, 2)

    def http_to_tcp(self, http_url, inc=1):
        #next port is used by messenger
        port = int(http_url.split(':')[-1]) + inc
        url = ':'.join(http_url.replace('http','tcp').split(':')[:-1]+[str(port)])
        return url

    def start(self, url, blockchain):
        try:
            self._http_url = url
            self._tcp_url = self.http_to_tcp(url)
            logging.debug("Starting messenger @ [%s]" % self._tcp_url)
            self._context = zmq.Context()
            self._sub_socket = self._context.socket(zmq.SUB)
            self._sub_socket.setsockopt_string(zmq.SUBSCRIBE, '')
            self._pub_socket = self._context.socket(zmq.PUB)
            self._pub_socket.bind(self._tcp_url)
            self._rep_socket = self._context.socket(zmq.REP) #for registration
            self._rep_socket.bind(self.http_to_rep(url))
            sub = threading.Thread(target=self.start_subscriber,args=(blockchain,))
            sub.start()
            reg = threading.Thread(target=self.start_register,args=(blockchain,))
            reg.start()
        except Exception as e:
            logging.error("!!!!!!Failed to start messenger: %s!!!!!!!" % e)

    def publish_message(self, msg_type, msg):
        msg = Message.to_str(self._http_url, str(msg_type), msg)
        logging.debug("publishing message: [%s]" % msg)
        self._pub_socket.send_string(msg)
        time.sleep(0.01)

