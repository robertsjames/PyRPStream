"""
08/21, R James, F Alder

Adapted from script by https://github.com/awmlee
"""

import numpy as np
import time

import PyRPStream as rp
export, __all__ = rp.exporter()


@export
class RPDevice:
    """
    """
    def __init__(self):
        # Connection information
        self.address_port = ('rp-f05a98.local', 8900)
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


    def acquire(self, acq_time, file_stamps='timestamps'):
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
            assert(isinstance(file_stamps, str))
        except:
            raise TypeError('file_stamps must be string')
        try:
            assert(file_stamps == 'timestamps' or 'numerical')
        except:
            raise ValueError('file_stamps must be either timestamps or numerical')

        try:
            assert(acq_time > 0)
        except:
            raise TypeError('Invalid acquisition time value')

        # Number of messages to use for data rate calculation
        n_samp = 10

        t_start = time.time()
        t_prev = t_start
        i = 0

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
                    break

                # Otherwise, save the data to files
                if file_stamps == 'timestamps':
                    np.savetxt(f'red_pitaya_data_ch1_{t}.txt', np.frombuffer(client_reply.reply['ch1_data'], dtype=np.int16))
                    np.savetxt(f'red_pitaya_data_ch2_{t}.txt', np.frombuffer(client_reply.reply['ch2_data'], dtype=np.int16))
                else:
                    np.savetxt(f'red_pitaya_data_ch1_{i}.txt', np.frombuffer(client_reply.reply['ch1_data'], dtype=np.int16))
                    np.savetxt(f'red_pitaya_data_ch2_{i}.txt', np.frombuffer(client_reply.reply['ch2_data'], dtype=np.int16))

                # Calculate the data rate every n_samp messages
                if i == n_samp:
                    print('Data rate is ', n_samp * 2**16 / (t - t_prev) / 1024 / 1024)  # MBytes/second
                    i = 0
                    t_prev = t

                i += 1