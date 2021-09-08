"""
08/21, R James, F Alder
"""

import numpy as np
import paramiko
import subprocess

import PyRPStream as rp
export, __all__ = rp.exporter()


@export
class CalibUtil:
    """
    """
    def __init__(self, device_name):
        # RP device
        self.device_name = device_name
        self.device = rp.RPDevice(device_name, ignore_calib=True)
        # RP device SSH connection information
        self.user_host_password = ('root', 'rp-f05a98.local', 'root')
        # Calibration parameters
        self.ch1_offset = 0
        self.ch1_gain = 1
        self.ch2_offset = 0
        self.ch2_gain = 1


    def reset_calib(self):
        """
        """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.user_host_password[1], username=self.user_host_password[0], password=self.user_host_password[2])
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('/opt/redpitaya/bin/calib -d')
        subprocess.Popen("rm -f {filename}".format(filename=self.device_name + '_calib.txt'),
                         shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()


    def write_calib(self):
        """
        """
        file = open(self.device_name + '_calib.txt', 'w')
        lines = [str(self.ch1_offset), str(self.ch1_gain), str(self.ch2_offset), str(self.ch2_gain)]
        file.writelines('%s\n' % l for l in lines)


    def ground_inputs(self):
        """
        """
        print('NOTE: this will only work if inputs are grounded')

        # self.device.connect()
        # self.device.acquire_calib()
        self.device.disconnect()

        data = np.loadtxt('red_pitaya_data_ch1_offset.txt')
        mean_reading = np.mean(data)
        offset = - mean_reading * self.device.input_range_V / (2 ** self.device.input_bits)
        self.ch1_offset = offset

        data = np.loadtxt('red_pitaya_data_ch2_offset.txt')
        mean_reading = np.mean(data)
        offset = - mean_reading * self.device.input_range_V / (2 ** self.device.input_bits)
        self.ch2_offset = offset


    def DC_inputs(self):
        """
        """
        print('NOTE: this will only work if inputs are given 0.5 V DC signals')

        # self.device.connect()
        # self.device.acquire_calib()
        self.device.disconnect()

        data = np.loadtxt('red_pitaya_data_ch1_gain.txt')
        mean_reading = np.mean(data)
        gain = 0.5 / (mean_reading * self.device.input_range_V / 2 ** self.device.input_bits + self.ch1_offset)
        self.ch1_gain = gain

        data = np.loadtxt('red_pitaya_data_ch2_gain.txt')
        mean_reading = np.mean(data)
        gain = 0.5 / (mean_reading * self.device.input_range_V / 2 ** self.device.input_bits + self.ch2_offset)
        self.ch2_gain = gain
