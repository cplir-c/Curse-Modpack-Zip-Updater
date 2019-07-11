'''
Created on Jul 10, 2019

@author: cplir-c
'''
from utilityfunctions import existent_path, is_zipfile, file_generator, \
  read_binary_json
from functools import lru_cache
from pathlib import Path, PurePath
from zipfile import ZipFile

class Mod:
    __slots__ = ('path','version','modid','pretty_name')
    def __init__(self, path:str, pretty_name:str, version:str, modid:str):
        self.path = path
        self.version = version
        self.pretty_name = pretty_name
        self.modid = modid

class CurseMod(Mod):
    """
        Retrieve a mod from the curseforge website.
    """
    __slots__ = ('project_id','file_id','url_name')
    def __init__(self, project_id, file_id):
        pass

#Download a curse mod

class Modpack:
    __slots__ = ('path','pretty_name')
    def __init__(self, path:Path, pretty_name:str):
        self.path = existent_path(path.resolve())
        self.pretty_name = pretty_name
    def list_mods(self):
        raise NotImplementedError
    def list_files(self):
        raise NotImplementedError
    def open_file(self, relative_path:PurePath, mode='r'):
        raise NotImplementedError
    def copy_pack(self):
        raise NotImplementedError

class ZippedPack(Modpack):
    __slots__ = ('zipfile',)
    def __init__(self, path):
        if not isinstance(path,PurePath):
            path = Path(path)
        if not path.is_absolute():
            path = path.absolute()
        path = path.resolve()
        existent_path(path)
        if not is_zipfile(path):
            raise ValueError("The zipped modpack path "+str(path)+" was not a path to a zip file.")
        
        read_zip = file_generator(path,opener=ZipFile)
        self.zipfile = read_zip
        
        name = None
        with read_zip.open('manifest.json') as manifest:
            for line in manifest:
                if line.lstrip().startswith(b'"name":'):
                    line = line.strip()[:-1]
                    print(line)
                    name = str(line[line.rstrip(b'"').rindex(b'"'):line.rindex(b'"')])
        print('name',name)
        super().__init__(path,name)
    
    def list_mods(self):
        read_binary_json(self.zipfile.open('manifest.json'))
        
        
class PackInstance(Modpack):
    @staticmethod
    def name_from_instance(instance_folder:Path) -> str:
        "This function extracts the name of the MultiMC instance from the instance config file."
        name = None
        with open(str(instance_folder/'instance.cfg'),'r') as config_file:
            for line in config_file:
                if line.startswith('name='):
                    name = line[5:]
                    return name

