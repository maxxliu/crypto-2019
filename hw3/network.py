'''
This file holds the code to construct a more robust version of the GoodCoin network and allows users to define arbitrarily topologies for the network.

This is the highest level of the GoodCoin stack (if it can be called a stack).
This defines the nodes in the network and how they interact. 
The goal is to make it easy for students to control the network. 

'''
# Normal packages
import os
import networkx as nx
import pickle
import random, time, logging, requests, copy
import subprocess as sub

import matplotlib.pyplot as plt
# GoodCoin packages
import server

logging.basicConfig(level=logging.INFO)

class Node():
    # Holds information about a particular node in the GoodCoin network.

    def __init__(self, name, addr, port, peers, role=1):
        '''
        Initializes a particular node object.

        :param addr: <str> IP address of node (i.e. '127.0.0.1')
        :param port: <str> port on which node will run
        :param peers: [int] A list of peer ports, assuming all node runs on the same IP w/ different port
        Each node is IDed by port number
        '''
        self.name = str(port)
        self.addr = addr
        self.port = port
        self.peers = peers
        self.role = role
        self.url = 'http://' + self.addr +':' + self.port
        self.good = True # Good nodes behave nicely. Bad nodes don't. 

    def __repr__(self):
        return 'Node ' + self.name + '; Address: ' + self.addr + ':' + self.port + '; Peers: ' + ','.join([str(p) for p in self.peers])

    def turn_on(self):
        '''
        Will start a GoodCoin instance running at this node's specified IP address/port.
        '''
        self.proc = sub.Popen(['python3', 'server.py', '-e', '-a', self.url])

    def turn_off(self):
        '''
        Will stop a GoodCoin instance running at this node's specified IP address/port.
        '''
        self.proc.kill()

    def genesis(self):
        try:
            requests.get(self.url+"/genesis")
        except requests.exceptions.RequestException as e:
            logging.error("Fail to create genesis block %s : %s" % (self.url, e))

    def chain(self):
        try:
            chain = requests.get(self.url+"/jchain").json()['chain']
            return chain
        except requests.exceptions.RequestException as e:
            logging.error("Fail to resolve %s : %s" % (self.url, e))

    def resolve(self):
        try:
            requests.get(self.url+"/nodes/resolve")
        except requests.exceptions.RequestException as e:
            logging.error("Fail to resolve %s : %s" % (self.url, e))

    def mine(self):
        try:
            requests.post(self.url+"/mine")
        except requests.exceptions.RequestException as e:
            logging.error("Fail to mine %s : %s" % (self.url, e))

    def flip_node(self):
        try:
            requests.post(self.url+"/nodes/flip")
        except requests.exceptions.RequestException as e:
            logging.error("Failed to flip %s : %s" % (self.url, e))


