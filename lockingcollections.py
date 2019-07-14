'''
Created on Jul 10, 2019

@author: cplir-c

This module contains locking collections.
These collections are mutable, but lock when hashed.
'''
from collections.abc import Hashable, Set, Sized
from collections import deque

#Oshit it doesn't work on tuples 
class LockingList(list):
    "This class extends the built-in list class to support hashing by locking itself when hashed."
    __slots__=()
    hashes = {}
    def __init__(self,iterable=(),hashes=hashes):
        super().__init__(iterable)
        self_id = id(self)
        if self_id in hashes:
            del hashes[self_id]
    def __hash__(self,hashes=hashes):
        print(self,id(self))
        self_id = id(self)
        self_hash = hashes.get(self_id,None)
        if self_hash is None:
            #It's either this, or detect recursive hashing, or use symbolic math
            hashes[self_id] = self_hash = hash(()) & 0xffffffff
            for k in self:
                if k is not self:
                    self_hash ^= hash(k)
                else:
                    self_hash ^= (self_hash>>1)
            hashes[self_id] = self_hash
        return self_hash
    def __eq__(self, other:object):
        if self.hashed() and hash(other) != hash(self):
            return False
        return super().__eq__(other)
    def check_hashed(self):
        if self.hashed():
            raise TypeError("You already hashed this List!")
    @staticmethod
    def check_locking(other):
        if not isinstance(other, Hashable):
            raise ValueError("Value "+str(other)+" is not hashable!")
    def hashed(self, hashes = hashes):
        return id(self) in hashes
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
        self.check_hashed()
        check_locking = self.check_locking
        for item in iterable:
            self.append(item)
    for method in (list.clear,list.pop,list.reverse,list.sort,list.remove,list.__delitem__):
        template = '''def %s(self, *arguments):
    self.check_hashed()
    return list.%s(self,*arguments)'''
        name = method.__name__
        exec(template%(name,name))
    del template,name,method,hashes
prt = lambda *k,**a: print(*k,**a) or k[0] if len(k) is 1 else k
hashtest = LockingList()
hashtest.append(LockingList(((hashtest,))))
#There would be an exception on the above line if tuples hashed their arguments
#instead, I suspect it only checks if it is hashable
#Whatever, this is good enough
hashtest.insert(1,LockingList((LockingList(hashtest),)))
try:
    hashtest.insert(8,[])
    raise TypeError()
except ValueError: pass
del hashtest,prt

