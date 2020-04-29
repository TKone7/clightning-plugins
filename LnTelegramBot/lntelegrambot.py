#!/usr/bin/env python3

import json
from os.path import join
import threading, time, signal, os

# Lightning stuff
from lightning.lightning import LightningRpc
from lightning.plugin import Plugin
# Telegram stuff
from telegram.ext import Updater, CommandHandler
from telegram import Bot

rpc_interface = None
plugin = Plugin(autopatch=True)
updater = None

# @plugin.method("startbot")
# def start(plugin, token, chat_id):
#     """Start the telegram bot with the given {token} talking only to a specific {chat_id}.
#
#     """
#     global updater
#     plugin.log("logg something", level="debug")
#     updater = Updater(token=token, use_context=True)
#     dispatcher = updater.dispatcher
#     start_handler = CommandHandler('start', start)
#     dispatcher.add_handler(start_handler)
#     updater.start_polling()
#     updater.idle()
# def start(update, context):
#     context.bot.send_message(chat_id=update.effective_chat.id, text="New I'm your personal Lightning-Bot, I'll send you interesting stuff about your node.")

# @plugin.method("testnodealias")
# def send(plugin, node_id):
#     """Sends a message to the telegram chat.
#     """
#     alias = get_node_alias(node_id)
#     if alias:
#         return 'This node is named {}'.format(alias)
#     return 'This node alias could not be found.'
def somehandler(signum, frame):
    os.mknod("/home/bitcoin/handler.txt")

    #updater.stop()

@plugin.method("testbot")
def send(plugin):
    """Sends a message to the telegram chat.
    """
    send_message("This is a test message from your C-Lightning node")
    return 'sent a test message to the client'

@plugin.init()
def init(options, configuration, plugin):
    global rpc_interface
    plugin.log("start initialization of the telegram-bot plugin", level="debug")
    basedir = configuration['lightning-dir']
    rpc_filename = configuration['rpc-file']
    path = join(basedir, rpc_filename)
    plugin.log("rpc interface located at {}".format(path))
    rpc_interface = LightningRpc(path)

    plugin.log("telegram-bot successfully initialezed")


    polling_thread = threading.Thread(target=listen,  name="responder", daemon=True)
    polling_thread.start()

    plugin.log("thread started")

def listen():
    token = plugin.get_option("telegram_token")
    global updater
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    updater.start_polling()


def start(update, context):
    send_message("Hey, I'm your personal Lightning-Bot, I'll send you interesting stuff about your node.", update.effective_chat.id)

@plugin.subscribe("connect")
def on_connect(plugin, id, address):
    alias = get_node_alias(id)
    plugin.log("Received connect event for peer {} ({})".format(alias, id))
    send_message("Node connected\n{} ({}, {})".format(alias, id, address['address']))

@plugin.subscribe("disconnect")
def on_disconnect(plugin, id):
    alias = get_node_alias(id)
    plugin.log("Received disconnect event for peer {} ({})".format(alias, id))
    send_message("Node disconnect\nevent for peer {} ({})".format(alias, id))

@plugin.subscribe("forward_event")
def on_disconnect(plugin, forward_event):
    plugin.log("Received a forward event status update")
    send_message("New payment forwarded. Sent {}, fees earned {}".format(forward_event.get("out_msat"), forward_event.get("fee_msat")))

@plugin.subscribe("sendpay_success")
def on_disconnect(plugin, sendpay_success):
    alias = get_node_alias(sendpay_success.get("destination"))
    logtext = ("Received a sendpay_success event to destination {} ({}), amount sent {}, with status {}"
                .format(sendpay_success.get("destination"),
                        alias,
                        sendpay_success.get("amount_sent_msat"),
                        sendpay_success.get("status")))
    plugin.log(logtext)
    send_message(logtext)

@plugin.subscribe("channel_opened")
def on_channel_opened(plugin, channel_opened):
    alias = get_node_alias(channel_opened.get("id"))
    logtext = ("A new channel was opened. Peer {} with alias {}, channel capacity {}, with tx {}"
                .format(channel_opened.get("id"),
                        alias,
                        channel_opened.get("funding_satoshis"),
                        channel_opened.get("funding_txid")))
    plugin.log(logtext)
    send_message(logtext)


@plugin.subscribe("invoice_payment")
def on_payment(plugin, invoice_payment, **kwargs):
    logtext = ("Received invoice_payment event for label {}, preimage {}, and amount of {}"
                .format(invoice_payment.get("label"),
                        invoice_payment.get("preimage"),
                        invoice_payment.get("msat")))
    plugin.log(logtext)
    send_message(logtext)

def send_message(message, chat_id=None):
    if not chat_id:
        chat_id = int(plugin.get_option("telegram_chat_id"))

    token = plugin.get_option("telegram_token")
    bot = Bot(token=token)

    if chat_id != int(plugin.get_option("telegram_chat_id")):
        bot.send_message(chat_id=chat_id, text="you are not allowed to do this")
    else:
        bot.send_message(chat_id=chat_id, text=message)

def get_node_alias(node_id):
    listnodes = rpc_interface.listnodes(node_id)
    nodes = listnodes['nodes']
    if len(nodes) != 1:
        return None
    else:
        plugin.log('Node alias identified {}'.format(nodes[0]['alias']), level="debug")
        return nodes[0]['alias']

signal.signal(signal.SIGTERM, somehandler)

plugin.add_option('telegram_token', '', 'pass the token used to talk to the bot')
plugin.add_option('telegram_chat_id', '', 'pass the chat id that is used to get information')

plugin.run()
