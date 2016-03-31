#!/usr/bin/env python3

import argparse

from pelita.ui.tk_viewer import TkViewer


def geometry_string(s):
    """Get a X-style geometry definition and return a tuple.

    600x400 -> (600,400)
    """
    try:
        x_string, y_string = s.split('x')
        geometry = (int(x_string), int(y_string))
    except ValueError:
        msg = "%s is not a valid geometry specification" %s
        raise argparse.ArgumentTypeError(msg)
    return geometry

parser = argparse.ArgumentParser(description='Open a Tk viewer')
parser.add_argument('subscribe_sock', metavar="URL", type=str,
                    help='subscribe socket')
parser.add_argument('--controller-address', metavar="URL", type=str,
                    help='controller address')
parser.add_argument('--geometry', type=geometry_string,
                    help='geometry')
parser.add_argument('--delay', type=int,
                    help='delay')

def run_viewer():
    args = parser.parse_args()
    tkargs = {
        'address': args.subscribe_sock,
        'controller_address': args.controller_address,
        'geometry': args.geometry,
        'delay': args.delay
    }
    v = TkViewer(**{k: v for k, v in list(tkargs.items()) if v is not None})
    v.run()

if __name__ == '__main__':
    run_viewer()
