from collections import defaultdict as default_dict
from zipfile import ZipFile
from pathlib import Path
from difflib import Differ,SequenceMatcher
from time import sleep
from pprint import pprint

from lockingcollections import LockingList as List
from utilityfunctions import check_zipfile
from modpackclasses import ZippedPack, PackInstance
'''
This module updates your multimc modpack.

It checks the difference between the old zip file and the new zip file, and changes the new zip file to make an updated instance when installed.

Line-level diffing is supported.

New plan:
    make Modpack instances from the two zips and one instance folder, and combine them into a new zip file using a CombiningSet.
'''
working_directory = Path.cwd()

def get_files(instance_folder, zip_file_folder, zip_new = None):
    "This function gets the zip files for updating, and the instance folder path."
    instance_folder = Path(working_directory,instance_folder).resolve()
    print('instance folder: '+str(instance_folder))
    #instance_pack = PackInstance(instance_folder)
    
    zip_file_folder = Path(working_directory,zip_file_folder).resolve()
    print('zip file folder: '+str(instance_folder))

    zip_old = zip_file_folder/(instance_folder.name+'.zip')
    print(zip_old)
    zip_old = zip_old.resolve()
    check_zipfile(zip_old)
    print('old zip:'+str(zip_old))
    old_zip_pack = ZippedPack(zip_old)
    
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
    new_zip_pack = ZippedPack(zip_new)

    return (instance_folder,old_zip_pack,new_zip_pack)

def update_from_zip(instance_folder, zip_file_folder, new_zip = None):
    "The main function. Updates the given instance using the zips in the folder. Both are string paths."
    instance_folder, zip_old_pack, zip_new_pack = get_files(instance_folder, zip_file_folder, new_zip)
    
    any(map(print,(zip_old_pack, zip_new_pack)))
    #It's going to be in the new zip file anyway.

update_from_zip(r'..\..\..\mc\mmc-stable-win32\MultiMC\instances\ATM3-_Expert_Shedding_Tiers-1.1.4',
                r'..\..\..\mc\mmc-stable-win32\MultiMC\instances\expert', 4)

