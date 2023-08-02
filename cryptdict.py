from sh import Command
from bytestr import bytestr
from secrets import token_bytes, token_hex
from hashlib import scrypt
from gnupg import GPG
from os import scandir, mkdir, rmdir, remove
from collections import defaultdict
from pprint import pprint


class BytestrGPG(GPG):
    """GPG but all data read into bytestr so it can be cleared from RAM
    Also provides a kill agent method to reset password requirement.
    """
    def __init__(self):
        super().__init__(gpgbinary='gpg', gnupghome=None, verbose=False,
                 use_agent=False, keyring=None, options=None,
                 secret_keyring=None)

    def _read_data(self, stream, result, on_data=None):
        # Read the contents of the file from GPG's stdout 
        result.data = bytestr()
        data = stream.read(1)
        while data:
            result.data += data
            data = stream.read(1)

    @classmethod
    def kill_agent(restart=True):
        Command("gpg-connect-agent")(_in="KILLAGENT\n",_out="/dev/null")        

class Cryptdict(dict):
    """Memory secure, GPG encrypted replacement for dict based on bytestr.py and gnupg.py"""
    gpg = BytestrGPG()
    
    def __init__(self, name, path, cipher="AES256", master_key_fp=None, from_dict={}):
        self.bytestr_dict = defaultdict(list)
        self.cipher = cipher
        self.recipients = master_key_fp

        self.name = name
        self.path = self._get_bytestr("attrs", path + name)
        self.key_offset = self._get_bytestr("attrs", token_hex(16))

        if name not in (e.name for e in scandir(path)):
            mkdir(self.path)
        
        self.token_bytestr = self._get_bytestr("auth", token_bytes(256))
        self.salt_bytestr = self._get_bytestr("auth", token_bytes(64))
        self.kdf_bytestr = self._get_bytestr("auth")
        self.key_bytestr = self._get_bytestr("auth")
        
        for k in from_dict:
            self[k] = from_dict[k]
            

        print(self.bytestr_dict)
        print("SCRYPT KEY:", self.scrypt_key)
        
       
    def _get_bytestr(self, bytestr_dict_key="temp", *args, **kwargs):
        if kwargs.pop("clearmem",False) or bytestr_dict_key not in ("auth", "attrs", "temp"):
            self._delbytestr(bytestr_dict_key)

        self.bytestr_dict[bytestr_dict_key].append(bytestr(*args,**kwargs))
        return self.bytestr_dict[bytestr_dict_key][-1]

    def _get_key(self,k):
        return f"{k}_{self.key_offset}"

    def wipe_keys(self):
        self.key_bytestr.clearmem()
        self.kdf_bytestr.clearmem() 

    @property
    def scrypt_key(self):
        self.wipe_keys()
        self.kdf_bytestr.extend(f'{id(self)}')
        self.kdf_bytestr.extend(self.token_bytestr)
        self.kdf_bytestr.extend(f'{id(self.kdf_bytestr)}')
        self.key_bytestr += scrypt(self.kdf_bytestr, salt=self.salt_bytestr, n=1024, r=8, p=1, dklen=64).hex()
        return self.key_bytestr

    def __setitem__(self,k,v):
        print(f"SET ITEM {k}")
        item_path = self.getpath(k, f"{self.path}/{token_hex(16)}.pgp")
        gpg_kwargs = { "recipients":self.recipients, 
                       "symmetric":self.cipher, 
                       "passphrase":self.scrypt_key,
                       "output":item_path }
        if type(v) is bytestr:
            v = v.IO
        if hasattr(v,"read"):
            encrypt_result = self.gpg.encrypt_file(v, **gpg_kwargs)
        else:
            encrypt_result = self.gpg.encrypt(v, **gpg_kwargs)                          
        self.wipe_keys()

        if encrypt_result.ok:
            super().__setitem__(k,item_path)
     
    def __getitem__(self,k):
        print(f"GET ITEM {k}")
        item_path = self.getpath(k)
        if item_path:
            with open(item_path,"rb",buffering=0) as item:
                decrypt_result = self.gpg.decrypt_file(item, passphrase=self.scrypt_key)
                self.wipe_keys()

                if decrypt_result.ok:
                    data = self._get_bytestr(self._get_key(k), decrypt_result.data, clearmem=True)
                    decrypt_result.data.clearmem()
                    del decrypt_result
                else:
                    raise ValueError
            return data
        
    def get(self, k, default=None):
        return self[k] or default

    def getpath(self, k, default=None):
        return super().get(k, default)

    def _delbytestr(self,k):
        for i, data_bytestr in enumerate(self.bytestr_dict[k]):
            data_bytestr.clearmem()
            del data_bytestr
        #del self.bytestr_dict[k]

    def __delitem__(self,k):
        print(f"DEL ITEM {k}")
        item_path = self.getpath(k)
        if item_path:
            #unique_k = f"{k}_{self.key_offset}"
            self._delbytestr(self._get_key(k))
            remove(path=item_path)
            super().__delitem__(k)

    def __del__(self):
        self.destroy()

    def destroy(self):
        print(f"\nBEGIN DEL {self.path}\n")
        pprint( self.__dict__)
        self._delbytestr("auth")
        print("\nDESTROYED AUTH",)
        pprint( self.__dict__)
        for k, path in self.items():
            self._delbytestr(self._get_key(k))
            remove(path=path)
        
        print("\nREMOVED ALL FILES AND DESTROYED ALL USER DATA")
        pprint(self.__dict__)
        rmdir(self.path)
        self._delbytestr("attrs")
        self._delbytestr("temp")
        print("\nREMOVED ALL ATTRS AND TEMP DATA")
        pprint(self.__dict__)
        print("\n---DONE---\n")     


if __name__ == "__main__":
    pass