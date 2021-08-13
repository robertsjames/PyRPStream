"""
08/21, R James, F Alder

Adapted from script by https://github.com/awmlee
"""

import socket
import threading
import queue
import numpy as np
import time

import PyRPStream as rp
export, __all__ = fd.exporter()


class ClientCommand:
    """ A command to the client thread.
        Each command key has its associated command type:

        'CONNECT':    (host, port) tuple
        'RECEIVE':    None
        'CLOSE':      None
    """
    def __init__(self, key, command=None):
        self.key = key
        self.command = command



class ClientReply:
    """ A reply from the client thread.
        Each reply key has its associated reply type:

        'ERROR':      The error string
        'DATA':       Depends on the command - for RECEIVE it's the received
                      data string, for others None
        'MESSAGE':    Status message
    """
    def __init__(self, key, reply=None):
        self.key = key
        self.reply = reply



@export
class SocketClientThread(threading.Thread):
    """ Implements the threading (run, join, etc.): the thread can be
        controlled via the cmd_q queue attribute. Replies are placed in
        the reply_q queue attribute.
    """
    def __init__(self):
        super(SocketClientThread, self).__init__()

        # Command and reply queues for communicating with the socket thread
        self.cmd_q = queue.Queue()
        self.reply_q = queue.Queue()
        # Thread run control
        self.alive = threading.Event()
        self.alive.set()
        # Socket connection attributes
        self.connected = 0
        self.socket = None
        # Buffer reading attributes
        self.header_size = 60
        self.ch1_size = 32768
        self.ch2_size = 32768
        # Data storage
        self.data_all_ch1 = []
        self.data_all_ch2 = []
        # Thread control handlers
        self.handlers = {
            'CONNECT': self._handle_CONNECT,
            'RECEIVE': self._handle_RECEIVE,
            'CLOSE': self._handle_CLOSE
        }

        print('Starting socket thread')


    def run(self):
        """ Thread control function.
        """
        while self.alive.isSet():
            if self.connected:
                # Default is to RECEIVE
                command = ClientCommand('RECEIVE')
                self.handlers[command.key](command)
            else:
                # Don't do anything if not connected
                time.sleep(0.1)
            try:
                # Check if any commands have been sent to the thread
                command = self.cmd_q.get(block=False)
                self.handlers[command.key](command)
            except queue.Empty:
                # Do nothing if no commands sent
                continue


    def join(self, timeout=None):
        """ Invoking this will end the thread.
        """
        self.alive.clear()
        threading.Thread.join(self, timeout)


    def _handle_CONNECT(self, client_command):
        """ Attempt to connect to the socket, if not already connected
        client_command should be a (host, port) tuple.
        """
        try:
            if self.connected == 0:
                # Attempt to connect if not already connected
                self.socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((client_command.command[0], client_command.command[1]))
                self.reply_q.put(self._message_reply('Socket connected'))
                self.connected = 1
            else:
                # We are already connected, do nothing
                self.reply_q.put(self._message_reply('Socket already connected'))
        except OSError as e:
            # Return error if we can't connect
            self.reply_q.put(self._error_reply(str(e)))
            self.connected = 0


    def _handle_RECEIVE(self, client_command):
        """ Read from the socket: discard the header information, then send
        data from channel 1 and channel 2 to the reply queue.
        """
        try:
            reply = {}

            # Take the header information from the socket, then discard
            header_bytes = self._receieve_bytes(self.header_size, self.socket)

            # Take channel 1 data from the socket, store in reply
            ch1_bytes = self._receieve_bytes(self.ch1_size, self.socket)
            reply.update({'ch1_data': ch1_bytes})

            # Take channel 2 data from the socket, store in reply
            ch2_bytes = self._receieve_bytes(self.ch2_size, self.socket)
            reply.update({'ch2_data': ch2_bytes})

            # Store the timestamp in reply
            reply.update({'timestamp': time.time()})

            # Put reply in the reply queue
            self.reply_q.put(self._data_reply(reply), block=True)

        except OSError as e:
            self.reply_q.put(self._error_reply(str(e)))
            self.connected = 0


    def _receieve_bytes(self, n, socket):
        """ Receive n bytes from socket.
        """
        tdata = bytearray()
        while len(tdata) < n:
            packet = socket.recv(n - len(tdata))
            if not packet:
                raise OSError('Empty packet from socket.recv()')
            tdata.extend(packet)

        return tdata


    def _handle_CLOSE(self, client_command):
        """ Close connection to the socket.
        """
        self.socket.close()
        self.reply_q.queue.clear()
        self.reply_q.put(self._message_reply('Socket closed'))
        self.connected = 0


    def _error_reply(self, errstr):
        return ClientReply('ERROR', errstr)


    def _message_reply(self, data=None):
        return ClientReply('MESSAGE', data)


    def _data_reply(self, data=None):
        return ClientReply('DATA', data)