class LinkedChunks:
    """
        This class implements the list interface using a linked list of lists.
        It's horrid to write.
    """
    __slots__ = ('start','end','size')
    def __init__(self, iterable = ()):
        self.start = []
        self.size = 0
        self.end = self.start
        self.extend(iterable)
    def append(self, item):
        self.size += 1
        if len(self.end) == 128:
            self.end.append([])
            self.end = self.end[128]
        self.end.append(item)
    def extend(self, iterable):
        iterator = iter(iterable)
        current = self.end
        size = self.size
        current_length = len(current)
        try:
            while True:
                for _ in range(128-current_length):
                    current.append(next(iterator))
                size += len(current) - current_length
                current.append([])
                current = current[-1]
        except StopIteration:
            size += len(current)
            self.end = current
            self.size = size
    __iadd__ = extend
    def len(self) -> int:
        return self.size
    def __getchunk(self, index:int):
        current = self.start
        remaining = index
        #must put in a look ahead one segment to see the end before arriving there
        #Otherwise it could go over the end when shortening the last link when there's one item in the last chunk
        #Or if the last item in the last link is a list with one item
        while len(current) < remaining:
            remaining -= len(current) - 1
            if len(current[-1]) == 1 and remaining > 0:
                current[-1] = current[-1][0]
            else:
                current = current[-1]
        return current
    def __getitem__(self, index:int):
        current, remaining = self.__getchunk(index)
        return current[remaining]
    def __delitem__(self, index):
        current, remaining = self.__getchunk(index)
        del current[remaining]
        self.size -= 1
    def pop(self, index = -1):
        if index < 0:
            index += self.size
        if index > self.size - len(self.end):
            return self.end.pop(index - self.size + len(self.end))
        current, remaining = self.__getchunk(index)
        current.pop(remaining)
    def __setitem__(self, index, item):
        current, remaining = self.__getchunk(index)
        current[remaining] = item
    def insert(self, index, item):
        current, remaining = self.__getchunk(index)
        current.insert(remaining, item)
        while len(current) == 128:
            current[-1].insert(0,current.pop(-2))
            current = current[-1]
    def __contains__(self, item):
        if item in self.end:
            return True
        for other in self:
            if other == item:
                return True
        return False
    class ChunkIterator:
        __slots__ = ('current','end','prev')
        def __init__(self, linked_chunks):
            self.current = linked_chunks.start
            self.end = linked_chunks.end
            self.prev = None
        def __next__(self):
            prev = self.current
            if self.prev is self.end:
                raise StopIteration
            if self.current is not self.end:
                self.current = self.current[-1]
            self.prev = self.current
            return prev
    def __chunk_iter(self):
        current = self.start
        end = self.end
        while current is not end:
            yield current
            current = current[-1]
        yield end
    def __iter(self):
        end = self.end
        for chunk in self.__chunk_iter():
            if chunk is not end:
                for i in range(len(chunk)-1):
                    yield chunk[i]
            else:
                yield from chunk
    class LinkedChunkIterator: 
        __slots__ = ('current','sub_index','index','size','end')
        def __init__(self, linked_chunks):
            self.current = linked_chunks.start
            self.size = linked_chunks.size
            self.end = linked_chunks.end
            self.index = 0
            self.sub_index = 0
        def __next__(self):
            self.sub_index += 1
            self.index += 1
            if self.index >= self.size:
                raise StopIteration()
            if self.sub_index >= len(self.current) - 1 and self.current is not self.end:
                #print(len(self.current),self.sub_index, self.index, self.size)
                self.current = self.current[self.sub_index]
                self.sub_index = 0
            return self.current[self.sub_index]
        
    def __iter__(self):
        return type(self).LinkedChunkIterator(self)
    def index(self, item):
        iterator = iter(self)
        for i in iterator:
            if i == item:
                return iterator.index
        raise IndexError
    def find(self, item):
        iterator = iter(self)
        for i in iterator:
            if i == item:
                return iterator.index
        return -1
    def remove(self, item):
        index = self.index(item)
        del self[index]
    def copy(self):
        return LinkedChunks(self)
    def reverse(self):
        current = self.start
        end = self.end
        while current is not end:
            next = current.pop()
            current.reverse()
            current.append(next)
            current = next
        current.reverse()
        self.start, self.end = self.end, self.start
        self.insert(-1,0)
        del self[-1]
    
            
linkedtest = LinkedChunks(range(999))
linkedtest.pop()
del linkedtest

class ShufflingSet:
    __slots__ = ('list')
    def __init__(self,iterable=()):
        self.list = LinkedChunks()
        self.update(iterable)
    def append(self, item):
        #Maximum shuffling!
        return self.list.append(item) if item not in self.list else False
    def update(self, iterable):
        deque(map(self.append,iterable),maxlen=0)
    __and__ = __add__ = update
    def isdisjoint(self, other):
        if isinstance(other, Sized) and len(other)*2 > len(self.list):
            other, self = self, other
        for item in other:
            if item in self:
                return False
        return True
    def symmetric_difference(self, iterable):
        pass
    def __contains__(self,item):
        for i in self:
            if i == item:
                index = i
        if index is -1:
            return False
        if index >> 2:
            #self.list[index], self.list[index//2] = self.list[index//2], self.list[index]
            del self.list[index]
            self.list.insert(index >> 2,item)
        return True
    def remove(self,item):
        self.list.remove(item)
    def __len__(self):
        return self.list.size
    def __iter__(self):
        return iter(self.list)
    def __str__(self):
        display = bytearray(b'{')
        for item in self.list:
            display += str(item).encode()
            display += b', '
        del display[-2:]
        display += b'}'
        return display.decode()
    def copy(self):
        return ShufflingSet(self)

def test():
    shuffleset = ShufflingSet()
    normalset = {}
    for function in "".split():
        shuffletest = shuffleset.copy()
        settest = normalset.copy()
        shufflefunc = getattr(shuffletest,function)
        setfunc = getattr(settest, function)
        
del shuffletest