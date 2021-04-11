#/usr/bin/python3

import requests, fileinput, psutil, os, json

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
    try:
        resp = requests.get(turl + '/getUpdates?timeout=' + 
                            str(CHECK_INTERVAL)).json()
    except json.decoder.JSONDecodeError:
        return status
    if resp['ok'] and resp['result']:
        for update in resp['result']:
            try:
                if 'status' in update['message']['text'].lower():
                    status = True
                    next_up = str(update['update_id'] + 1)
                    # Mark this update as processed, so it won't appear again
                    requests.get(turl + '/getUpdates?offset=' + next_up)
            except KeyError:
                pass
    return status
            
def get_nodes():
    nodes = []
    try:
        resp = requests.get(purl).json()
    except json.decoder.JSONDecodeError:
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
        chat = requests.get(turl + '/getChat?chat_id=' + str(TELEGRAM_CHAT_ID)).json()
        msg_id = chat['result']['pinned_message']['message_id']
        text = chat['result']['pinned_message']['text']
    except (KeyError, json.decoder.JSONDecodeError):
        msg_id = None
        text = ''
    return msg_id, text

def pin(message):
    try:
        msg_id = message['result']['message_id']
        requests.get(turl + '/pinChatMessage?chat_id={}&message_id={}&disable_notification=True'.format(TELEGRAM_CHAT_ID, msg_id))
    except KeyError:
        pass

def unpin_all():
    requests.get(turl + '/unpinAllChatMessages?chat_id=' + TELEGRAM_CHAT_ID)


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
        requests.get(turl + '/editMessageText?chat_id={}&message_id={}&text={}'.format(TELEGRAM_CHAT_ID, pin_id, pin_text))
    if not one_disconnected:
        requests.get(turl + '/unpinAllChatMessages?chat_id=' + TELEGRAM_CHAT_ID)

def send_status(nodes):
    if nodes:
        message = 'Current Node Status\n---------------------\n'
        for name, connected, minutes, url in nodes:
            if connected:
                message += '{} is connected\n'.format(name)
            else:
                message += '{} is disconnected\n'.format(name)
                if url:
                    message += url + '\n'

        print(message)
        try:
            resp = requests.get(turl + '/sendMessage?chat_id={}&text={}'.format(TELEGRAM_CHAT_ID, message)).json()
            return resp
        except json.decoder.JSONDecodeError:
            return None

def send_alert(nodes):
    message = ''
    for node in nodes:
        message += node[0] + ' is disconnected\n'
        if node[3]:
            message += node[3] + '\n'
    
    if message:
        try:
            resp = requests.get(turl + '/sendMessage?chat_id={}&text={}'.format(TELEGRAM_CHAT_ID, message)).json()
            unpin_all()
            pin(resp)
        except json.decoder.JSONDecodeError:
            pass



if not TELEGRAM_CHAT_ID:
    try:
        resp = requests.get(turl + '/getUpdates').json()
    except json.decoder.JSONDecodeError:
        print('Unexpected reply from Telegram, please try again.')
        raise SystemExit

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

                requests.get(turl+ 'setMyCommands?commands=[{"command": "status", "description": "Get the status of nodes"}]')
                print('Set to chat with @{}\n'.format(username))

                nodes = get_nodes()
                if nodes:
                    message = "Hey there! Here is the current status of your Presearch nodes. Message me the word 'status' or use the /status command to check on your nodes at any time"
                else:
                    message = "Hey there! I wasn't able to find any nodes under the provided Presearch node API key. Please double check your API key and wait a few minutes. Then message me the word 'status' or use the /status command to try again"
                requests.get(turl + '/sendMessage?chat_id={}&text={}'.format(str(TELEGRAM_CHAT_ID), message))

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
while 1:
    try:
        if check_status_request():
            nodes = get_nodes()
            status_message = send_status(nodes)
            disconnected_nodes = check_alert(nodes)
            if disconnected_nodes:
                unpin_all()
                pin(status_message)
        
        send_alert(check_alert(get_nodes()))

    except KeyboardInterrupt:
        raise SystemExit
