"""
02/22, R James, F Alder

Adapted from script by https://github.com/awmlee
"""
from websocket import create_connection
import requests
import json
import keyboard


class Websocket:
    def __init__(self, socket_url=None):
        self.rp_ip = 'rp-f05a98.local' if socket_url == '' else socket_url
        self.socket_url = 'ws://' + self.rp_ip + '/wss'
        self.start_app_url = 'http://' + self.rp_ip + '/bazaar?start=streaming_manager'



#------------------------------------------------------------------------------
socket_url = input('Red Pitaya IP address (press enter for default: rp-f05a98.local):')
WS = Websocket(socket_url)

# Start streaming server
try:
    web = requests.get(WS.start_app_url)
    print('Connection established')
except:
    raise OSError('Could not connect to Red Pitaya')

# Create websocket connection
ws = create_connection(WS.socket_url)

# Set websocket parameters
setbits = ({'parameters': {'SS_RESOLUTION': {'value': 2}, 'in_command': {'value': 'send_all_params'}}})
setrate = ({'parameters': {'SS_RATE': {'value': 120}, 'in_command': {'value': 'send_all_params'}}})
setdualchan = ({'parameters': {'SS_CHANNEL': {'value': 3},' in_command': {'value': 'send_all_params'}}})
ws.send(json.dumps(setbits))
ws.send(json.dumps(setrate))
ws.send(json.dumps(setdualchan))

startcmd = ({'parameters': {'SS_START': {'value': 1}, 'in_command': {'value': 'send_all_params'}}})
stopcmd = ({'parameters': {'SS_START': {'value': 0}, 'in_command': {'value': 'send_all_params'}}})

# Start streaming data
ws.send(json.dumps(startcmd))

print('Streaming: press q to stop')
while True:
    if keyboard.read_key() == 'q':
        print('Ending streaming, closing connection')
        break

# Stop streaming data and close websocket
ws.send(json.dumps(stopcmd))
ws.close()
