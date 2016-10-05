
class Context(object):
    def __init__(self, node):
        self.node = node

    def enter(self, node):
        self.node.append(node)
        inst = self.__class__(node)
        return inst
