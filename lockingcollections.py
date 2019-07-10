'''
Created on Jul 10, 2019

@author: cplir-c

This module contains locking collections.
These collections are mutable, but lock when hashed.
'''

class LockingList(list):
    "This class extends the built-in list class to support hashing by locking itself when hashed."
    __slots__=('____hash',)
    def __init__(self,iterable=()):
        self.____hash = None
        list.__init__(self,iterable)
    def __hash__(self):
        if self.____hash is None:
            self_hash = id(self) & 0xffffffff
            for k in self:
                if k is not self:
                    self_hash ^= hash(k)
                else:
                    self_hash ^= (self_hash>>1)
            self.____hash = self_hash
        return self.____hash
    def __eq__(self, other:object):
        if self.____hash is not None:
            if hasattr(other, '____hash') and other.____hash is not None:
                if other.____hash != self.____hash:
                    return False
            else:
                if self.____hash != hash(other):
                    return False
        return list.__eq__(self, other)
    def check_hashed(self):
        if self.____hash is not None:
            raise TypeError("You already hashed this List!")
    def __setitem__(self, key:int, value):
        self.check_hashed()
        if hasattr(value, '__hash__'):
            list.__setitem__(self, key, value)
        else:
            raise ValueError("Value "+str(value)+" is not hashable!")
    def append(self, item):
        self.check_hashed()
        if hasattr(item, '__hash__'):
            return list.append(self, item)
        else:
            raise ValueError("Item "+str(item)+" is not hashable!")
    def pop(self, index:int = -1):
        self.check_hashed()
        return list.pop(self, index)
    def extend(self, iterable):
        for value in iterable:
            self.append(value)

