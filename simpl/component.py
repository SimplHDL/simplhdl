class component:

    name = ''
    files = []
    children = []
    parent = ''
    abspath = ''

    def __init__(self, name):
        self.name = name
        self.files = []
        self.children = []
        self.parent = ''
        self.abspath = ''
