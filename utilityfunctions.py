'''
Created on Jul 10, 2019

@author: cplir-c
'''
from pathlib import Path
from weakref import finalize
from zipfile import is_zipfile
from json import loads, JSONDecodeError
from typing import Union
from html.parser import HTMLParser
from ast import literal_eval

def is_zipfile(fp,is_a_zipfile=is_zipfile):
    """Version of is_zipfile that can take Paths, in addition to str and objects with a read() method."""
    if isinstance(fp,Path):
        fp=str(fp)
    return is_a_zipfile(fp)

def existent_path(path:Path) -> Path:
    """Check if path exists and raise an error if it doesn't."""
    if not path.exists():
        raise ValueError("Path "+str(path)+" does not exist.")
    return path

_open_files = {}
def _count_closed_files(x):
    x=x[:2]
    if x not in _open_files:
        _open_files[x]=1
    else:
        _open_files[x]+=1
    #print(x,_open_files[x],end=' '+('\n'*(_open_files[x]%10==0)))

def file_generator(path:Union[str,Path],mode:str='r',opener=open):
    """Use finalizers to auto-close closable objects"""
    try:
        opened = opener(path,mode=mode)
        #print('opened',path)
        finalize(opened,opened.close)
        _count_closed_files(str(path)[:2])
        return opened
    except:
        try:
            opened.close()
        except NameError:
            pass
        print(path,mode,opener)
        raise
finalize(file_generator, print, _open_files)

def check_zipfile(path:Path) -> bool:
    """Checks if a file exists and is a zipfile."""
    return is_zipfile(existent_path(path))

def possibly_equal(first, second):
    """Equality comparison that propagates uncertainty.
    It represents uncertainty using its own function object."""
    if first is possibly_equal or second is possibly_equal:
        return possibly_equal #Propagate the possibilities
    return first == second

def read_binary_json(file):
    #join every line using commas
    contents = ','.join(line.strip().decode() for line in file)
    #Deduplicate commas
    while ',,' in contents:
        contents = contents.replace(',,',',')
    #Remove silly commas
    for opening in '{[(':
        issue_string = opening + ','
        while issue_string in contents:
            contents = contents.replace(issue_string, opening)
    for closing in ')]}':
        issue_string = ',' + closing
        while issue_string in contents:
            contents = contents.replace(issue_string, closing)
    while ':,' in contents:
        contents = contents.replace(':,', ':')
    
    try:
        return literal_eval(contents)
    except ValueError:
        try:
            return loads(contents)
        except JSONDecodeError:
            print(repr(contents))
            raise
        raise
read_binary_json(b"""{"l":{},"j":["k",{},[]]}""".split(b'\n'))

class parse_html(HTMLParser):
    """
    This class is an html parser that you use like a generator function.
    I hope this isn't too bad.
    e.g. : for href, title in parse_html(file_generator('~/Documents/myfile.html').read()): print(href,title)
    It's really designed for parsing modlist.html in modpacks.
    I don't know what program makes the modlist automatically, but I'll use it for better mod listing.
    All the links in them are broken, by the way.
    """
    __slots__ = 'data'
    def __init__(self, data):
        super().__init__()
        self.data = [[]]
        if hasattr(data,'decode'):
            data = data.decode()
        self.feed(data)
        del self.data[-1]
    def __iter__(self):
        return iter(self.data)
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            attrs = dict(attrs)
            self.data[-1].append(attrs['href'])
    def handle_data(self, data):
        if data[0].isalpha() and data[0].startswith('https://'):
            self.data[-1].append(data)
            self.data.append([])
        
def prettify_name(name:str) -> str:
    if isinstance(name, str):
        return name.replace('_',' ') if ' ' not in name else name
    return possibly_equal