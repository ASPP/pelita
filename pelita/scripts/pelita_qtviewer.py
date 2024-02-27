#!/usr/bin/env python3

import argparse
import os
import sys

from PyQt6.QtWidgets import QApplication

import pelita
from pelita.ui.qt.qt_viewer import QtViewer

from .script_utils import start_logging


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

LOG_QT = os.environ.get("PELITA_LOG_QT", None)

parser = argparse.ArgumentParser(description='Open a Qt viewer')
parser.add_argument('subscribe_sock', metavar="URL", type=str,
                    help='subscribe socket')
parser.add_argument('--controller-address', metavar="URL", type=str,
                    help='controller address')
parser.add_argument('--geometry', type=geometry_string,
                    help='geometry')
parser.add_argument('--delay', type=int,
                    help='delay')
parser.add_argument('--export', type=str, metavar="FOLDER", help='png export path')
parser.add_argument('--stop-after', type=int, metavar="N",
                    help='Stop after N rounds.')
parser._optionals = parser.add_argument_group('Options')
parser.add_argument('--version', help='show the version number and exit',
                    action='store_const', const=True)
parser.add_argument('--log', help='print debugging log information to'
                                  ' LOGFILE (default \'stderr\')',
                    metavar='LOGFILE', const='-', nargs='?')

def main():
    args = parser.parse_args()
    if args.version:
        print("Pelita {}".format(pelita.__version__))
        sys.exit(0)

    if LOG_QT or args.log:
        start_logging(args.log)

    viewer_args = {
        'address': args.subscribe_sock,
        'controller_address': args.controller_address,
        'geometry': args.geometry,
        'delay': args.delay,
        'export': args.export,
        'stop_after': args.stop_after
    }
    app = QApplication(sys.argv)
    app.setApplicationName("Pelita")
    app.setApplicationDisplayName("Pelita")

    mainWindow = QtViewer(**{k: v for k, v in list(viewer_args.items()) if v is not None})
    mainWindow.show()
    ret = app.exec()
    sys.exit(ret)

if __name__ == '__main__':
    main()
