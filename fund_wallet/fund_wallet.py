#!/usr/bin/env python3

import hashlib, requests, json
from hkdf import Hkdf
from os.path import expanduser, join
from os import listdir
from pycoin.symbols.btc import network

from bitcoinutils.script import Script
from bitcoinutils.setup import setup
from bitcoinutils.keys import P2wpkhAddress, P2wshAddress, P2shAddress, PrivateKey, PublicKey

from lightning.lightning import LightningRpc
from lightning.plugin import Plugin

base_url = 'https://exchange.api.bity.com'
rpc_interface = None
plugin = Plugin(autopatch=True)
updater = None

@plugin.init()
def init(options, configuration, plugin):
    global rpc_interface
    plugin.log('start initialization of the funding plugin', level='info')
    basedir = configuration['lightning-dir']
    rpc_filename = configuration['rpc-file']
    path = join(basedir, rpc_filename)
    plugin.log('rpc interface located at {}'.format(path), level="info")
    rpc_interface = LightningRpc(path)
    plugin.log('funding plugin successfully initialezed')

@plugin.method('bityorders')
def list_bityorders(plugin, order_id=None):
    """Lists the previously created orders on bity. Can be filtered with {order_id}
    """
    order_files = [e for e in listdir() if e[-5:] == '.json']
    if len(order_files) == 0:
        return 'There are no previous orders to look up.'
    orders = []
    for order_file in order_files:
        if not order_id or order_file[:-5] == order_id:
            with open(order_file, 'r', encoding='utf-8') as f:
                order = json.load(f)
                response = requests.get(base_url + '/v2/orders/' + order['id'], cookies = {'sessionid': order['sessionid']})
                if response.status_code != 200:
                    continue
                orders.append(response.json())

    if order_id:
        return orders[0] if len(orders) == 1 else 'No order with the given id found.'
    else:
        # print short overview
        return [{'id': order['id'], 'timestamp_awaiting_payment_since': order['timestamp_awaiting_payment_since']} for order in orders]

@plugin.method('fundwithfiat')
def fundwithfiat(plugin, amount, iban):
    """Creates a new buy order at Bity over the {amount} in satoshi, payable by {iban}.
    This works without registration or any KYC because during the process we provide proof of ownership by signing with the private key.
    """
    # unit = 'sat'
    # if amount[-3:] == 'sat' or amount[-4:] == 'sats' or amount[-1:] == 's' or 'satoshis' in amount or 'satoshi' in amount:
    #     unit = 'sat'

    if not isinstance(amount, int) or amount <= int(0):
        return 'Amount must be an integer satoshi value greater than zero'

    plugin.log('Gonna buy {} sats with iban {}'.format(amount, iban), level="info")

    newaddr = rpc_interface.newaddr('p2sh-segwit')['p2sh-segwit']
    plugin.log('address being used for buy {}'.format(newaddr), level="info")

    # try to derive the private key for the newly generated address
    priv_key = get_priv_key(newaddr)
    plugin.log('priv_key derived', level="info")

    # place new buy order
    place_url = base_url + '/v2/orders'
    data = {
        "input": {
        "currency": "CHF",
        "iban": iban,
        "type": "bank_account"
      },
      "output": {
      	"amount": "{:.8f}".format(amount/100000000),
        "crypto_address": newaddr,
        "currency": "BTC",
        "type": "crypto_address"
        }
    }
    response = requests.post(place_url, json=data)
    if response.status_code != 201:
        errors = response.json()['errors']
        return errors[0]
    location = response.headers.get('Location')
    plugin.log('new order is placed at location {}'.format(location), level="info")
    cookies = response.cookies.get_dict()

    # get the details for the signature
    response = requests.get(base_url + location, cookies = cookies)
    if response.status_code != 200:
        errors = response.json()['errors']
        return errors[0]
    msg = response.json()['message_to_sign']['body']
    sign_url = response.json()['message_to_sign']['signature_submission_url']
    order_id = response.json()['id']
    plugin.log('need to sign the received msg and send it here {}'.format(sign_url), level="info")

    # store order details together with cookies
    dumpdata = dict()
    dumpdata.update(cookies)
    dumpdata['id'] = order_id

    # sign the challenge received from bity
    sig = sign_message(priv_key, msg)
    plugin.log('message signed {}'.format(sig), level="info")

    # submit the signature
    headers = {'Content-type': 'text/plain'}
    response = requests.post(base_url + sign_url, data=sig, headers=headers)
    if response.status_code != 204:
        errors = response.json()['errors']
        return errors[0]

    response = requests.get(base_url + location, cookies = cookies)
    if response.status_code != 200:
        errors = response.json()['errors']
        return errors[0]

    input = response.json()['input']
    output = response.json()['output']
    payment_details = response.json()['payment_details']
    price_breakdown = response.json()['price_breakdown']
    # store detail to file for later reuse
    with open(str(order_id) + '.json', 'w', encoding='utf-8') as f:
        json.dump(dumpdata, f, ensure_ascii=False, indent=4)

    return {
        'id': order_id,
        'input': input,
        'payment_details': payment_details,
        'price_breakdown': price_breakdown
    }

def get_priv_key(address):
    # read master secret from hsm_secret
    hsm_secret = open(expanduser('~/.lightning/bitcoin/hsm_secret'), 'rb').read()
    # derive the bip32_seed
    salt = bytes([0]) or b'\x00'
    bip32_seed = Hkdf(salt, hsm_secret, hash=hashlib.sha256).expand(b'bip32 seed')
    master = network.keys.bip32_seed(bip32_seed)
    index = 0
    while True:
        # derive an index
        subkey = master.subkey_for_path('0/0/' + str(index))
        setup('mainnet')
        # create segwit address
        segwit = PrivateKey.from_wif(subkey.wif()).get_public_key().get_segwit_address()
        # wrap in P2SH address
        wrapped_p2sh = P2shAddress.from_script(segwit.to_script_pub_key())
        if wrapped_p2sh.to_string() == address:
            break
        index += 1
    plugin.log('found the address at index {}'.format(index), level="info")
    return master.subkey_for_path('0/0/' + str(index))

def sign_message(priv_key, message):
    sig = network.msg.sign(priv_key, message)
    return sig

plugin.run()
