from argparse import ArgumentParser
from blockchain import Blockchain
import threading
import requests
import logging
import ast
import zmq
import time, datetime, json, random
import pickle
from messenger import Messenger
from message import Message
from network import Node, Network

logging.basicConfig(level=logging.INFO)

class Action:
    '''
    Actions represent network actions at each step. 

    Current available actions are hard-coded and described below:
    - MINE = mine a block.
    - NEW_TX = conduct a new transaction between two nodes. 
    - FLIP = make a good node bad or a bad node good. 
    - RESOLVE_NODES = will resolve all nodes in a list of nodes provided. 
    - RESOLVE_ALL = will resolve all nodes.
    '''

    MINE=0
    NEW_TX=1
    FLIP=2
    RESOLVE_NODES=3
    RESOLVE_ALL=4

    @classmethod
    def show_action(cls, a):
        if a['type']==cls.MINE:
            atype = "MINE"
        elif a['type']==cls.NEW_TX:
            atype="NEW_TX"
        elif a['type']==cls.FLIP:
            atype="FLIP"
        elif a['type']==cls.RESOLVE_NODES:
            atype='RESOLVE_NODES'
        elif a['type']==cls.RESOLVE_ALL:
            atype='RESOLVE_ALL'
        logging.info("Action: %s %s %s " % (atype, a['n1'] if 'n1' in a else '', a['n2'] if 'n2' in a else ''))

    @classmethod
    def random_action(cls, network):
        '''
        Note: can put node names for actions that don't need node names but that's fine for now. 
        '''
        t = random.randint(0, 4) # 0, 1, or 2 -- current allowed methods
        n1 = n2 = None
        n2id = n1id = random.randint(0, len(network.nodes)-1)
        while t == cls.NEW_TX and n1id == n2id:
            n2id = random.randint(0, len(network.nodes)-1)
        if t == 0 or t == 1 or t == 2 or t == 4:
            n1 = network.nodes[n1id]
            n2 = network.nodes[n2id]
            action = {'type':t, 'n1':n1, 'n2':n2}
        elif t == 3:
            num_nodes = random.randint(0, len(network.nodes)-1)
            nodes = [network.nodes[random.randint(0, len(network.nodes)-1)] for i in range(num_nodes)]
            action = {'type':t,'nodes':nodes}
        return action

class Playbook:
    '''
        A playbook is simply a json file contains a list of events, each event is a list of actions that should the taken by the nodes in the network at each timestep.

        Actions could be: turn on/off a node, specify a node for mining, create/cancel a transaction, create a double spend transaction, etc.
        
        A playbook is deterministic and repeatable sequence of events that will happen in the network.
        
        Using a playbook, we can simply simulate a 51% attack or whatever behavior we want student to investigate. With this kind of deterministic behavior of the network, whatever assignment we planned eventually, we can compare students' result/output (as the status of network at the final timestep) against our expected output.
    '''

    def __init__(self, network):
        '''
        :param book: <list> the playbook. 
        :param network: <Network> the network for which the playbook will be written. 
        '''
        self.book = []
        self.network = network

    def set_book(self, book):
        self.book = book

    def play_book(self):
        '''
        '''
        logging.info("Playing book...")
        for id, action in enumerate(self.book):
            Action.show_action(action)
            if action['type'] == Action.MINE:
                self.network.mine(action['n1'])
            elif action['type'] == Action.NEW_TX:
                self.network.tx(action['n1'], action['n2'])
            elif action['type'] == Action.FLIP:
                # flip the loyalty of node -- if it's good, make it bad, and vice versa.
                self.network.flip_node(action['n1'])
            elif action['type'] == Action.RESOLVE_NODES:
                self.network.resolve_nodes(action['nodes'])
            elif action['type'] == Action.RESOLVE_ALL:
                self.network.resolve_all()
            time.sleep(1)


    def random_playbook(self, length, save=False, filename='playbook.pickle'):
        '''
        Generate a random playbookby default, save it off
        '''
        for i in range(length):
            self.book.append(Action.random_action(self.network))
        if save:
            pickle.dump(self.book, open(filename, 'wb'))

    def build_playbook(self, save=False, filename='playbook.pickle'):
        '''
        Allows the user to construct their own playbook. Will run until the user tells it to quit.
        '''
        addplay = 'y'
        while addplay == 'y':
            play = int(input('Enter action type (0 = mine, 1 = new transaction, 2 = flip node, 3 = resolve nodes, 4 = resolve all): '))
            # Force the user to behave
            while play not in [0, 1, 2, 3, 4]:
                try:
                    play = input('Enter action type (0 = mine, 1 = new transaction, 2 = flip node, 3= resolve nodes, 4 = resolve all): ')
                except:
                    print('invalid action type')
            if play == 0 or play == 2:
                node = input('Enter node name: ')
                while node not in self.network.nodes:
                    node = input('Node not found. Please enter node name: ')
                self.book.append({'type': play, 'n1': node})
            elif play == 1:
                node1 = input('Enter sending node name: ')
                while node1 not in self.network.nodes:
                    node1 = input('Node not found. Please enter sending node name: ')
                node2 = input('Enter receiving node name: ')
                while node2 not in self.network.nodes:
                    node2 = input('Node not found. Please enter receiving node name: ')
                self.book.append({'type': play, 'n1': node1, 'n2': node2})
            elif play == 3:
                nodes = []
                addnode = 'y'
                while addnode == 'y':
                    node = input('Enter name of node to add to the list of nodes to be resolved: ')
                    while node not in self.network.nodes:
                        node = input('Node not found. Enter name of node to add to the list of nodes to be resolved: ')
                    nodes.append(node)
                    addnode = input('Would you like to add another node to be resolved? (y/n) ')
                self.book.append({'type':play, 'nodes': nodes})
            elif play == 4:
                self.book.append({'type':play})
            addplay = input('Would you like to add another action to the playbook? (y/n) ')
        if save:
            pickle.dump(self.book, open(filename, 'wb'))

    def load_playbook(self, filename):
        '''
        loads a pre-created playbook.
        NOTE: right now, this requires that playbook be re-attached to a network with the same number of nodes on which it was generated. 
              If you want the simulation to run exactly as it did before, attach playbook to the exact same network as before. 
        '''
        self.book = pickle.load(open(filename, 'rb'))

    def save_playbook(self, filename):
        '''
        Save off a playbook you've created.
        '''
        pickle.dump(self.book, open(filename,'wb'))