class Network():

    # Holds information about the general topology of the network.

    def __init__(self):
        '''

        '''
        self.graph = nx.Graph()
        self.nodes = []
        self.topology = {}

    def mine(self, node_name):
        self.topology[node_name].mine()

    def flip_node(self, node):
        '''
        Flips good node into bad node and vice versa.

        NOTE: bad nodes *must* be peers in the network in order to interact. 
        '''
        self.topology[node].good =  not self.topology[node].good
        self.topology[node].flip_node()

    def resolve_all(self):
        self.resolve_nodes(list(self.topology.keys()))

    def resolve_nodes(self, node_names):
        #resolve nodes until they have the same chain
        count = 0
        while count < 10:
            conflict = False
            last_chain = None
            last_name = None
            count += 1
            logging.info("Resolving nodes...%s" % node_names)
            for node_name in node_names:
                self.topology[node_name].resolve()
                if len(node_names) == 1: return
                current_chain = self.topology[node_name].chain()
                if last_chain is None:
                    last_chain = current_chain
                    last_name = node_name
                if current_chain != last_chain:
                    conflict = True
                    logging.info("Conflict: %s vs %s" % (last_name, node_name))
                last_chain = current_chain
                last_name = node_name
            if conflict == False:
                logging.info("Resolved")
                return
            time.sleep(1)
        logging.error("Failed to resolve nodes")

    def tx(self, n1, n2):
        '''
        make a transaction from node1 to node2
        i.e. find first transaction owned by node1 in utxo as input
             node2 as output
        '''
        try:
            node1 = self.topology[n1]
            node2 = self.topology[n2]
            utxos = []
            n1k = {}
            n2k = {}
            in_tx = output = None
            res = requests.get(node1.url+"/key")
            if res.status_code == 200:
                n1k['pk'] = res.json()['pk']
                n1k['sk'] = res.json()['sk']

            res = requests.get(node2.url+"/key")
            if res.status_code == 200:
                n2k['pk'] = res.json()['pk']
                n2k['sk'] = res.json()['sk']

            logging.info("TX: %s:%s => %s:%s" % (n1, n1k['pk'], n2, n2k['pk']))
            res = requests.get(node1.url+"/jutxo")
            if res.status_code == 200:
                utxos = res.json()['utxos']
            for utxo in utxos:
                if utxo['addr'] == n1k['pk']:
                    in_tx = utxo
            if in_tx is None:
                logging.info("Transaction Failed: No UTXO for %s exists" % n1)
                return
            output = {'addr': n2k['pk'], 'amount':in_tx['amount']}
            data = {'inputs': [in_tx], 'outputs': [output], 'priv_key': n1k['sk']}
            requests.post(node1.url+"/transactions/new", json=data)
            #found a tx from utxo
        except requests.exceptions.RequestException as e:
            logging.error("Fail to make transaction from %s to %s : %s" % (node1.url, node2.url, e))

    def stop(self):
        #turn on all nodes
        for node_name in self.nodes:
            logging.info("Turn off %s" % node_name)
            self.topology[node_name].turn_off()
            time.sleep(0.1)

    def start(self):
        #turn on all nodes
        for node_name in self.nodes:
            logging.info("Turn on %s" % node_name)
            self.topology[node_name].turn_on()
            time.sleep(1)

        logging.info("Registering, please wait...")
        self.register_peers()
        time.sleep(1)

        nodes = self.nodes
        logging.info("Mining genesis Block #%s" % nodes[0])
        self.topology[nodes[0]].genesis()
        time.sleep(1)

        # because the network is not fully connected now,
        # the propagation has to be from peer to peer
        logging.info("Resolving genesis block")
        nodes_to_sync = set(copy.deepcopy(self.nodes))
        while len(nodes_to_sync) > 0:
            resolved = set()
            for node_name in nodes_to_sync:
                # Couldn't we just put in a "sleep" command here? This would simulate the latency.
                # I guess we would have to multithread it in order to simulate it all going out at once.
                # Furthermore, couldn't we use the shortest path command to propogate further?
                node = self.topology[node_name]
                chain = node.chain()
                if len(chain) == 0:
                    node.resolve()
                else:
                    resolved.add(node_name)
                logging.debug("%s: chain size: %s" % (node_name, len(chain)))
            nodes_to_sync -= resolved
            time.sleep(1)
        logging.info("Resolved genesis block")

    def register_peers(self):
        '''
        register each ndoe with its peers
        should be called after generate the topology
        '''
        for _, node in self.topology.items():
            node_url = node.url
            logging.info("Registering %s" % node)
            for peer in node.peers:
                peer_name = peer[0]
                peer_url = self.topology[peer_name].url
                server.register_with_neighbor(node_url, peer_url)
                time.sleep(0.5)


    def define_topology(self):
        '''
        Note to user: probably best to draw out the topology you want before implementing it. 
        Asks for user input to define network topology, then loads this into the graph. 
        Will save the topology file if the user wants. 
        '''

        addnode = 'y'

        # Enter loop to generate topology until user is done. 
        while addnode == 'y':
            name = input('Enter node name (e.g. node1): ')
            addr = input('Enter IP address for node (e.g. 127.0.0.1): ')
            port = input('Enter port for node (e.g. 5000): ')
            addpeers = input('Would you like to define peers for this node? (y/n) ')
            while addpeers == 'y':
                peers = []
                while addpeers == 'y':
                    p_name = input('Enter peer name (e.g. node2): ')
                    p_dist = input('Enter distance from peer (e.g. 5): ')
                    peers.add((p_name, p_dist))
                    addpeers = input('Would you like to define another peer for this node? (y/n) ')
            # Store topology in file, just in case the user wants to save it.
            self.topology[name] = Node(addr, port, peers)
            # Actually add this node to the graph. 
            self.add_node(name, addr, port, peers)
            print('Node %s added! \n' % name)
            addnode = input('Would you like to add another node? (y/n) ')

        # Save off topology if the user wants
        saveit = input('Would you like to save this topology file? (y/n) ')
        if saveit == 'y':
            filename = input('Define a file name: ')
            pickle.dump(self.topology, open(filename, 'wb'))
            print('Saved topology to %s.pickle' % filename)
        return

    def load_topology(self, filename):
        '''
        Given a pre-created topology file called <filename>.pickle, load in that structure and add it to the graph.

        :param filename: <str> filename (must include directory path if file not in current working directory)
        '''
        self.topology = pickle.load(open(filename, 'rb'))
        for name in self.topology:
            # TODO only create one Node object, not two as we do now (in topology file and again on node creation)
            self.add_node(name, self.topology[name].addr, self.topology[name].port, self.topology[name].peers)
        return

    def generate_hw3_topology(self, base_url='127.0.0.1', base_port=3000):
        '''
        Given a pre-defined number of nodes, generate a random topology based on those nodes.
        Note: right now, will generate nodes that all run on localhost on ports 3000 to 3000 + num_nodes.

        :param num_nodes: <int> Number of nodes in the topology.
        :param max_distance: <int> Maximum distance between nodes.
        :param max_num_peers: <int> Maximum number of peers a node can have.
        :param base_url: <str> The URL for the nodes (assume all run on localhost for time being)
        :param base_port: <int> Starting number for port -- will increment.
        '''
        # Generate a list of all nodes.
        num_nodes= 9
        max_distance = 10 # please ignore this
        top = {
            'node0': ['node1', 'node2', 'node3', 'node7', 'node8'],
            'node1': ['node0', 'node2', 'node8'],
            'node2': ['node0', 'node1', 'node3'],
            'node3': ['node0', 'node2', 'node7', 'node8'],
            'node4': ['node5', 'node6', 'node7', 'node8'],
            'node5': ['node4', 'node6', 'node7'],
            'node6': ['node4', 'node5', 'node7'],
            'node7': ['node0', 'node3', 'node4', 'node5', 'node6'],
            'node8': ['node0', 'node1', 'node3', 'node4',]
            }

        for i in range(num_nodes):
            self.topology['node' + str(i)] = Node('node' + str(i), base_url, str(base_port + i*10), [])
        # Now, using that list, generate peers for the nodes.
        for node in top:
            for peer in top[node]:
                self.topology[node].peers.append((peer, max_distance))
            self.add_node(node, self.topology[node].addr, self.topology[node].port, self.topology[node].peers)
        self.draw_graph()
        return True

    def generate_random_topology(self, num_nodes, max_distance, max_num_peers,
                                 base_url='127.0.0.1', base_port=3000):
        '''
        Given a pre-defined number of nodes, generate a random topology based on those nodes.
        Note: right now, will generate nodes that all run on localhost on ports 3000 to 3000 + num_nodes.

        :param num_nodes: <int> Number of nodes in the topology.
        :param max_distance: <int> Maximum distance between nodes.
        :param max_num_peers: <int> Maximum number of peers a node can have.
        :param base_url: <str> The URL for the nodes (assume all run on localhost for time being)
        :param base_port: <int> Starting number for port -- will increment. 
        '''
        # Generate a list of all nodes.
        for i in range(num_nodes):
            self.topology['node' + str(i)] = Node('node' + str(i), base_url, str(base_port + i*10), [])
        # Now, using that list, generate peers for the nodes.
        for node in self.topology:
            num_peers = random.randint(1, max_num_peers)
            for i in range(num_peers):
                peer = random.choice(list(self.topology.keys()))
                # prevent self-peering
                while peer == node:
                    peer = random.choice(list(self.topology.keys()))
                self.topology[node].peers.append((peer, random.randint(1, max_distance)))
            self.add_node(node, self.topology[node].addr, self.topology[node].port, self.topology[node].peers)
        # Now save off this topology
        pickle.dump(self.topology, open('topology_' + str(num_nodes) + '_nodes.pickle', 'wb'))
        self.draw_graph()
        return True

    def add_node(self, name, addr, port, peers):
        '''
        Add a new node to the graph by name.

        :param name: <str> Easy to remember node name.
        :param addr: <str> IP address of node (i.e. '127.0.0.1')
        :param port: <str> port on which node will run
        :param peers: <list> list of peers for the node in the format (name, distance).
        '''
        # Make sure we don't get node name conflicts.
        if name in self.nodes:
            print('A node with this name is already defined.')
            return False
        else:
            self.nodes.append(name)
            self.graph.add_node(name)
            # Assume peer list is formatted as above.
            for p in peers:
                self.graph.add_edge(name, p[0], weight=p[1])
            return True

    def draw_graph(self):
        '''
        Plots a very simple graph visualization.
        
        '''
        color_map = []
        for node in self.graph:
            if self.topology[node].good:
                color_map.append('green')
            else:
                color_map.append('red')
        #nx.draw_shell(self.graph, with_labels=True)
        nx.draw_shell(self.graph, node_color = color_map, with_labels=True)
        plt.savefig("static/network.png", format="PNG")
        return True

    def remove_node(self, name):
        '''
        Remove a node with a given name from the topology.
        '''
        self.graph.remove_node(name)
        return

    def shortest_path(self, node1, node2):
        '''
        Returns the shortest path between two nodes.
        '''
        return nx.shortest_path(self.graph, node1, node2)

    


    
    



