"""
02/22, R James
"""

import numpy as np
import time
import os

import PyRPStream as rp
export, __all__ = rp.exporter()


class RPDevice:
    """
    """
    def __init__(self, name, address, port):
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
        self.address_port = (address, port)
        # Device information
        self.input_range_V = 2.
        self.input_bits = 16


@export
class RPDeviceCollection:
    """
    """
    def __init__(self):
        # Device collection
        self.device_collection = []
        self.device_names = []
        # Socket thread
        self.client = rp.SocketClientThread([])
        # Start the socket thread
        self.client.start()


    def add_device(self, device_name, device_address, device_port):
        try:
            assert isinstance(device_name, str)
        except:
            raise ValueError('device_name must be string')

        try:
            assert isinstance(device_address, str)
        except:
            raise ValueError('device_address must be string')

        try:
            assert isinstance(device_port, int)
        except:
            raise ValueError('device_port must be int')

        # Add new device to device collection
        self.device_collection.append(RPDevice(device_name, device_address, device_port))
        self.device_names.append(device_name)


    def initialise(self):
        if self.client.alive.isSet():
            # End the old thread if there is one
            self.client.join()

        # Socket thread
        self.client = rp.SocketClientThread(self.device_names)
        # Start the socket thread
        self.client.start()


    def connect(self):
        """
        """
        if not self.client.alive.isSet():
            # Create new socket thread
            self.client = rp.SocketClientThread(self.device_names)
            # Start the socket thread
            self.client.start()

        print('Trying to CONNECT to sockets')
        # Make 10 attempts, then give up
        for i in range(10):
            self.client.cmd_q.put(rp.ClientCommand('CONNECT', [device.address_port for device in self.device_collection]))
            client_replies = [self.client.reply_q.get() for device in self.device_collection]

            for client_reply in client_replies:
                print(client_reply.reply)

            if any(client_reply.key == 'ERROR' for client_reply in client_replies):
                print('Trying to CONNECT again')
            elif all(client_reply.key == 'MESSAGE' for client_reply in client_replies):
                break
            else:
                # Don't know how to handle this: disconnect from all connected sockets, end the thread
                self.disconnect()
                raise OSError('Unknown error when attempting to CONENCT: exiting')

        # # Check if we are connected by attempting to RECEIVE
        # self.client.cmd_q.put(rp.ClientCommand('RECEIVE'))
        # client_replies = [self.client.reply_q.get() for _ in self.device_collection]
        # if any(client_reply.key == 'ERROR' for client_reply in client_replies):
        #     # We aren't connected to at least one device: disconnect from all connected sockets, end the thread
        #     for client_reply in client_replies:
        #         if client_reply.key == 'ERROR':
        #             print(client_reply.reply)
        #     self.disconnect()
        #     raise OSError('Repeatedly failed to execute CONNECT: exiting')
        #
        # time.sleep(1)


    def disconnect(self):
        """
        """
        print('Trying to CLOSE socket connection')

        if not self.client.alive.isSet():
            # There is no thread
            return

        if all(connected == False for connected in self.client.connected):
            # We aren't connected to any devices: end the thread
            self.client.join()
            return

        self.client.cmd_q.put(rp.ClientCommand('CLOSE'))

        time.sleep(1)

        # Get reply upon socket closure
        client_reply = self.client.reply_q.get()
        print(client_reply.reply)

        # End the thread
        self.client.join()


    def acquire(self, acq_time_s, file_size=250e6, acquire_raw=False):
        """
        """
        if not self.client.alive.isSet():
            # There is no thread
            raise OSError('Cannot acquire when not connected to any devices')

        if any(connected == False for connected in self.client.connected):
            # We aren't connected to at least one device: disconnect from all connected sockets, end the thread
            self.disconnect()
            raise OSError('Cannot aquire unless connected to all devices: exiting')

        try:
            assert(acq_time_s > 0)
        except:
            raise TypeError('Invalid acquisition time value')

        # Number of messages to use for data rate calculation
        n_samp = 10

        # Get reply from reply queue to obtain start time
        client_reply = self.client.reply_q.get()

        if client_reply.key == 'ERROR':
            # Disconnect from all connected sockets, end the thread if we receive ERROR
            print(client_reply.reply)
            self.disconnect()
            raise OSError('Error during RECEIVE: exiting')

        # elif client_reply.key == 'DATA':
        #     # If we have DATA, get the start acquisition time
        #     t_start_ns = client_reply.reply['timestamp']

        # t_prev_ns = t_start_ns
        # i = 0

        # ch1_data = bytearray()
        # ch2_data = bytearray()
        # ch1_reads = 0
        # ch2_reads = 0
        # t_file_ch1 = None
        # t_file_ch2 = None

        device1_data = bytearray()
        device1_reads = 0
        device2_data = bytearray()
        device2_reads = 0

        # Loop to RECEIVE DATA, unless an ERROR occurs
        while True:
            # Get reply from reply queue
            client_reply = self.client.reply_q.get()

            # if client_reply.key == 'ERROR':
            #     # End the thread if we receive ERROR
            #     print(client_reply.reply)
            #     self.client.join()
            #     raise OSError('Error during RECEIVE: exiting')
            #
            # elif client_reply.key == 'DATA':
            #     # If we have DATA, exit if we have exceeded acquisition time
            #     t_ns = client_reply.reply['timestamp']
            #     if t_ns - t_start_ns > (acq_time_s * 1e9):
            #         self.save_data(ch1_data, channel=1, acquire_raw=acquire_raw, t_file=t_file_ch1_ns)
            #         self.save_data(ch2_data, channel=2, acquire_raw=acquire_raw, t_file=t_file_ch2_ns)
            #         break

                # # Otherwise,
                # if ch1_reads == 0:
                #     t_file_ch1_ns = t_ns
                # if ch2_reads == 0:
                #     t_file_ch2_ns = t_ns

                # ch1_data += client_reply.reply['ch1_data']
                # ch2_data += client_reply.reply['ch2_data']
                # ch1_reads += 1
                # ch2_reads += 1

            if 'og_rp' in client_reply.reply:
                device1_data += client_reply.reply['og_rp']
                device1_reads += 1
            if 'ln_rp' in client_reply.reply:
                device2_data += client_reply.reply['ln_rp']
                device2_reads += 1

            if (device1_reads * self.client.ch1_size > 1e6):
                self.save_data(device1_data, channel=1, acquire_raw=acquire_raw, t_file='og_rp', device=self.device_collection[0])
                self.save_data(device2_data, channel=1, acquire_raw=acquire_raw, t_file='ln_rp', device=self.device_collection[1])
                break

                # if (ch1_reads * self.client.ch1_size > file_size):
                #     self.save_data(ch1_data, channel=1, acquire_raw=acquire_raw, t_file=t_file_ch1_ns)
                #     ch1_data = bytearray()
                #     ch1_reads = 0
                # if (ch2_reads * self.client.ch2_size > file_size):
                #     self.save_data(ch2_data, channel=2, acquire_raw=acquire_raw, t_file=t_file_ch2_ns)
                #     ch2_data = bytearray()
                #     ch2_reads = 0
        #
        #         # Calculate the data rate every n_samp messages
        #         if i == n_samp:
        #             print('Data rate is ', n_samp * 2**16 / (t_ns - t_prev_ns) / 1024 / 1024 * 1e9)  # MBytes/second
        #             i = 0
        #             t_prev_ns = t_ns
        #
        #         i += 1


    # def acquire_calib(self, acquire_raw=False):
    #     """
    #     """
    #     if not self.client.alive.isSet():
    #         # There is no thread
    #         raise OSError('Cannot calibrate when not connected to device')
    #
    #     if not self.client.connected:
    #         # We aren't connected: end the thread
    #         self.client.join()
    #         raise OSError('Cannot calibrate when not connected to device')
    #
    #     # Get reply from reply queue to obtain start time
    #     client_reply = self.client.reply_q.get()
    #
    #     if client_reply.key == 'ERROR':
    #         # End the thread if we receive ERROR
    #         print(client_reply.reply)
    #         self.client.join()
    #         raise OSError('Error during RECEIVE: exiting')
    #
    #     elif client_reply.key == 'DATA':
    #         # If we have DATA, get the start acquisition time
    #         t_start_ns = client_reply.reply['timestamp']
    #
    #     ch1_data = bytearray()
    #     ch2_data = bytearray()
    #
    #     # Loop to RECEIVE DATA, unless an ERROR occurs
    #     while True:
    #         # Get reply from reply queue
    #         client_reply = self.client.reply_q.get()
    #
    #         if client_reply.key == 'ERROR':
    #             # End the thread if we receive ERROR
    #             print(client_reply.reply)
    #             self.client.join()
    #             raise OSError('Error during RECEIVE: exiting')
    #
    #         elif client_reply.key == 'DATA':
    #             # If we have DATA, exit if we have exceeded acquisition time
    #             t_ns = client_reply.reply['timestamp']
    #             if t_ns - t_start_ns > 1e9: # Acquire for 1 second
    #                 break
    #
    #             # Otherwise, append data
    #             ch1_data += client_reply.reply['ch1_data']
    #             ch2_data += client_reply.reply['ch2_data']
    #
    #     self.save_data(ch1_data, channel=1, calib=True, acquire_raw=acquire_raw)
    #     self.save_data(ch2_data, channel=2, calib=True, acquire_raw=acquire_raw)
    #
    #
    def save_data(self, data_bytes, channel=1, calib=False, acquire_raw=False, t_file=None, device=None):
        """
        """
        try:
            assert(device is not None)
        except:
            raise ValueError('Must specify device')

        try:
            assert((channel == 1) or (channel == 2))
        except:
            raise ValueError('channel must be 1 or 2')

        data = np.frombuffer(data_bytes, dtype=np.int16)

        if not acquire_raw:
        # Convert from ADC -> V, with calibration factors, by default
            if channel == 1:
                data = np.float16(device.ch1_gain * (data * device.input_range_V / 2. ** device.input_bits + device.ch1_offset))
            elif channel == 2:
                data = np.float16(device.ch2_gain * (data * device.input_range_V / 2. ** device.input_bits + device.ch2_offset))

        if calib:
        # Save calibration data to files
            if channel == 1:
                np.savetxt('red_pitaya_data_ch1_calib.txt', data)
            elif channel == 2:
                np.savetxt('red_pitaya_data_ch2_calib.txt', data)
        else:
        # Save acquired data to files
            try:
                assert(t_file is not None)
            except:
                raise ValueError('Must supply timestamp when saving data outside of calibration mode')
            data.tofile(f'red_pitaya_data_ch{channel}_{t_file}.bin')
