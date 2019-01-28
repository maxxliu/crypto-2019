from blockchain import Blockchain
import pytest

'''
how to perform test:
go to the goodcoin folder and run:
pytest --disable-warnings -v

Please note following test case are simple examples, your code will be tested with more complicated cases.
Feel free to add more test cases before submitting your code.
'''
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
    hash_chains = {
        'url1':['b2', 'b3'],
        'url2':['b2','b3','b4','b5'],
        'url3':['b2','b3','b4','b5'],
        'url4': ['b6','b7','b8','b9'],
        'url5': ['b6','b7','b8','b9']
    }
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 4)
    assert hash_chains[bc.consensus(hash_chains)] == ['b2','b3','b4','b5']

def test5():
    bc = Blockchain()
    hash_chains = {
        'url1':['b0', 'b1'],
        'url2':['b2','b3','b4','b5'],
        'url3':['b2','b3','b4','b5'],
        'url4': ['b6','b7','b8','b9','b10'],
        'url5': ['b6','b7','b8','b9']
    }
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 5)

def test6():
    bc = Blockchain()
    hash_chains = {
        'url1':['b0'],
        'url2':['b2'],
        'url3':['b2'],
        'url4': ['b6'],
        'url5': ['b6']
    }
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 1)
    assert hash_chains[bc.consensus(hash_chains)] == ['b2']


def test7():
    bc = Blockchain()
    hash_chains = {
        'url1':['b0'],
        'url2':['b2']
    }
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 1)
    assert hash_chains[bc.consensus(hash_chains)] == ['b0']


def test8():
    bc = Blockchain()
    hash_chains = {
        'url1':[],
        'url2':[]
    }
    assert(bc.consensus(hash_chains) == 'url1')


def test9():
    bc = Blockchain()
    hash_chains = {
        'url1':['b0', 'b1', 'b2','b4','b6','b7']
    }
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 6)

def test10():
    bc = Blockchain()
    hash_chains = {}
    assert(bc.consensus(hash_chains) == '')

def test11():
    bc = Blockchain()
    hash_chains = {'url1':[]}
    assert(bc.consensus(hash_chains) == 'url1')


def test12():
    bc = Blockchain()
    hash_chains = {
        'url1':[],
        'url2':['b1'],
        'url3':['b1'],
        'url4':[]
    }
    assert(bc.consensus(hash_chains) == 'url2')
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 1)
    assert(hash_chains[bc.consensus(hash_chains)] == ['b1'])

def test13():
    bc = Blockchain()
    hash_chains = {
        'url1':[],
        'url2':['b1', 'b4'],
        'url3':['b4'],
        'url4':[]
    }
    assert(bc.consensus(hash_chains) == 'url2')
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 2)
    assert(hash_chains[bc.consensus(hash_chains)] == ['b1','b4'])

def test13():
    bc = Blockchain()
    hash_chains = {
        'url1':['b4'],
        'url2':['b1', 'b4','b4'],
        'url3':['b4','b4'],
        'url4':[]
    }
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 2)


def test14():
    bc = Blockchain()
    hash_chains = {
        'url1':['b1'],
        'url2':['b1', 'b4','b4'],
        'url3':['b4','b4'],
        'url4':[]
    }
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 3)

def test15():
    bc = Blockchain()
    hash_chains = {
        'url1':['b1'],
        'url2':['b9', 'b4','b4'],
        'url3':['b4','b4'],
        'url4':[]
    }
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 3)

def test16():
    bc = Blockchain()
    hash_chains = {
        'url1':['b1'],
        'url2':['b9', 'b4','b4'],
        'url3':['b4','b4'],
        'url4':[],
        'url5':['b11','b9', 'b4','b4'],
    }
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 4)

def test16():
    bc = Blockchain()
    hash_chains = {
        'url1':['b1'],
        'url2':['b1', 'b2','b3'],
        'url3':['b1','b2'],
        'url4':['b14'],
        'url5':['b1','b2', 'b3','b4','b5','b6'],
    }
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 6)


def test17():
    bc = Blockchain()
    hash_chains = {
        'url1':['b1','b4'],
        'url2':['b1', 'b4'],
        'url3':['b4','b1'],
        'url4':['b4','b1'],
        'url5':['b4','b1']
    }
    assert(len(hash_chains[bc.consensus(hash_chains)]) == 2)
    assert(hash_chains[bc.consensus(hash_chains)] == ['b1','b4'])

def test18():
    bc = Blockchain()
    hash_chains = {'url1':['b1', 'b2', 'b3'], 'url2':['b1','b2','b3'],
                    'url3':['b1','b2','b3','b4','b5'], 'url4':['b1','b2','b4','b6'],
                    'url5':['b1','b2','b4','b5','b6','b7']}
    assert(bc.consensus(hash_chains) == 'url5')

def test19():
    bc = Blockchain()
    hash_chains = {'url1':['b1', 'b2', 'b3'], 'url2':['b1','b3','b4'],
                    'url3':['b1','b2','b5','b6','b7'], 'url4':['b1','b2','b4','b5'],
                    'url5':['b1','b2','b4'], 'url6':['b1','b3','b4','b5','b6']}
    assert(bc.consensus(hash_chains) == 'url6')

def test20():
    bc = Blockchain()
    hash_chains = {'url1':['b1', 'b2', 'b3'], 'url2':['b1','b2','b3'],
                    'url3':['b1','b2','b3','b4','b5'], 'url4':['b1','b2','b4','b5'],
                    'url5':['b1','b2','b4','b5','b6'], 'url6':['b1','b3','b4','b5','b6','b7']}
    assert(bc.consensus(hash_chains) == 'url5')
