import socket
from math import ceil
from os import urandom
import binascii


def get_mac():
    '''Get the mac-address of the computer
    '''
    try:
        str = open('/sys/class/net/wlan0/address').read()
    except:   # noqa
        raise RuntimeError('Could not get MAC for wlan0')
    return str[0:17]    # cut off trailing \n


def rand_str(length):
    '''Get a random string of length 'length'
    '''
    return binascii.b2a_hex(
            urandom(
                int(ceil(float(length)/2))
                )
            )[:length]


def get_ip():
    '''Get the ip-address of the computer
    '''
    ip = socket.gethostbyname(socket.gethostname())

    if ip.startswith("127."):
        # There shouldn't be any need to actually reach a destination to get our ip
        server = "192.168.0.80"

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((server, 80))
            ip = s.getsockname()[0]
        except:  # noqa
            ip = "?"
        finally:
            s.close()

    return ip
