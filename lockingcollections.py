'''
Created on Jul 10, 2019

@author: cplir-c

This module contains locking collections.
These collections are mutable, but lock when hashed.
'''
from collections.abc import Hashable

class LockingList(list):
    "This class extends the built-in list class to support hashing by locking itself when hashed."
    __slots__=('____hash',)
    def __init__(self,iterable=()):
        self.____hash = None
        super().__init__(iterable)
    def __hash__(self):
        if self.____hash is None:
            self.____hash = self_hash = hash(()) & 0xffffffff
            #It's either this, or detect recursive hashing, or use symbolic math
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
        return super().__eq__(other)
    def check_hashed(self):
        if self.____hash is not None:
            raise TypeError("You already hashed this List!")
    @staticmethod
    def check_locking(other):
        if not isinstance(other, Hashable):
            raise ValueError("Value "+str(other)+" is not hashable!")
    def __setitem__(self, key:int, value):
        self.check_hashed()
        type(self).check_locking(value)
        super()[key] = value
    def append(self, item):
        self.check_hashed()
        type(self).check_locking(item)
        return super().append(item)
    def insert(self, key:int, item):
        self.check_hashed()
        type(self).check_locking(item)
        return super().insert(key,item)
    def extend(self, iterable):
        for value in iterable:
            self.append(value)
    for method in (list.clear,list.pop,list.reverse,list.sort,list.remove):
        template = '''def %s(self, *arguments):
    self.check_hashed()
    return list.%s(self,*arguments)'''
        name = method.__name__
        exec(template%(name,name))
    del template,name,method
hashtest = LockingList()
hashtest.append(LockingList((hashtest,)))
hashtest.insert(1,LockingList((LockingList(hashtest),)))
assert hash(hashtest)
print((hashtest))
try:
    hashtest.insert(8,[])
    raise Exception()
except: pass
del hashtest