#/usr/bin/python3

import requests, fileinput, psutil, os, json, time

PRESEARCH_NODE_KEY = ''
TELEGRAM_BOT_TOKEN = ''

ALERT_DELAY = 3 #How long in minutes a node is offline before alert is sent
CHECK_INTERVAL = 60 #How long in seconds to wait between node checks

# Don't worry about this, we'll fill it in for you
TELEGRAM_CHAT_ID = ''

turl = 'https://api.telegram.org/bot' + TELEGRAM_BOT_TOKEN
purl = 'https://nodes.presearch.org/api/nodes/status/' + PRESEARCH_NODE_KEY


def check_alert(nodes):
    pin_id, pin_text = get_pinned_message()
    disconnected_nodes = []
    alert = False
    for node in nodes:
        if node[1] == False:
            disconnected_nodes.append(node)
            if node[2] >= ALERT_DELAY and node[0] + ' is disconnected' not in pin_text:
                alert = True

    if alert:
        return disconnected_nodes
    elif pin_text:
        update_pinned_message(nodes, pin_id, pin_text)
        
    return []

def check_status_request():
    status = False
    resp = send_request(turl + '/getUpdates', timeout=str(CHECK_INTERVAL))

    if resp['ok'] and resp['result']:
        for update in resp['result']:
            try:
                if 'status' in update['message']['text'].lower():
                    status = True
                    next_up = str(update['update_id'] + 1)
                    # Mark this update as processed, so it won't appear again
                    send_request(turl + '/getUpdates', offset=next_up)
            except KeyError:
                pass
    return status
            
def get_nodes():
    nodes = []
    resp = send_request(purl)

    if resp == None:
        print('Error connecting to Presearch API')
        return nodes

    if resp['success'] is True:
        for node in resp['nodes'].items():
            key = node[0]
            description = node[1]['meta']['description']
            url = node[1]['meta']['url']
            connected = node[1]['status']['connected']
            minutes = node[1]['status']['minutes_in_current_state']

            if description:
                name = description
            else:
                name = key[:60]

            nodes.append([name, connected, minutes, url])

    return nodes

def get_pinned_message():
    try:
        chat = send_request(turl + '/getChat', chat_id=TELEGRAM_CHAT_ID)
        msg_id = chat['result']['pinned_message']['message_id']
        text = chat['result']['pinned_message']['text']
    except KeyError:
        msg_id = None
        text = ''
    return msg_id, text

def pin(message):
    try:
        msg_id = message['result']['message_id']
        send_request(turl + '/pinChatMessage', chat_id=TELEGRAM_CHAT_ID, message_id=msg_id)
    except KeyError:
        print('Tried to pin a malformed message')

def unpin_all():
    send_request(turl + '/unpinAllChatMessages', chat_id=TELEGRAM_CHAT_ID)

def update_pinned_message(nodes, pin_id, pin_text):
    one_disconnected = False
    text_changed = False
    for node in nodes:
        if node[1] == True and node[0] + ' is disconnected' in pin_text:
            pin_text = pin_text.replace(node[0] + ' is disconnected', node[0] + ' was disconnected')
            text_changed = True
        elif node[1] == False:
            one_disconnected = True

    if text_changed:
        send_request(turl + '/editMessageText', chat_id=TELEGRAM_CHAT_ID, message_id=pin_id, text=pin_text)

    if not one_disconnected:
        unpin_all()

def send_status(nodes):
    if nodes:
        message = 'Current Node Status:\n\n'

        for name, connected, minutes, url in nodes:
            if connected:
                message += '{} is connected\n'.format(name)
            else:
                message += '{} is disconnected\n'.format(name)
                if url:
                    message += url + '\n'

        print(message)
        resp = send_request(turl + '/sendMessage', chat_id=TELEGRAM_CHAT_ID, text=message)
        return resp


def send_alert(nodes):
    message = ''
    for node in nodes:
        message += node[0] + ' is disconnected\n'
        if node[3]:
            message += node[3] + '\n'
    
    if message:
        resp = send_request(turl + '/sendMessage', chat_id=TELEGRAM_CHAT_ID, text=message)
        unpin_all()
        pin(resp)

def send_request(url, timeout=5, **kwds):
    try:
        resp = requests.get(url, timeout=int(timeout), params=kwds).json()
        return resp
    except (requests.exceptions.Timeout, json.decoder.JSONDecodeError, ConnectionError) as e:
        print(e)
        return None

if not TELEGRAM_CHAT_ID:
    resp = send_request(turl + '/getUpdates')

    if resp['ok']:
        got_message = False
        for update in resp['result']:
            if 'message' in update:
                got_message = True
                chat = update['message']['chat']
                chat_id = chat['id']
                username = chat['username']

                TELEGRAM_CHAT_ID = chat_id

                with fileinput.input(__file__, inplace=True) as file:
                    for line in file:
                        if line[:16] == 'TELEGRAM_CHAT_ID':
                            print("TELEGRAM_CHAT_ID = '{}'".format(chat_id))
                        else:
                            print(line, end='')

                send_request(turl + '/setMyCommands', message_id=msg_id, commands='[{"command": "status", "description": "Get the status of nodes"}]')

                print('Set to chat with @{}\n'.format(username))

                nodes = get_nodes()
                if nodes:
                    message = "Hey there! Here is the current status of your Presearch nodes. Message me the word 'status' or use the /status command to check on your nodes at any time"
                else:
                    message = "Hey there! I wasn't able to find any nodes under the provided Presearch node API key. Please double check your API key and wait a few minutes. Then message me the word 'status' or use the /status command to try again"

                send_request(turl + '/sendMessage', chat_id=TELEGRAM_CHAT_ID, text=message)

                send_status(nodes)

        if not got_message:
            print('No incoming messages. Did you say hi to your bot?')
            raise SystemExit

    else:
        print('Error reaching Telegram bot. Please verify your bot token.')
        raise SystemExit

try:
    send_alert(check_alert(get_nodes()))
except KeyboardInterrupt:
    raise SystemExit


# If another process is already running, kill it
for process in psutil.process_iter():
    try:
        for part in process.cmdline():
            if part == 'bash' or part == 'sh':
                break
            if __file__.rsplit('/', 1)[-1] in part and os.getpid() != process.pid:
                process.kill()
    except IndexError:
        pass

print('Listening for status requests...')
last_node_check = 0
while 1:
    try:
        if check_status_request():
            nodes = get_nodes()
            status_message = send_status(nodes)
            disconnected_nodes = check_alert(nodes)
            if disconnected_nodes:
                unpin_all()
                pin(status_message)
        
        # A safeguard, so we're not relying solely on a long poll timeout from Telegram to avoid spamming the Presearch API and potentially hitting rate limits
        if last_node_check + CHECK_INTERVAL < time.time():
            send_alert(check_alert(get_nodes()))
            last_node_check = time.time()
        else:
            pass

    except KeyboardInterrupt:
        raise SystemExit
