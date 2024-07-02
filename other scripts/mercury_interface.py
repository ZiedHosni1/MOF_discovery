#
# This script can be used for any purpose without limitation subject to the
# conditions at http://www.ccdc.cam.ac.uk/Community/Pages/Licences/v2.aspx
#
# This permission notice and the following statement of attribution must be
# included in all copies or substantial portions of this script.
#
# 2015-05-01: created by Clare Macrae, the Cambridge Crystallographic Data Centre
# 2015-06-18: made available by the Cambridge Crystallographic Data Centre
#

'''
    mercury_interface.py   -   parse arguments sent by mercury

This file is designed to match the version of Mercury it is released with,
and so it is not intended to be modified by users.

'''
from ccdc.utilities import ApplicationInterface

import warnings
# Warnings will cause the launched script to crash in mercury, so let's ignore them.
warnings.simplefilter('ignore')


class MercuryInterface(ApplicationInterface):
    """ Thin wrapper for the new ApplicationInterface class.
    This is built as a thin wrapper so that ApplicationInterface becomes a drop-in replacement
    for existing scripts.
    """
    pass


if __name__ == "__main__":
    raise RuntimeError('\n\nSorry - this is a helper script.\n'
                       'It is not intended for running - and should somehow '
                       'be hidden from the scripts menu')
