class AluIf:

    def __init__(self, a, b, x, cmd, ready, valid, busy, clock, reset):
        self.a = a
        self.b = b
        self.x = x
        self.cmd = cmd
        self.ready = ready
        self.busy = busy
        self.valid = valid
        self.clock = clock
        self.reset = reset
