# Presearch Node Status Telegram Bot

This is a small program that drives a Telegram bot to provide status information and alerts for Presearch nodes. It is intended to be run as a cron job or service on a machine with high uptime.

**Features:**
* Send a /status command to the bot, and it will reply with a list of your nodes and whether the are connected or disconnected
* When a node is disconnected for a chosen number of minutes, the bot will alert you with a message (just a single message for now)
* Displays the node's description, if it has one, or the beginning of it's public key otherwise. When nodes are disconnected, their url is included if they have one

*Please note:* this is a first draft, and it shouldn't be exclusively relied on for checking up on your Presearch nodes. Not yet anyway :)

## Install

You'll need `python3` and I've only tested on Linux. Mac might work and some parts definitely won't work on Windows. Please open an issue or drop me a line if you have experience with or interest in other platforms.

The code was written in python 3.9.2, and relies on the `requests` and `psutils` libraries. On older versions of Python 3, you may need to install these manually with `pip3`:

`pip3 install requests psutil`

Then grab the source from Github:

```
wget https://github.com/scottyeager/presearch-node-status-bot/archive/refs/heads/main.zip
unzip main.zip
```

or

`git clone https://github.com/scottyeager/presearch-node-status-bot.git`


## Setup

To do it's job, the program needs a Telegram bot token and a Presearch node API key. Insert these directly into `pnsb.py` before you run it for the first time.

Get your Telegram bot, by visiting the [BotFather](https://t.me/botfather). Just pick a name and you're done. Do note that BotFather asks for two names, with the second being the display name. Look for the bot's token upon completion, and consider storing it somewhere safe like a password manager.

To find your Presearch node API key, visit the [node dashboard](https://nodes.presearch.org/node), click the 'Stats' button for any node, and scroll to the bottom of the page.

Edit your copy of `pnsb.py`, inserting your Presearch node API key and your Telegram bot token on the appropriate lines between the quote marks.

### First run

Before the first run, it's necessary to say 'hi' to your bot. By sending a message to your bot, you give it permission to message you back. This also determines who your bot sends alerts to. Send any message to your bot then run:

`python3 pnsb.py`

If everything works right, it should print your Telegram username and the status of your nodes. In the background, the script has also saved a Telegram chat id associated with your conversation.

The first status report from your bot should also arrive soon. If it doesn't or you want to play around, leave the program running and try messaging your bot with the word 'status' or the `/status` command. Hit `ctl-c` when you're ready to move on.

## Autostart

When the program starts, it looks for other instances that are already running and sends a kill signal to them. This means that you can run it periodically as a cron job to get a fresh start every so often in case it dies or hangs.

For example, run `crontab -e` and insert a line like this to run once every five minutes:

`*/5 * * * * python3 /path/to/pnsb.py`

Some crons won't actually start a new process if it's still running, and you might prefer another option like creating a system service or using kind of autostart mechanism. This should all work fine, as the program will continue periodically checking if an alert is needed. However, there may well be bugs that prevent alerts from being sent without causing an exit, so restarting occasionally may be advisable.

## Config

There are two parameters you can set by editing them in the Python file:

* `ALERT_DELAY` specifies how many minutes a node is offline before you are alerted and is set to 3 minutes by default
* `CHECK_INTERVAL` is how many seconds to wait between queries of the Presearch node API and is set to 60 seconds by default

## What's Up with the Pinned Messages?
Pinning messages is a way to tell which alerts have already been messaged out. The program itself stores no state beside API secrets and Telegram only allows historical access to pinned messages. The bot pins an alert, then modifies or unpins it as things change.

The Telegram bot API indicated that no notifications should be sent while pinning messages in private chats. I've even enabled an option to disable the notification in cases where it would normally appear, and I still get pinned message notifications in the Telegram app. Getting a double buzz for an alert might be a bit annoying, but it's essential to keep from blowing up with alerts on the same disconnected node constantly.

## Et Cetera

Please contact me with any questions, concerns, comments, etc. on Telegram: @scottyeager. If you find a bug, let me know or an open an issue on Github.

This project was developed in the "hackathon" spirit to rapidly deliver a minimal working feature set. Additional commands, communication protocols, and other features are not planned at this time. Feel free to fork the repo and continue development, or let me know if there's something you'd really like to see.

Thanks for reading. I hope you find this bot useful!
