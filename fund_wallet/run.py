import hashlib
from hkdf import Hkdf
from os.path import expanduser
from hd import HDPrivateKey
from pycoin.symbols.btc import network

hsm_secret = open(expanduser("~/.lightning/bitcoin/hsm_secret"), "rb").read()
salt = bytes([0]) or b"\x00"
bip32_seed = Hkdf(salt, hsm_secret, hash=hashlib.sha256).expand(b"bip32 seed")

key = network.keys.bip32_seed(bip32_seed)
p0 = key.subkey_for_path('0/0/1')
print('priv',p0.wif())

pub = p0.sec().hex()
print('public', pub)
sig = network.msg.sign(p0, 'asdfasdf')
print(sig)
