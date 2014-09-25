class Namespace(object):
    def __init__(self, **kwargs):
        for (kw, val) in kwargs.items():
            setattr(self, kw, val)
    def __repr__(self):
        string = ", ".join("{0}={1}".format(k, repr(v)) for (k, v) in
                           self.__dict__.items())
        return "Namespace({0})".format(string)
    def items(self):
        return self.__dict__.items()
    def __iter__(self):
        return iter([x for x in self.__dict__.keys() if not x.startswith("__")])
