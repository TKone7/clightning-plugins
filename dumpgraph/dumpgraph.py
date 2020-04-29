#!/usr/bin/env python3
import json

from lightning.lightning import LightningRpc
from lightning.plugin import Plugin
from os.path import join
from os import path
import sys

rpc_interface = None
plugin = Plugin(autopatch=True)


@plugin.method("dump")
def dump(plugin, output_path):
    """Creates a dump from the network graph known to the node and saves it as a csv in {path}.
    """
    filename = "dump.csv"
    if not path.isdir(output_path):
        return 'This is not a valid output directory. Input: {}'.format(output_path)

    listchannels = rpc_interface.listchannels()

    try:
        file = open(output_path + filename, "w")
        file.write("source\tdestination\tsort_channel_id\tsatoshis\tbase_fee_msat\tfee_per_millionth\n")
        for c in listchannels['channels']:
            file.write("{}\t{}\t{}\t{}\t{}\t{}\n".format(c['source'], c['destination'], c['short_channel_id'], c['satoshis'], c['base_fee_millisatoshi'], c['fee_per_millionth']))
        file.close()
    except IOError as e:
        return "I/O error({0}): {1}".format(e.errno, e.strerror)
    except: #handle other exceptions such as attribute errors
        return "Unexpected error:", sys.exc_info()[0]
    return '{} channels written at {}'.format(len(listchannels['channels']), output_path+filename)

@plugin.init()
def init(options, configuration, plugin):
    global rpc_interface
    plugin.log("start initialization of the dumpgraph plugin", level="debug")
    basedir = configuration['lightning-dir']
    rpc_filename = configuration['rpc-file']
    path = join(basedir, rpc_filename)
    plugin.log("rpc interface located at {}".format(path))
    rpc_interface = LightningRpc(path)
    plugin.log("dumpgraph successfully initialezed")

plugin.run()
