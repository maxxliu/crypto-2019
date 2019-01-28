import hashlib
import json
import requests
import logging
import base58
from ecdsa import SigningKey, VerifyingKey
from threading import Lock, Thread
from time import time, sleep
from urllib.parse import urlparse
from uuid import uuid4
from message import Message
import copy

logging.basicConfig(level=logging.DEBUG)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.mqueue = [] #the message queue which contains msg from other node
        self.mqueue_mutex = Lock()
        self.current_transactions = []
        self.transactions_per_block = 5
        self.nodes = set()
        self.nodes_mutex = Lock()
        self.reward = 2 # 2 GoodCoins mined per block.
        self.address = ""
        self.utxo_pool = []
        self.sk, self.vk = self.generate_keypair()

    def start(self):
        # Create the genesis Block or sync with other nodes
        if len(self.nodes) == 0:
            self.new_transaction([],[], None, coinbase=True)
            self.new_block(previous_hash='1', proof=100)
        else:
            self.resolve_conflicts()


    ############################## MINING FUNCTIONS ##############################

    def proof_of_work(self, last_block):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes
         - Where p is the previous proof, and p' is the new proof
         - For the purposes of this assignment, p' = counter + last_hash

        :param last_block: <dict> last Block
        :return: <int>
        """
        print('TRYING TO SOLVE POW...')
        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        # difficulty should change with number of nodes
        num_nodes = len(self.nodes)
        difficulty = int(num_nodes ** 0.5) + 3
        print('DIFFICULTY = %d' % difficulty)
        # include the nodes verification key in the hash so that each node
        #   has a different proof of work
        my_vk = self.key_to_addr(self.vk)

        proof_counter = 0
        proof = str(difficulty) + '-' + my_vk + str(proof_counter)
        print('SAMPLE PROOF LOOKS LIKE: %s' % proof)
        while self.valid_proof(last_proof, proof, last_hash) is False:
            # print(proof_counter)
            proof_counter += 1
            proof = str(difficulty) + '-' + my_vk + str(proof_counter)

        print('SOLVED PROOF.')
        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validates the Proof: Does hash contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
            this is now a str
        :return: <bool> True if correct, False if not.
        """

        #### YOUR CODE HERE ####
        # You will modify the code below in order to create a new proof of work for the GoodCoin.
        # See the assignment document for additional instructions.

        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        # need to extract the difficulty level first
        difficulty = int(proof.split('-')[0])
        leading_zeros = ''.join(['0' for x in range(difficulty)])
        # print('GUESS: %s' % guess_hash[:difficulty])
        return guess_hash[:difficulty] == leading_zeros


    def mine(self):
        """
        Compute the proof, append a final transaction
        and mine a new Block in the chain
        :return: <dict> New Block
        """
        # We run the proof of work algorithm to get the next proof...
        last_block = self.last_block
        proof = self.proof_of_work(last_block)

        # Generate coinbase transaction.
        coinbase = self.new_transaction([],[], None, coinbase=True)

        # Since we have a new block, trigger peers to
        # resolve potential chain conflicts
        # No need to send any message, since we already ask peers to resolve/
        thr = Thread(target=self.force_resolve)
        thr.daemon = True
        thr.start()

        # Forge the new Block by adding it to the chain
        previous_hash = self.hash(last_block)

        return self.new_block(proof, previous_hash)

    def new_block(self, proof, previous_hash):
        """
        Create a new Block in the Blockchain
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Check for signature validity.
        for tx in self.current_transactions[1:]:
            if not self.verify_signature(tx):
                return 'Found invalid transaction in block.'

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    ############################## TRANSACTION FUNCTIONS ##############################

    def new_transaction(self, ins, outs, sk, coinbase=False):
        """
        Creates a new transaction to go into the next mined block.

        IMPORTANT NOTE: transaction inputs MUST include b58 encoded public keys or later signatures will NOT verify.

        :param ins: <dict> {tx_hash, addr, output_index, amount} Source(s) of funds.
        :param outs: <dict> {amount, addr} Recipient(s) of funds.
        :param sk: <SigningKey or str> The secret key used by payee to sign transaction.
        Must be the other half of the keypair used in the inputs to the transaction.
        :return: <int> The index of the Block that will hold this transaction
        """
        if coinbase:
            tx = {'ins': [],
                  'outs': [{'amount': self.reward, 'addr': self.key_to_addr(self.vk)}], # need to fix this
                  'time': time(),
                  'coinbase': True }
        else:
            tx = {'ins': [i for i in ins],
                  'outs': [o for o in outs],
                  'time': time(), # Basically a nonce so you don't get the same transaction twice.
                  'coinbase': False }
        if self.valid_tx(tx) != True:
            # Return the error code.
            return self.valid_tx(tx)
        # If it's valid, add the hash and put it in the current_txs pool.
        tx['hash'] = self.hash(tx)
        if coinbase:
            # Node will sign coinbase transaction with its own secret key.
            # Can't verify this because there's no associated public key to check.
            tx = self.sign_tx(tx, SigningKey.from_string(self.sk))
            self.current_transactions = [tx] + self.current_transactions
        else:
            if type(sk) is str:
                # assume base58 encoding here.
                sk = self.decode_sk(sk)
            elif type(sk) is bytes:
                # assume bytestring here.
                sk = SigningKey.from_string(sk)
            tx = self.sign_tx(tx, sk)
            if not self.verify_signature(tx):
                return 'Signature not valid.', 400
            self.current_transactions.append(tx)

        self.msgr.publish_message(Message.NEW_TX, json.dumps(tx))
        self.update_utxo_pool(tx)

        if len(self.chain) == 0:
            return 0
        else:
            return self.last_block['index'] + 1

    def valid_tx(self, tx):
        """
        Checks to see if a transaction is valid.
        """
        if tx['coinbase']:
            '''
            Should have no inputs, one amount, amount should be equal to reward.
            '''
            if len(tx['ins']) != 0:
                return "Coinbase transaction should have no inputs.", 400
            elif len(tx['outs']) != 1:
                return "Coinbase transaction should have a single output.", 400
            elif tx['outs'][0]['amount'] != self.reward:
                return "Output amount should equal reward.", 400
            else:
                return True
        else:
            '''
            All tx_inputs should be in UTXO pool.
            Sum of input amounts should equal sum of output amounts.
            Time should be less than current time?
            '''
            if len(tx['ins']) == 0:
                return "Must provide transaction inputs.", 400
            elif len(tx['outs']) == 0:
                return "Must provide transaction outputs.", 400
            elif not all(elem in self.utxo_pool for elem in tx['ins']):
                return "Inputs not found in UTXO pool.", 400
            elif sum([el['amount'] for el in tx['ins']]) != sum([el['amount'] for el in tx['outs']]):
                return "Sum of inputs does not equal sum of outputs.", 400
            elif len(list(set([el['addr'] for el in tx['ins']]))) != 1:
                # Check to make sure all inputs have same public key.
                return "All transaction inputs must share the same public key"
            elif tx['time'] > time():
                return "Transaction timestamp is incorrect.", 400
            return True

    def update_utxo_pool(self, tx):
        """
        Updates UTXO pool based on single transaction.
        :param tx: <dict> {ins, outs, time. coinbase, hash} Transaction object.
        """
        if not tx['coinbase']:
            for i in tx['ins']:
                self.utxo_pool.remove(i)
        for ix, o in enumerate(tx['outs']):
            self.utxo_pool.append({'tx_hash':tx['hash'], 'output_index':ix, 'amount':o['amount'], 'addr': o['addr']})
        return True


    ############################## SIGNATURE FUNCTIONS ##############################

    def sign_tx(self, tx, priv_key):
        '''
        Sign the hash of the transaction, which in effect says that the whole transaction is valid.
        NOTE: signature has been decoded to a latin1 string
        '''
        tx['sig'] = base58.b58encode(priv_key.sign(bytes(tx['hash'], 'utf-8'))).decode('utf-8')
        return tx


    def verify_signature(self, tx):
        '''
        Check that the transaction signature is valid.
        return True for valid signature else False
        '''
        if tx['coinbase'] == True: return True

        #### YOUR CODE HERE ####
        # Add in code below to verify that the signature over the transaction is indeed valid.
        # Hint: recall that the signature has been base58 encoded before being added to the tx (see sign_tx).
        print('Verifying signature of transaction')
        # the tx_hash has already been signed by the users signing key
        # we can take the public key given by a UTXO to verify that the
        # pk and sk are a pair
        tx_hash = tx['hash'] # convert hash to bytes
        msg = tx_hash.encode('utf-8')
        sig = tx['sig'] # convert signature back to bytes
        sig = base58.b58decode(sig)
        addr = tx['ins'][0]['addr'] # convert this back into the verifying key
        vk = VerifyingKey.from_string(base58.b58decode(addr))
        # now we can verify
        try:
            if vk.verify(sig, msg):
                return True
        except:
            return False


    @staticmethod
    def generate_keypair(to_str=True):
        '''
        Generates a keypair for a user.
        By design, this keypair is separate from the node itself, which ensures that multiple users can all use the same node.
        '''
        sk = SigningKey.generate() # this is the signing/secret key
        vk = sk.get_verifying_key() # this is the public/verifying key
        if to_str:
            return (sk.to_string(), vk.to_string())
        else:
            return (sk, vk)

    @staticmethod
    def key_to_addr(vk):
        '''
        A GoodCoin address is a base58 encoding of a user's public key, decoded into a str.

        Will also encode a user's private key in base58 encoding.
        '''
        if type(vk) != bytes:
            return base58.b58encode(vk.to_string()).decode('utf-8')
        else:
            return base58.b58encode(vk).decode('utf-8')

    @staticmethod
    def addr_to_vk(addr):
        '''
        Convert an address back into a verifying key format so you can verify a signature.
        '''
        return VerifyingKey.from_string(base58.b58decode(bytes(addr, 'utf-8')))

    @staticmethod
    def decode_sk(enc):
        '''
        Decode a signing key from its base58 encoding so you can actually use it.
        '''
        # Crude method to deal with user putting quotes around private key. Might not always work.
        if enc[0] == "'" or enc[0] == '"':
            enc = enc[1:-1]
        return SigningKey.from_string(base58.b58decode(enc))

    ############################## CONSENSUS FUNCTIONS ##############################

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            # print(f'{last_block}')
            # print(f'{block}')
            # print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof'],
                                    block['previous_hash']):
                return False

            last_block = block
            current_index += 1

        return True

    def get_hash_list(self, chain):
        #return a list of hashes, each hash represent a block in the chain
        l = []
        for block in chain:
            l.append(block['previous_hash'])
        if len(chain) > 0:
            l.append(self.hash(chain[-1]))
        return l

    def consensus(self, chains):
        '''
        Input:
        chains: a dict of hash list of peer nodes
                key: url of each peer node
                value: a list of hashes representing the blockchain of the node
        Output:
                return the url of the node that contains the 'longest chain w/ longest common prefix'
        '''

        #### YOUR CODE HERE ####
        # The following code is an example of the 'longest chain' policy
        # You will modify the code below to implement the 'longest chain w/ longest common prefix' policy
        # It will be difficult to test this function thru the web interface.
        # In tests/test_consensus.py, you will find helpful tests to ensure your code is running properly.
        print('RUNNING CONSENSUS...')
        # keep track of longest prefix and chain length so far and the node
        # that it corresponds to
        longest_prefix = 0
        longest_chain = 0
        longest_url = ''

        for url1, chain1 in chains.items():
            chain_len = len(chain1)
            if len(longest_url) == 0:
                longest_url = url1
                longest_chain = chain_len
            for url2, chain2 in chains.items():
                if url1 == url2:
                    pass
                elif (len(chain1) == 0) or (len(chain2) == 0):
                    pass
                else:
                    prefix_len = 0
                    i = 0
                    while chain1[i] == chain2[i]:
                        prefix_len += 1
                        i += 1
                        if (i >= len(chain1)) or (i >= len(chain2)):
                            break
                    # check if a better chain has been found
                    if prefix_len > longest_prefix:
                        longest_prefix = prefix_len
                        longest_chain = chain_len
                        longest_url = url1
                    elif prefix_len == longest_prefix:
                        if chain_len > longest_chain:
                            longest_prefix = prefix_len
                            longest_chain = chain_len
                            longest_url = url1
                    else:
                        # this chain pair is not compelling enough to switch to
                        pass

        return longest_url

    def resolve_conflicts(self):
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: True if our chain was replaced, False if not
        """
        if len(self.nodes) == 0: return
        hash_chains = {}
        hash_chains[self.address] = self.get_hash_list(self.chain)
        full_chains = {}
        full_chains[self.address] = self.chain

        neighbours = copy.deepcopy(self.nodes) #this is to avoid self.nodes change during iteration
        # Grab and verify the chains from all the nodes in our network
        peers = (node for node in neighbours if node != self.address)
        for node in peers:
            try:
                response = requests.get(f"http://{node}/jchain")
                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['chain']
                    # Check if the length is longer and the chain is valid
                    if self.valid_chain(chain):
                        full_chains[node] = chain
                        hash_chains[node] = self.get_hash_list(chain)
            except Exception as e:
                logging.error(e)
            finally:
                pass

        # Do the consensus checking.
        url = self.consensus(hash_chains)

        # Replace our chain if we discovered a valid chain longer than ours
        if len(full_chains[url]) > len(self.chain):
            self.chain = full_chains[url]
            self.utxo_pool = requests.get(f"http://{url}/jutxo").json()['utxos']
            self.current_transactions = requests.get(f"http://{url}/jtxs").json()['txs']
            return True
        return False

    def force_resolve(self):
        #this function is called in another thread,
        #we wait to make sure new block is added to our chain
        sleep(1);
        for node in self.nodes:
            logging.debug(node)
            requests.get(f"http://{node}/nodes/resolve")


    ############################## MESSAGING FUNCTIONS ##############################

    def set_msgr(self, msgr):
        self.msgr = msgr

    def process_message(self, msg):
        if msg.mtype == Message.NEW_TX:
            tx = msg.json_data()
            logging.debug("NEW_TX: %s" % tx)
            if not self.verify_signature(tx):
                logging.debug('=== Ignored TX w/ Invalid Signature == %s' % tx)
            else:
                logging.debug('+++ Verified New TX +++ %s' % tx)
                if tx['coinbase'] == False: #coinbase will be resolved
                    self.current_transactions.append(tx)
                    self.update_utxo_pool(tx)
        else:
            logging.error("Unsupported Message: %s" % msg)

    def process_mqueue(self):
        while True:
            if len(self.mqueue) == 0: break
            #depends on the format of data split by space may not work properly
            msg = Message(self.mqueue[0])
            self.process_message(msg)
            self.pop_message()

    def pop_message(self):
        self.mqueue_mutex.acquire()
        self.mqueue.pop(0)
        self.mqueue_mutex.release()

    def push_message(self, msg):
        self.mqueue_mutex.acquire()
        self.mqueue.append(msg)
        self.mqueue_mutex.release()


    ############################## NODE/PEER FUNCTIONS ##############################

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """
        self.nodes_mutex.acquire()
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            # Make sure you aren't re-adding node.
            if parsed_url.netloc not in self.nodes:
                self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            # Make sure you aren't re-addding something.
            if parsed_url.path not in self.nodes and parsed_url.path != self.address:
                self.nodes.add(parsed_url.path)
        else:
            self.nodes_mutex.release()
            raise ValueError('Invalid URL')

        self.nodes_mutex.release()

    def query_nodes(self):
        """
        Query nodes for its known nodes and add to set.
        """
        counter = 1
        while True:
            counter += 1
            sleep(1)
            self.process_mqueue() #check msg queue every 1s
            if counter % 30 != 0: continue #only query_node every 30s
            found_nodes = set()
            for node in self.nodes:
                try:
                    response = requests.get(f"http://{node}/nodes/peers")
                    if response.status_code == 200:
                        for neighbor in response.json()['nodes']:
                            found_nodes.add(neighbor)
                except requests.exceptions.ConnectionError as e:
                    logging.error("Error connecting to peer %s : %s", node, e)
            for node in found_nodes:
                try:
                    self.register_node(node)
                except ValueError as e:
                    logging.error("Error adding new node %s : %s",
                                  node, e)

    ############################## UTILITY FUNCTIONS ##############################

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block or Transaction
        :param block: <dict> Block or Transaction
        :return: <str>
        """

        # We must make sure that the Dictionary is Ordered,
        # or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # Returns the last block in the chain
        return self.chain[-1]
