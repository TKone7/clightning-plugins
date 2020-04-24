#!/usr/bin/env python3

import json
from os.path import join

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


@plugin.method("testbot")
def send(plugin):
    """Sends a message to the telegram chat.
    """
    send_message("This is a test message from your C-Lightning node")
    return 'sent a test message client'

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

@plugin.subscribe("connect")
def on_connect(plugin, id, address):
    plugin.log("Received connect event for peer {}".format(id))
    send_message("Received connect event for peer {} and address {}".format(id, address))

@plugin.subscribe("disconnect")
def on_disconnect(plugin, id):
    plugin.log("Received disconnect event for peer {}".format(id))
    send_message("Received disconnect event for peer {}".format(id))

@plugin.subscribe("forward_event")
def on_disconnect(plugin, forward_event):
    plugin.log("Received a forward event status update")
    send_message("New payment forwarded. Sent {}, fees earned {}".format(forward_event.get("out_msat"), forward_event.get("fee_msat")))

@plugin.subscribe("sendpay_success")
def on_disconnect(plugin, sendpay_success):
    logtext = ("Received a sendpay_success event to destination {}, amount sent {}, with status {}"
                .format(sendpay_success.get("destination"),
                        sendpay_success.get("amount_sent_msat"),
                        sendpay_success.get("status")))
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

def send_message(message):
    token = plugin.get_option("telegram_token")
    chat_id = plugin.get_option("telegram_chat_id")
    bot = Bot(token=token)
    bot.send_message(chat_id=chat_id, text=message)

plugin.add_option('telegram_token', '', 'pass the token used to talk to the bot')
plugin.add_option('telegram_chat_id', '', 'pass the chat id that is used to get information')

plugin.run()
