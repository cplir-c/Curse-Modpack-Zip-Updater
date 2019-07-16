'''
Created on Jul 10, 2019

@author: cplir-c
'''
from pathlib import Path, PurePath
from zipfile import ZipFile
from functools import lru_cache

from utilityfunctions import existent_path, is_zipfile, file_generator, \
  read_binary_json, check_zipfile, possibly_equal, parse_html
from lockingcollections import CombiningSet

class Mod:
    __slots__ = ('in_modpack','version','pretty_name', 'project_id', 'mod_id', 'file_id')
    def __init__(self, in_modpack, name:str, version:str=possibly_equal, project_id=possibly_equal, file_id=possibly_equal, mod_id=possibly_equal):
        self.in_modpack = in_modpack
        self.version = version
        self.pretty_name = name
        self.project_id = project_id
        self.file_id = file_id
        self.mod_id = mod_id
    def same_mod(self, other):
        if isinstance(other,Mod):
            mod_id_equality = possibly_equal(self.mod_id, other.mod_id)
            if mod_id_equality is not possibly_equal:
                return mod_id_equality
            
            project_id_equality = possibly_equal(self.project_id, other.project_id)
            if project_id_equality is not possibly_equal:
                return project_id_equality
            
            name_equality = possibly_equal(self.pretty_name, other.pretty_name)
            if name_equality is not possibly_equal:
                if not name_equality:
                    print('name equality',name_equality,self, other)
                return name_equality
            
            return possibly_equal
        return False
    def same_version(self, other):
        version_equality = possibly_equal(self.version, other.version)
        if version_equality is not possibly_equal:
            return version_equality
        
        return possibly_equal
    def __eq__(self, other):
        return self.same_mod(other)
    def __str__(self):
        return "<version "+self.version+" of "+self.pretty_name+">"
    def __repr__(self):
        return type(self).__name__+"(name='"+self.name+"',version='"+self.version+"')"

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
    def __str__(self):
        return type(self).__name__+" "+self.pretty_name+' (at '+str(self.path)+')'

class ZippedPack(Modpack):
    __slots__ = ('zipfile','manifest','mods')
    def __init__(self, path):
        if not isinstance(path,Path):
            path = Path(path)
        if not path.is_absolute():
            path = path.absolute()
        path = path.resolve()
        check_zipfile(path)
        if not is_zipfile(path):
            raise ValueError("There was no zipped modpack at "+str(path))
        
        read_zip = file_generator(path,opener=ZipFile)
        self.zipfile = read_zip
        
        manifest = file_generator('manifest.json', opener=read_zip.open)
        self.manifest = manifest = read_binary_json(manifest)
        
        name = manifest["name"]
        print('name',name)
        super().__init__(path,name)
    def open_file(self, relative_path:PurePath, mode='r'):
        return file_generator(relative_path, mode, self.zipfile.open)
    def list_files(self):
        return self.zipfile.namelist()
    @lru_cache(32)
    def list_mods(self):
        mods = CombiningSet()
        mods.update(self.list_override_mods())
        mods.update(self.list_modlist_mods())
        mods.update(self.list_manifest_mods())
        return mods
    @lru_cache(16)
    def list_override_mods(self):
        paths = self.list_files()
        files = list( #Using map and filter because I'm sure it does it one by one instead of saving intermediate results
            filter(
                lambda x:is_zipfile(x[1]),
                map(
                    lambda path,opener=self.zipfile.open:(path,file_generator(path, opener=opener)),
                    paths
                )
            )
        )
        mods = [ForgeMod(self,*path) for path in files]
        return mods
    def list_modlist_mods(self):
        modlist = self.open_file(PurePath('modlist.html'))
        modlist = modlist.read()
        parsed = parse_html(modlist)
        mods = [ListMod(self, href, title) for href, title in parsed]
    def list_manifest_mods(self):
        pass
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

class ForgeMod(Mod):
    '''
        Retrieve mod details from the (forge) mod jar.
    '''
    @staticmethod
    def new(modpack:Modpack, relative_path, mod_file = None) -> Mod:
        if mod_file is None:
            mod_file = modpack.open_file(relative_path)
        mod_jar = file_generator(mod_file, 'r', ZipFile)
        
        manifest = file_generator('mcmod.info',opener = mod_jar.open)
        manifests = read_binary_json(manifest)
        
        modids = []
        versions = []
        names = []
        
        for manifest in manifests:
            modids.append(manifest['modid'])
            versions.append(manifest['version'])
            names.append(manifest['name'])
        
        info = zip(names, versions, modids)
        #Assume the mod with the shortest modid is the main mod
        name, version, modid = min(info, key=lambda x: len(x[2]))
        
        return Mod(self, modpack, name, version, mod_id=modid)

class ListMod(Mod):
    """
        inspect modlist.html for names
    """
    def __new__(self, modpack:Modpack, href:str, title:str):
        project_id = href[href.rfind('/')+1:]
        name = title[:title.find('(')]
        return Mod(in_modpack=modpack, name=name, project_id=project_id)