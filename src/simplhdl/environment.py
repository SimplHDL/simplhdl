import os

class environment:
    """docstring for environment."""
    def __init__(self):
        pass

    def _searchUp(self, filename):
        d = os.getcwd()
        while d != '/':
            d = os.path.dirname(d)
            if os.path.isfile(os.path.join(d,filename)):
                return d
        print 'Error: did not find file: '+filename
