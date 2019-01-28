import sys
sys.path.append("../")

from blockchain import Blockchain
from playbook import Playbook, Action
from network import Node, Network

import pytest

'''
how to perform test:
go to the goodcoin folder and run:
pytest --disable-warnings -v

Please note following test case are simple examples, your code will be tested with more complicated cases.
Feel free to add more test cases before submitting your code.
'''

###### HW2 Test Cases ######

def test1():
    bc = Blockchain()
    hash_chains = {'url1':['b1', 'b2', 'b3'], 'url2':['b1','b2','b3']}
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 3)

def test2():
    bc = Blockchain()
    hash_chains = {'url1':['b1', 'b2', 'b3'], 'url2':['b1','b2','b3'], 'url3':['b1','b3','b4','b5']}
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 3)

def test3():
    bc = Blockchain()
    hash_chains = {'url1':['b1', 'b2', 'b3'], 'url2':['b1','b2','b3'], 'url3':['b1','b2','b3','b4','b5']}
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 5)

def test4():
    bc = Blockchain()
    hash_chains = {'url1':['b1', 'b2', 'b3'], 'url2':['b1','b2','b3'],
                    'url3':['b1','b2','b3','b4','b5'], 'url4':['b1','b2','b4','b6'],
                    'url5':['b1','b2','b4','b5','b6','b7']}
    assert(bc.consensus(hash_chains) == 'url5')

def test5():
    bc = Blockchain()
    hash_chains = {'url1':['b1', 'b2', 'b3'], 'url2':['b1','b3','b4'],
                    'url3':['b1','b2','b5','b6','b7'], 'url4':['b1','b2','b4','b5'],
                    'url5':['b1','b2','b4'], 'url6':['b1','b3','b4','b5','b6']}
    assert(bc.consensus(hash_chains) == 'url6')

def test6():
    bc = Blockchain()
    hash_chains = {'url1':['b1', 'b2', 'b3'], 'url2':['b1','b2','b3'],
                    'url3':['b1','b2','b3','b4','b5'], 'url4':['b1','b2','b4','b5'],
                    'url5':['b1','b2','b4','b5','b6'], 'url6':['b1','b3','b4','b5','b6','b7']}
    assert(bc.consensus(hash_chains) == 'url5')

###### End of HW2 Test Cases ######
