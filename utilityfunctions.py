'''
Created on Jul 10, 2019

@author: cplir-c
'''
from pathlib import Path
from weakref import finalize
from zipfile import is_zipfile
from json import load


def is_zipfile(fp,is_a_zipfile=is_zipfile):
    if isinstance(fp,Path):
        fp=str(fp)
    return is_a_zipfile(fp)

def existent_path(path:Path) -> Path:
    if not path.exists():
        raise ValueError("Path "+str(path)+" does not exist.")
    return path
        
def file_generator(path:Path,mode:str='r',opener=open):
    try:
        opened = opener(str(path),mode=mode)
        #print('opened',path)
        finalize(opened,opened.close)
        #finalize(opened,print,'closed '+str(opened))
        return opened
    except:
        try:
            opened.close()
        except NameError:
            pass

def check_zipfile(path:Path) -> bool:
    return is_zipfile(existent_path(path))

read_binary_json = load