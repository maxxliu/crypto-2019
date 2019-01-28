from flask import Flask, jsonify, request, render_template
from argparse import ArgumentParser
from blockchain import Blockchain
import threading
import requests
import logging
import ast
import zmq
import time, datetime, json
from messenger import Messenger
from message import Message


logging.basicConfig(level=logging.INFO)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Instantiate our Node
app = Flask(__name__)

# Instantiate the Blockchain
blockchain = Blockchain()

# Messenger init
msgr = Messenger()

############################## NAVBAR CONTROLS ##############################

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transactions')
def transactions():
    return render_template('transactions.html', transaction_info='')

@app.route('/mining')
def mining():
    return render_template('mining.html', mine_info='')

@app.route('/chain', methods=['GET'])
def chain():
    response = {
        'length': len(blockchain.chain),
        'chain': blockchain.chain

    }
    return render_template('blockchain.html', blockchain=response)

@app.route('/txs', methods=['GET'])
def txs():
    response = {
        'num_txs': len(blockchain.current_transactions),
        'txs': blockchain.current_transactions
    }
    # print(blockchain.utxo_pool)
    return render_template('txs.html', txs=response)

@app.route('/jtxs', methods=['GET'])
def full_txs():
    response = {
        'txs': blockchain.current_transactions
    }
    return jsonify(response), 200

@app.route('/genesis', methods=['GET'])
def genesis():
    blockchain.genesis()
    return jsonify({}), 200

@app.route('/keys', methods=['GET'])
def keys():
    return render_template('keys.html', key_info='')

@app.route('/utxo')
def utxo():
    response = {
        'num_utxos': len(blockchain.utxo_pool),
        'utxos': blockchain.utxo_pool
    }
    return render_template('utxo.html', utxo=response)

@app.route('/key')
def key():
    response = {
        'pk': blockchain.key_to_addr(blockchain.vk),
        'sk': blockchain.key_to_addr(blockchain.sk)
    }
    return jsonify(response), 200

@app.route('/nodes')
def nodes():
    peers = blockchain.nodes
    return render_template('nodes.html', peers=peers, key_info=[blockchain.key_to_addr(blockchain.vk), blockchain.key_to_addr(blockchain.sk)])

############################## FUNCTIONALITY ##############################

@app.route('/mine', methods=['GET', 'POST'])
def mine():
    if len(blockchain.chain) == 0:
        #haven't synced the genesis block
        logging.info("Syncing genesis @ %s" % blockchain.address)
        blockchain.force_resolve()
        logging.info("After Syncing genesis: %s %s" % (blockchain.address, len(blockchain.chain)))
    block = blockchain.mine()
    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    #return jsonify(response), 200
    return render_template('mining.html', mine_info=response)

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    # Check for required fields.
    values = request.form
    if len(values) == 0:
        values = json.loads(request.data)

    fields = [k for k in values]
    required = ['inputs', 'outputs', 'priv_key']
    if not all(k in fields for k in required):
        logging.info("xxxxx New TX Failed1 xxxxx")
        return render_template('transactions.html', transaction_info={'_message':'Incorrect transaction format.'})
    # Check to make sure they put in something.
    if len(values['inputs']) == 0 or len(values['outputs']) == 0 or len(values['priv_key']) == 0:
        logging.info("xxxxx New TX Failed2 xxxxx")
        return render_template('transactions.html', transaction_info={'_message':'Missing values -- please provide transaction inputs, outputs, and signing key'})
    # Create a new transaction
    try:
        inputs = ast.literal_eval(values['inputs'])
        outputs = ast.literal_eval(values['outputs'])
    except Exception as e:
        inputs = values['inputs']
        outputs = values['outputs']
    valid = blockchain.new_transaction(inputs, outputs, values['priv_key'])
    print(valid)
    if len(blockchain.current_transactions) >= blockchain.transactions_per_block:
            blockchain.mine()
            return blockchain.last_block['index']
    if type(valid) == int:
        response = {'_message': f'Transaction will be added to Block {valid}',
                    'ins': values['inputs'],
                    'outs': values['outputs']}
        return render_template("transactions.html", transaction_info=response)
    else:
        return render_template("transactions.html", transaction_info=valid[0])

