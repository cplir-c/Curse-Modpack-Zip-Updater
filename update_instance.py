from collections import defaultdict as default_dict
from zipfile import ZipFile
from pathlib import Path, PurePath
from difflib import Differ,SequenceMatcher
from time import sleep
from pprint import pprint

from lockingcollections import LockingList as List
'''
This module updates your multimc modpack.

It checks the difference between the old zip file and the new zip file, and changes the new zip file to make an updated instance when installed.

Line-level diffing is supported.

New plan:
    Copy the newer zip file, and put overrides in there.
    Copy the files from the instance to the new zip file if 
      they aren't the same as the ones in the overrides in the old zip file.
    Exclude mods in the old zip file's manifest from copying.
    Optionally copy all mods that aren't in the new zip file's manifest to
      the new zip file and remove the mods listed in the new zip's manifest
      that are already downloaded.
    
    Copy the newer zip file to a new zip file.
    Compare the files from the instance folder and the old zip file's overrides folder.
    Copy files in the instance folder that 
'''

def get_files(instance_folder, zip_file_folder, zip_new = None):
    "This function gets the zip files for updating, and the instance folder path."
    instance_folder = Path(working_directory,instance_folder).resolve()
    print('instance folder: '+str(instance_folder))
    
    zip_file_folder = Path(working_directory,zip_file_folder).resolve()
    print('zip file folder: '+str(instance_folder))

    instance_name = name_from_instance(instance_folder)
    print(instance_name,instance_folder)
    zip_old = zip_file_folder/(instance_folder.name+'.zip')
    print(zip_old)
    zip_old = zip_old.resolve()
    check_zipfile(zip_old)
    print('old zip:'+str(zip_old))
    
    matcher = SequenceMatcher(b=zip_old.name)
    def difference_key(other:Path,matcher:SequenceMatcher=matcher):
        matcher.set_seq1(other.name)
        return matcher.ratio()
    del matcher
    
    folder_contents = [file for file in zip_file_folder.iterdir() if check_zipfile(file)]
    folder_contents.sort(key=difference_key,reverse=False)
    zip_names = [file.name for file in folder_contents]
    
    i=len(folder_contents)
    print(zip_new)
    if zip_new is not None:
        zip_new = str(zip_new)
    while zip_new not in (list(map(str,range(i)))+zip_names):
        print('Zip files available:')
        for i,zip_new in enumerate(folder_contents):
            print(str(i)+')',zip_new)
        
        zip_new = input('Zip file to update to? ')
    
    if zip_new in zip_names:
        zip_new = zip_names.index(zip_new)
    else:
        zip_new = int(zip_new)
    zip_new = folder_contents[zip_new]
    print("You selected",zip_new.name)
    sleep(1)
    check_zipfile(zip_new)

    return (instance_folder,zip_old,zip_new)

def inspect_files(old_zip:ZipFile, new_zip:ZipFile, in_both:frozenset):
    old_contents = List(map(old_zip.getinfo,in_both))
    new_contents = List(map(new_zip.getinfo,in_both))
    
    print(old_zip.filename,new_zip.filename)
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
        print(diff)
        print(old_contents)
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
            #elif line.startswith('? '): pass
                #ignore this line
            #else: pass
                #Also ignore this line
                
        #sleep(0.2)
    print(len(contents_to_ignore))

    return (lines_to_delete,lines_to_add)

def compare_zipfile_contents(zip_old, zip_new):
    "This function returns the differences between two zip files, including changed lines."
    #Don't print this. It's way too long. Prints the entire zip file contents, and all subfolders' contents too.
    #[*map(pprint,map(ZipFile.namelist,(zip_old,zip_new)))]

    old_zip_contents, new_zip_contents = map(frozenset,map(ZipFile.namelist,(zip_old,zip_new)))
    #print(*(old_zip_contents & new_zip_contents),sep='\n',end='\n\n')
    #print(*new_zip_contents,sep='\n',end='\n\n')
    #Old files
    contents_to_delete = old_zip_contents - new_zip_contents
    assert not (contents_to_delete & new_zip_contents)
    print(len(contents_to_delete),len(old_zip_contents))
    assert contents_to_delete <= old_zip_contents
    #New files
    contents_to_add = new_zip_contents - old_zip_contents
    assert not (contents_to_add & old_zip_contents)
    print(len(contents_to_add),len(new_zip_contents))
    assert contents_to_add <= new_zip_contents
    #Interesting files
    contents_to_inspect = old_zip_contents & new_zip_contents

    (lines_to_delete,lines_to_add) = inspect_files(zip_old, zip_new, contents_to_inspect)
    return contents_to_delete, contents_to_add, lines_to_delete, lines_to_add

def update_from_zip(instance_folder, zip_file_folder, new_zip = None):
    "The main function. Updates the given instance using the zips in the folder. Both are string paths."
    instance_folder, zip_old_path, zip_new_path = get_files(instance_folder, zip_file_folder, new_zip)
    ZippedPack(zip_old_path)
    raise
    zip_old,zip_new = map(ZipFile,map(str,(zip_old_path, zip_new_path)))
    
    (files_to_delete, files_to_add, lines_to_delete, lines_to_add) = compare_zipfile_contents(zip_old, zip_new)

    if not any((files_to_delete, files_to_add, lines_to_delete, lines_to_add)):
        raise ValueError("The zip files you selected: "+zip_old_path+", and "+zip_new_path+" were found to be the same. Please don't try to update twice!")
    
    #print(*files_to_delete,sep='\n',end='\n\n')
    any(map(pprint,(lines_to_delete,lines_to_add)))
    #mods_to_delete = lines_to_delete['manifest.json']
    #mods_to_download = lines_to_add['manifest.json']
    #pprint(mods_to_delete)
    #pprint(mods_to_download)
    if lines_to_delete:
        del lines_to_delete['manifest.json']
    if lines_to_add:
        del lines_to_add['manifest.json']
    #It's going to be in the new zip file anyway.

update_from_zip(r'..\..\..\mc\mmc-stable-win32\MultiMC\instances\ATM3-_Expert_Shedding_Tiers-1.1.4',
                r'..\..\..\mc\mmc-stable-win32\MultiMC\instances\expert', 4)
    
