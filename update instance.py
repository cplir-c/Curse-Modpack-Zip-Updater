from collections import defaultdict as default_dict
from zipfile import ZipFile,ZipInfo,is_zipfile
from pathlib import Path
from difflib import Differ
from time import sleep
from sys import stderr
from shutil import copytree, ignore_patterns
from json import loads, dumps, JSONDecodeError
'''
This module updates your multimc modpack.

It checks the difference between the old zip file and the new zip file, and changes the new zip file to make an updated instance when installed.

Line-level diffing is supported.
'''
class List(list):
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
    def __eq__(self, other):
        if self.____hash is not None:
            if hasattr(other, '____hash') and other.____hash is not None:
                if other.____hash != self.____hash:
                    return False
            else:
                if self.____hash != hash(other):
                    return False
        return list.__eq__(self, other)
    def __setitem__(self, key, value):
        if self.____hash is not None:
            raise ValueError("You already hashed this List!")
        if hasattr(value, '__hash__'):
            list.__setitem__(self, key, value)
        else:
            raise ValueError("Value "+str(value)+" is not hashable!")
    def append(self, item):
        if self.____hash is not None:
            raise ValueError("You already hashed this List!")
        if hasattr(item, '__hash__'):
            return list.append(self, item)
        else:
            raise ValueError("Item "+str(item)+" is not hashable!")
    def pop(self, index = -1):
        if self.____hash is not None:
            raise ValueError("You already hashed this List!")
        return list.pop(self, index)
    def extend(self, iterable):
        if self.____hash is not None:
            raise ValueError("You already hashed this List!")
        for value in iterable:
            self.append(value)
hash_test = List()
hash_test._List____hash = 54
hash(hash_test)
def name_from_instance(instance_folder):
    name = None
    with open(instance_folder / 'instance.cfg','r') as config_file:
        for line in config_file:
            if line.startswith('name='):
                name = line[5:]
                return name

def check_zipfile(zip_file):
    if not zip_file.exists() and is_zipfile(zip_file):
        raise FileNotFoundError(str(zip_file))

def get_files(instance_folder, zip_file_folder):
    working_dir = Path.cwd()
    instance_folder = Path(working_dir,instance_folder)
    check_zipfile(instance_folder)
    print('instance folder:'+str(instance_folder))
    
    zip_file_folder = Path(working_dir,zip_file_folder)
    check_zipfile(zip_file_folder)
    print(':'+str(instance_folder))

    instance_name = name_from_instance(instance_folder)
    print(instance_name,instance_folder)
    zip_old = Path(zip_file_folder,instance_folder.name+'.zip')
    print(zip_old)
    check_zipfile(zip_old)
    print('old zip:'+str(zip_old))
    
    def difference_key(other,o=zip_old):
        return sum(a==b for a,b in zip(other.name,o.name))
    
    folder_contents = [file for file in zip_file_folder.iterdir() if file.exists() and is_zipfile(file)]
    folder_contents.sort(key=difference_key,reverse=True)
    zip_names = [file.name for file in folder_contents]

    print('Zip files available:')
    i = None #To ensure it's visible after the loop
    for i,zip_new in enumerate(folder_contents):
        print(str(i)+')',zip_new)
        
    zip_new = None
    while zip_new not in (list(map(str,range(i+1)))+zip_names):
        zip_new = input('Zip file to update to? ')
    
    if zip_new in zip_names:
        zip_new = zip_names.index(zip_new)
    else:
        zip_new = int(zip_new)
    zip_new = folder_contents[zip_new]
    print("You selected",zip_new)
    sleep(1)
    check_zipfile(zip_new)

    return (instance_folder,zip_old,zip_new)