@app.route('/keys/generate', methods=['POST'])
def generate_keypair():
    '''
    In the real world you would do this locally so the node can't see your pk/sk pair, but this isn't the real world, now is it?
    '''
    pk, vk = blockchain.generate_keypair()
    response = {
        'public_key': blockchain.key_to_addr(vk),
        'secret_key': blockchain.key_to_addr(pk)
    }
    return render_template('keys.html', key_info=response)

@app.route('/jutxo', methods=['GET'])
def full_utxo():
    response = {
        'utxos': blockchain.utxo_pool
    }
    return jsonify(response), 200

@app.route('/jchain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/good', methods=['GET'])
def is_peer_good():
    response = {
        'good': blockchain.good
    }
    return jsonify(response), 200

@app.route('/nodes/flip',  methods=['GET', 'POST'])
def flip_node():
    '''
    This will flip a node from good to bad or vice versa.
    '''
    blockchain.flip_node()
    response = {
        'message': 'Flipped node'
    }
    return jsonify(response), 200

@app.route('/nodes/register',methods=['POST'])
def register_node():
    # NOTE: correct format for this is something like node=127.0.0.1:4000
    values = json.loads(request.data)
    node = values['node'][0]
    msgr.subscribe(node)
    if node is None:
        return "Error: please supply a valid node argument (i.e. /nodes/register?node=http://127.0.0.1:4000)", 400
    try:
        blockchain.register_node(node)
    except ValueError as e:
        logging.error("Error registering node: %s error: %s", node, e)
    response = {
        'message': 'Current blockchain nodes',
        'total_nodes': list(blockchain.nodes),
    }

    # Skip resolving right after registration
    # Somehow calling /nodes/resolve here cause problem, but it works outside
    # We can resolve elsewhere
    # Sync node to all other nodes, do chain resolution.
    # for peer in blockchain.nodes:
    #     requests.get(f"http://{peer}/nodes/resolve") # chain resolution

    return jsonify(response), 201


@app.route('/nodes/peers', methods=['GET'])
def share_peers():
    response = {
        'message': 'Current blockchain nodes',
        'nodes': list(blockchain.nodes),
    }
    return jsonify(response), 200


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    '''
    Will perform resolution among chain versions. 
    '''
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


def register_with_neighbor(neighbor, address):
    # register current node with its neighbors
    payload = {'node': [address]}
    try:
        requests.post(f"{neighbor}/nodes/register", json=payload)
    except requests.exceptions.RequestException as e:
        logging.error("Error connecting to neighbor %s : %s", neighbor, e)


def sync_with_peers(seeds, address):
    neighbours = seeds.split(",")
    for neighbor in neighbours:
        try:
            blockchain.register_node(neighbor)
        except ValueError as e:
            logging.error("Error registering node: %s error: %s", neighbor, e)
            continue
        register_with_neighbor(neighbor, address)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-s', '--seeds', type=str, help='Initial neighboring blockchain nodes')
    parser.add_argument('-a', '--address', type=str, default="http://127.0.0.1:5000", help='Local address')
    parser.add_argument('-e', '--ensemble', action='store_true')
    args = parser.parse_args()
    blockchain.address = args.address.split("//")[1]
    blockchain.set_msgr(msgr)

    if args.seeds is not None:
        sync_with_peers(args.seeds, args.address)
    thr = threading.Thread(target=blockchain.query_nodes)
    thr.daemon = True
    thr.start()

    msgr.start(args.address, blockchain)

    if args.seeds is not None:
        for seed in args.seeds.split(','):
            msgr.subscribe(seed)

    if not args.ensemble: #for ensemble mode, we wait for instruction
        blockchain.start()

    app.run(host='0.0.0.0', port=int(args.address.split(":")[2]), debug=False, use_reloader=False)
