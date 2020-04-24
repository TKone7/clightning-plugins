import json

from lightning.lightning import LightningRpc
from lightning.plugin import Plugin
from os.path import join
from os import path

rpc_interface = None
plugin = Plugin(autopatch=True)


@plugin.method("dump")
def dump(plugin, output_path):
    """Creates a dump from the network graph known to the node and saves it as a json in {path}.
    """
    filename = "dump.json"
    if not path.exists(output_path):
        return 'This path does not exist. Path: {}'.format(output_path)

    file = open(output_path + filename, "w")
    file.write("Your text goes here")
    file.close()

    return 'file written at {}'.format(output_path+filename)

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