def inspect_files(old_zip, new_zip, in_both):
    old_contents = List(map(old_zip.getinfo,in_both))
    new_contents = List(map(new_zip.getinfo,in_both))

    contents_to_ignore = set() #For clarity

    lines_to_delete = default_dict(List)
    lines_to_add = default_dict(List)

    
    # If the CRC of the files is the same, check the contents
    # If the contents of the files matches, ignore the files
    # Otherwise, Diff the contents and save the diff
    
    for name, old_info, new_info in zip(in_both,old_contents,new_contents):
        if old_info.CRC == new_info.CRC and old_info.file_size == new_info.file_size:
            #Compare the contents
            with old_zip.open(name) as old_file, \
                 new_zip.open(name) as new_file:
                if old_file.read() == new_file.read():
                    contents_to_ignore.add(name)
                    continue # Ignore the identical files
        #The files are different
        with old_zip.open(name) as old_file, \
             new_zip.open(name) as new_file:
            old_contents = List(old_file.readlines())
            #print(old_contents[0])
            new_contents = List(new_file.readlines())
        old_contents = [str(line)[2:-1] for line in old_contents]
        new_contents = [str(line)[2:-1] for line in new_contents]
        diff = List(Differ().compare(old_contents, new_contents))
        print('inspected', name)
        #try:
        #    #print(*diff,sep='\n',end='\n\n')
        #except UnicodeEncodeError:
        #    print('errored on',name,file=stderr)
        for line in diff:
            if line.startswith('+ '):
                lines_to_add[name].append(line[2:])
                #try:print(line)
                #except UnicodeEncodeError: pass
            elif line.startswith('- '):
                lines_to_delete[name].append(line[2:])
                #try:print(line)
                #except UnicodeEncodeError: pass
            elif line.startswith('? '): pass
                #ignore this line
            else: pass
                #Also ignore this line
                
        #sleep(0.2)
    return (lines_to_delete,lines_to_add)

from pprint import pprint

def compare_zipfile_contents(zip_old, zip_new):
    #Don't print this. It's way too long. Prints the entire zip file contents, and all subfolders' contents too.
    #[*map(pprint,map(ZipFile.namelist,(zip_old,zip_new)))]

    old_zip_contents, new_zip_contents = map(frozenset,map(ZipFile.namelist,(zip_old,zip_new)))
    #print(*(old_zip_contents & new_zip_contents),sep='\n',end='\n\n')
    #print(*new_zip_contents,sep='\n',end='\n\n')
    #Old files
    contents_to_delete = old_zip_contents - new_zip_contents
    assert not (contents_to_delete & new_zip_contents)
    assert contents_to_delete < old_zip_contents
    #New files
    contents_to_add = new_zip_contents - old_zip_contents
    assert not (contents_to_add & old_zip_contents)
    assert contents_to_add < new_zip_contents
    #Interesting files
    contents_to_inspect = old_zip_contents & new_zip_contents

    (lines_to_delete,lines_to_add) = inspect_files(zip_old, zip_new, contents_to_inspect)
    return contents_to_delete, contents_to_add, lines_to_delete, lines_to_add

def update_from_zip(instance_folder, zip_file_folder):
    instance_folder, zip_old_path, zip_new_path = get_files(instance_folder, zip_file_folder)
    zip_old,zip_new = map(ZipFile,map(str,(zip_old_path, zip_new_path)))

    (files_to_delete, files_to_add, lines_to_delete, lines_to_add) = compare_zipfile_contents(zip_old, zip_new)

    print(*files_to_delete,sep='\n',end='\n\n')

    #mods_to_delete = lines_to_delete['manifest.json']
    #mods_to_download = lines_to_add['manifest.json']
    #pprint(mods_to_delete)
    #pprint(mods_to_download)
    del lines_to_delete['manifest.json'],lines_to_add['manifest.json']
    #It's going to be in the new zip file anyway.
    
update_from_zip(r'..\mc\mmc-stable-win32\MultiMC\instances\expert_alpha-1.1.3',
                r'..\mc\mmc-stable-win32\MultiMC\instances\expert')
    
