#!/usr/bin/env python3
#
# This script can be used for any purpose without limitation subject to the
# conditions at http://www.ccdc.cam.ac.uk/Community/Pages/Licences/v2.aspx
#
# This permission notice and the following statement of attribution must be
# included in all copies or substantial portions of this script.
#
# 2020-09-15: created by the Cambridge Crystallographic Data Centre
#
'''
One script to call them all.

'''

from pathlib import Path
import shutil
import subprocess
import sys

import goldhpc_utilities

script_list = [
    ['cluster_batching.py'],
    ['cluster_submit.py'],
    ['cluster_monitor.py'],
    ['cluster_status.py'],
    ['cluster_timing.py'],
    ['cluster_collect.py']
]


def locate_script(script_name):
    '''Given a script name, locate it:

    1. In the directory goldhpc_utilitites.py is located
    2. In the directory this script is located
    3. In PATH
    4. In current working directory

    If all fails, raises.

    '''
    locations = [
            lambda x: goldhpc_utilities.GOLDHPC_DIR / x,
            lambda x: Path(__file__).parent.resolve() / x,
            lambda x: Path(shutil.which(x)),
            lambda x: Path.cwd() / x,
            ]
    for location in locations:
        try:
            script = location(script_name)
        except TypeError:
            continue
        if script.exists():
            return str(script)
    raise FileNotFoundError(f'{script_name} not found')


def main():
    for script in script_list:
        try:
            script[0] = locate_script(script[0])
            completed_process = subprocess.run(script)
        except FileNotFoundError as exc:
            sys.exit(f'{exc}')
        if completed_process.returncode != 0:
            sys.exit(completed_process.returncode)


if __name__ == '__main__':
    main()
