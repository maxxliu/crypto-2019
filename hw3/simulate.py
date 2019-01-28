from argparse import ArgumentParser
from blockchain import Blockchain
import threading
import requests
import logging
import ast
import zmq
import time, datetime, json
from playbook import Playbook, Action
from messenger import Messenger
from message import Message
from network import Node, Network

logging.basicConfig(level=logging.INFO)

def test_bad_node_mining():
    '''
    This simulates a bad node mining in isolation and then beaconing its bad chain back to the network.
    '''
    n = Network()
    n.load_topology("./simulations/topology_3_nodes.pickle")
    n.start()
    book = Playbook(n)
    book.load_playbook("./simulations/test_bad_3_nodes")
    logging.info("start playbook")
    book.play_book()
    time.sleep(1)
    n.stop()
    return True
        
if __name__ == '__main__':
    try:
        network = Network()
        logging.info("Generating Network")
        network.generate_hw3_topology()
        logging.info("Starting Network")
        network.start()
        logging.info("Network Started")
        book = Playbook(network)
        book.set_book([
                        {'type':Action.NEW_TX,'n1':'node0','n2':'node8'},
                        {'type':Action.MINE,'n1':'node3'},
                        {'type':Action.RESOLVE_ALL},
                        {'type':Action.NEW_TX,'n1':'node3','n2':'node7'},
                        {'type':Action.MINE,'n1':'node7'},
                        {'type':Action.RESOLVE_NODES, 'nodes':['node0', 'node3', 'node4', 'node5', 'node6']},
                    ])
        book.play_book()
        logging.info("========All Actions Played, Press Ctrl-C to Stop========")
        while 1: time.sleep(60)
    except Exception as e:
        logging.error(e)
    finally:
        network.stop()
        logging.info("Network Stopped")

