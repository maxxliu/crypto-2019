'''
This file provides examples of how to work with the network.py and playbook.py components of the GoodCoin network. 
While it is possible to test and build your attack by editing and running this file, we recommend that you use IPython or some other command line Python interpreter to try things out. It will make your life easier. 

To test out this file, simply run "python3 examples.py" in the command line. 
'''
from network import Network
from playbook import Playbook

# Define a new GoodCoin network.
n = Network()
# Generate a network topology -- in this case, one with 5 nodes, where each node has at most 1 neighbor and is at most distance 1 from its neighbors. 
n.generate_random_topology(5,1,1)
# Start the network -- i.e. start the servers associated with all nodes in this network.
n.start()

# Define a new playbook for this network.
p = Playbook(n)
# Generate a random playbook with 10 actions for this network.
# Alternatively, you can build a playbook step-by-step using the p.build_playbook() function, which accepts user input to build the playbook.
p.random_playbook(10)
# Now run the playbook, which corresponds to having nodes conduct various transactions, mine blocks. and potentially flips nodes from good to bad.
p.play_book()

# Put the network to sleep for a bit to let all the changes percolate through.
time.sleep(2)
# Now turn off all the servers in this network.
n.stop()
