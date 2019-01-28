import json
class Message:
    '''
    enum of message types, to add more
    '''
    MINE = '1'
    NEW_TX = '2'

    # separator
    SEPARATOR = "::"

    def __init__(self, msg):
        self.addr = msg.split(self.SEPARATOR)[0]
        self.mtype = msg.split(self.SEPARATOR)[1]
        self.data = msg.split(self.SEPARATOR)[2]

    @classmethod
    def to_str(self, addr, mtype, data):
        return self.SEPARATOR.join([addr, mtype, data])

    def __str__(self):
        return self.SEPARATOR.join([self.addr, self.mtype, self.data])

    def json_data(self):
        return json.loads(self.data)
