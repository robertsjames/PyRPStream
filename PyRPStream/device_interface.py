"""
08/21, R James, F Alder

Adapted from script by https://github.com/awmlee
"""

import numpy as np
import time
import os

import PyRPStream as rp
export, __all__ = rp.exporter()


@export
class RPDevice:
    """
    """
    def __init__(self, name):
        # Device name
        self.name = name
        # Calibration parameters
        if os.path.isfile(self.name + '_calib.txt'):
            file = open(self.name + '_calib.txt', 'r')
            calib_consts = file.readlines()
            self.ch1_offset = float(calib_consts[0])
            self.ch1_gain = float(calib_consts[1])
            self.ch2_offset = float(calib_consts[2])
            self.ch2_gain = float(calib_consts[3])
        else:
            self.ch1_offset = 0.
            self.ch1_gain = 1.
            self.ch2_offset = 0.
            self.ch2_gain = 1.
        # Connection information
        self.address_port = ('rp-f05a98.local', 8900)
        # Device information
        self.input_range_V = 2.
        self.input_bits = 16
        # Socket thread
        self.client = rp.SocketClientThread()
        # Start the socket thread
        self.client.start()


    def connect(self):
        """
        """
        if not self.client.alive.isSet():
            # Create new socket thread
            self.client = rp.SocketClientThread()
            # Start the socket thread
            self.client.start()

        print('Trying to CONNECT to socket')
        # Make 10 attempts, then give up
        for i in range(10):
            self.client.cmd_q.put(rp.ClientCommand('CONNECT', self.address_port))
            client_reply = self.client.reply_q.get()

            if client_reply.key == 'ERROR':
                print(client_reply.reply)
                print('Trying to CONNECT again')
            elif client_reply.key == 'MESSAGE':
                print(client_reply.reply)
                break
            else:
                break

        # Check if we are connected by attempting to RECEIVE
        self.client.cmd_q.put(rp.ClientCommand('RECEIVE'))
        client_reply = self.client.reply_q.get()
        if client_reply.key == 'ERROR':
            # We aren't connected: end the thread
            print(client_reply.reply)
            self.client.join()
            raise OSError('Repeatedly failed to execute CONNECT: exiting')

        time.sleep(1)


    def disconnect(self):
        """
        """
        print('Trying to CLOSE socket connection')

        if not self.client.alive.isSet():
            # There is no thread
            return

        if not self.client.connected:
            # We aren't connected: end the thread
            self.client.join()
            return

        self.client.cmd_q.put(rp.ClientCommand('CLOSE'))

        time.sleep(1)

        # Get reply upon socket closure
        client_reply = self.client.reply_q.get()
        print(client_reply.reply)

        # End the thread
        self.client.join()


    def acquire(self, acq_time, file_size=250e6):
        """
        """
        if not self.client.alive.isSet():
            # There is no thread
            raise OSError('Cannot acquire when not connected to device')

        if not self.client.connected:
            # We aren't connected: end the thread
            self.client.join()
            raise OSError('Cannot acquire when not connected to device')

        try:
            assert(acq_time > 0)
        except:
            raise TypeError('Invalid acquisition time value')

        # Number of messages to use for data rate calculation
        n_samp = 10

        # Get reply from reply queue to obtain start time
        client_reply = self.client.reply_q.get()

        if client_reply.key == 'ERROR':
            # End the thread if we receive ERROR
            print(client_reply.reply)
            self.client.join()
            raise OSError('Error during RECEIVE: exiting')

        elif client_reply.key == 'DATA':
            # If we have DATA, get the start acquisition time
            t_start = client_reply.reply['timestamp']

        t_prev = t_start
        i = 0

        ch1_data = bytearray()
        ch2_data = bytearray()
        ch1_reads = 0
        ch2_reads = 0
        t_file_ch1 = None
        t_file_ch2 = None

        # Loop to RECEIVE DATA, unless an ERROR occurs
        while True:
            # Get reply from reply queue
            client_reply = self.client.reply_q.get()

            if client_reply.key == 'ERROR':
                # End the thread if we receive ERROR
                print(client_reply.reply)
                self.client.join()
                raise OSError('Error during RECEIVE: exiting')

            elif client_reply.key == 'DATA':
                # If we have DATA, exit if we have exceeded acquisition time
                t = client_reply.reply['timestamp']
                if t - t_start > acq_time:
                    data_decoded = np.frombuffer(ch1_data, dtype=np.int16)
                    data_calib = np.float32(self.ch1_gain * (data_decoded  * self.input_range_V / 2 ** self.input_bits + self.ch1_offset))
                    data_calib.tofile(f'red_pitaya_data_ch1_{t_file_ch1}.bin')

                    data_decoded = np.frombuffer(ch2_data, dtype=np.int16)
                    data_calib = np.float32(self.ch2_gain * (data_decoded  * self.input_range_V / 2 ** self.input_bits + self.ch2_offset))
                    data_calib.tofile(f'red_pitaya_data_ch2_{t_file_ch2}.bin')

                    break

                # Otherwise,
                if ch1_reads == 0:
                    t_file_ch1 = t
                if ch2_reads == 0:
                    t_file_ch2 = t

                ch1_data += client_reply.reply['ch1_data']
                ch2_data += client_reply.reply['ch2_data']
                ch1_reads += 1
                ch2_reads += 1

                if (ch1_reads * self.client.ch1_size * (32 / 16) > file_size):
                    data_decoded = np.frombuffer(ch1_data, dtype=np.int16)
                    data_calib = np.float32(self.ch1_gain * (data_decoded  * self.input_range_V / 2 ** self.input_bits + self.ch1_offset))
                    data_calib.tofile(f'red_pitaya_data_ch1_{t_file_ch1}.bin')
                    ch1_data = bytearray()
                    ch1_reads = 0
                if (ch2_reads * self.client.ch2_size * (32 / 16) > file_size):
                    data_decoded = np.frombuffer(ch2_data, dtype=np.int16)
                    data_calib = np.float32(self.ch2_gain * (data_decoded  * self.input_range_V / 2 ** self.input_bits + self.ch2_offset))
                    data_calib.tofile(f'red_pitaya_data_ch2_{t_file_ch2}.bin')
                    ch2_data = bytearray()
                    ch2_reads = 0

                # Calculate the data rate every n_samp messages
                if i == n_samp:
                    print('Data rate is ', n_samp * 2**16 / (t - t_prev) / 1024 / 1024)  # MBytes/second
                    i = 0
                    t_prev = t

                i += 1


    def acquire_calib(self, acquire_raw=False):
        """
        """
        if not self.client.alive.isSet():
            # There is no thread
            raise OSError('Cannot calibrate when not connected to device')

        if not self.client.connected:
            # We aren't connected: end the thread
            self.client.join()
            raise OSError('Cannot calibrate when not connected to device')

        # Get reply from reply queue to obtain start time
        client_reply = self.client.reply_q.get()

        if client_reply.key == 'ERROR':
            # End the thread if we receive ERROR
            print(client_reply.reply)
            self.client.join()
            raise OSError('Error during RECEIVE: exiting')

        elif client_reply.key == 'DATA':
            # If we have DATA, get the start acquisition time
            t_start = client_reply.reply['timestamp']

        ch1_data_store = []
        ch2_data_store = []

        # Loop to RECEIVE DATA, unless an ERROR occurs
        while True:
            # Get reply from reply queue
            client_reply = self.client.reply_q.get()

            if client_reply.key == 'ERROR':
                # End the thread if we receive ERROR
                print(client_reply.reply)
                self.client.join()
                raise OSError('Error during RECEIVE: exiting')

            elif client_reply.key == 'DATA':
                # If we have DATA, exit if we have exceeded acquisition time
                t = client_reply.reply['timestamp']
                if t - t_start > 1: # Acquire for 1 second
                    break

                # Otherwise, append data
                ch1_data = np.frombuffer(client_reply.reply['ch1_data'], dtype=np.int16)
                ch2_data= np.frombuffer(client_reply.reply['ch2_data'], dtype=np.int16)

                if not acquire_raw:
                # Convert from ADC -> V, with calibration factors, by default
                    ch1_data = self.ch1_gain * (ch1_data * self.input_range_V / 2. ** self.input_bits + self.ch1_offset)
                    ch2_data = self.ch2_gain * (ch2_data * self.input_range_V / 2. ** self.input_bits + self.ch2_offset)

                ch1_data_store = np.append(ch1_data_store, ch1_data)
                ch2_data_store = np.append(ch2_data_store, ch2_data)

        # Save calibration data to files
        np.savetxt('red_pitaya_data_ch1_calib.txt', ch1_data_store)
        np.savetxt('red_pitaya_data_ch2_calib.txt', ch2_data_store)
