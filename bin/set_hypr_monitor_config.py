#!/usr/bin/env python

# A work in progress to eventually replace set_hypr_monitor_config and set_hypr_monitor_config.awk

import argparse
import os
import sys
from pathlib import Path
import shutil
import re

MAX_INDENT = 10

arg_parser = argparse.ArgumentParser(
    description='''
Edits the Hyprland configuration file to set up a monitor configuration based on what monitors are
connected.

Note: This script is intended for use with up to 3 monitors placed side-by-side, or up to 3 
side-by-side external monitors and a builtin laptop monitor. 
''',
    epilog='Hyprland monitor configuration',
    argument_default=None,
    usage='''
[-h] [--left-monitor <name> <resolution> <refresh-rate> <starting-coordinate> <scale>]
[--center-monitor <name> <resolution> <refresh-rate> <starting-coordinate> <scale>]
[--right-monitor <name> <resolution> <refresh-rate> <starting-coordinate> <scale>]
[--builtin-monitor <name> <resolution> <refresh-rate> <starting-coordinate> <scale>]
--secondary-monitor <l|r>

For help with these values, see https://wiki.hyprland.org/configuring/monitors/
'''
)

arg_parser.add_argument(
    '--left-monitor',
    '-l',
    help='Left monitor hypr configuration',
    nargs=5
)

arg_parser.add_argument(
    '--center-monitor',
    '-c',
    help='Center monitor hypr configuration',
    nargs=5
)

arg_parser.add_argument(
    '--right-monitor',
    '-r',
    help='Right monitor hypr configuration',
    nargs=5
)

arg_parser.add_argument(
    '--builtin-monitor',
    '-b',
    help='Builtin monitor hypr configuration',
    nargs=5
)

arg_parser.add_argument(
    '--secondary-monitor',
    '-s',
    help='Place secondary monitor to the left (l) or right (r) when only 2 monitors are connected?',
    required=True,
    choices=['l', 'r']
)

arg_parser.add_argument(
    '--verbose',
    '-v',
    help='Print output to the CLI verbosely',
    action='store_true'
)

arg_parser.add_argument(
    '--dry-run',
    '-d',
    help='Output new config file, but do not overwrite existing config',
    action='store_true'
)

def validate_monitor_config_args(monitor_config_args: list) -> bool:
    valid = True

    if not RESOLUTION_REGEX.match(monitor_config_args[1]):
        valid = False

        print(
            f'Error, invalid resolution for {monitor_config_args[0]} -> {monitor_config_args[1]}',
            file=sys.stderr
        )

    if not REFRESH_RATE_REGEX.match(monitor_config_args[2]):
        valid = False

        print(
            f'Error, invalid refresh rate for {monitor_config_args[0]} -> {monitor_config_args[2]}',
            file=sys.stderr
        )

    if not POSITION_COORDINATE_REGEX.match(monitor_config_args[3]):
        valid = False

        print(
            f'Error, starting coordinate for {monitor_config_args[0]} -> {monitor_config_args[3]}',
            file=sys.stderr
        )

    if not SCALING_REGEX.match(monitor_config_args[4]):
        valid = False

        print(
            f'Error, scale for {monitor_config_args[0]} -> {monitor_config_args[4]}',
            file=sys.stderr
        )

    return valid

HOME_DIR = os.getenv('HOME')
HYPR_CONFIG_FILE = f'{HOME_DIR}/.config/hypr/hyprland.conf'
HYPR_CONFIG_FILE_BAK = f'{HOME_DIR}/.config/hypr/hyprland.conf.bak'
HYPR_CONFIG_TMP_FILE = '/tmp/hypr_config'

WAYBAR_CONFIG_FILE = f'{HOME_DIR}/.config/waybar/config'
WAYBAR_CONFIG_FILE_BAK = f'{HOME_DIR}/.config/waybar/config.bak'
WAYBAR_OUTPUT_START = '    "output": ["'
WAYBAR_OUTPUT_END = '", ],\n'

RESOLUTION_REGEX = re.compile('^[0-9]{4}x[0-9]{3,4}$')
REFRESH_RATE_REGEX = re.compile('^[0-9]{2,3}$')
POSITION_COORDINATE_REGEX = re.compile('^[0-9]{1,4}x0$')
SCALING_REGEX = re.compile('^[0-9]$')

DRM_DIR = '/sys/class/drm'
STATUS_FILE = 'status'
MONITOR_DIR_REGEX = re.compile(f'^{DRM_DIR}/card[0-9]-\\S+$')
CONNECTED_STATUS = 'connected'

POSITION_COORDINATE_INDEX = 3

cli_args = arg_parser.parse_args()

if not os.path.isfile(HYPR_CONFIG_FILE_BAK):
    if cli_args.verbose:
        print('No hyprland.conf.bak found, creating one...')

    shutil.copyfile(HYPR_CONFIG_FILE, HYPR_CONFIG_FILE_BAK)

if not os.path.isfile(WAYBAR_CONFIG_FILE_BAK):
    if cli_args.verbose:
        print('No Waybar config.bak found, creating one...')

    shutil.copyfile(WAYBAR_CONFIG_FILE, WAYBAR_CONFIG_FILE_BAK)

left_monitor_configs = cli_args.left_monitor
center_monitor_configs = cli_args.center_monitor
right_monitor_configs = cli_args.right_monitor
builtin_monitor_configs = cli_args.builtin_monitor
secondary_monitor_left = cli_args.secondary_monitor == 'l'
verbose = cli_args.verbose
dry_run = cli_args.dry_run

LEFT_MONITOR_DIR_REGEX = re.compile(f'^\\S+{left_monitor_configs[0]}$')\
    if left_monitor_configs else None

CENTER_MONITOR_DIR_REGEX = re.compile(f'^\\S+{center_monitor_configs[0]}$')\
    if center_monitor_configs else None

RIGHT_MONITOR_DIR_REGEX = re.compile(f'^\\S+{right_monitor_configs[0]}$')\
    if right_monitor_configs else None

BUILTIN_MONITOR_DIR_REGEX = re.compile(f'^\\S+{builtin_monitor_configs[0]}$')\
    if builtin_monitor_configs else None

drm_path = Path(DRM_DIR)

monitor_dirs = [
    str(dir_name) for dir_name in drm_path.iterdir()
    if dir_name.is_dir() and MONITOR_DIR_REGEX.match(str(dir_name))
]

left_monitor_connected = False
center_monitor_connected = False
right_monitor_connected = False
builtin_monitor_connected = False

for monitor_dir in monitor_dirs:

    with open(f'{monitor_dir}/{STATUS_FILE}', 'r') as file:
        monitor_status = file.read().strip()

        if LEFT_MONITOR_DIR_REGEX and LEFT_MONITOR_DIR_REGEX.match(monitor_dir):
            left_monitor_connected = monitor_status == CONNECTED_STATUS
        elif CENTER_MONITOR_DIR_REGEX and CENTER_MONITOR_DIR_REGEX.match(monitor_dir):
            center_monitor_connected = monitor_status == CONNECTED_STATUS
        elif RIGHT_MONITOR_DIR_REGEX and RIGHT_MONITOR_DIR_REGEX.match(monitor_dir):
            right_monitor_connected = monitor_status == CONNECTED_STATUS
        elif BUILTIN_MONITOR_DIR_REGEX and BUILTIN_MONITOR_DIR_REGEX.match(monitor_dir):
            builtin_monitor_connected = monitor_status == CONNECTED_STATUS

if left_monitor_connected and center_monitor_connected and right_monitor_connected:

    if verbose:
        print('... all monitors connected')

    waybar_position = f'{WAYBAR_OUTPUT_START}{center_monitor_configs[0]}{WAYBAR_OUTPUT_END}'
elif not left_monitor_connected and center_monitor_connected and right_monitor_connected:

    if verbose:
        print('... left monitor not connected')

    builtin_monitor_configs[POSITION_COORDINATE_INDEX] = right_monitor_configs[POSITION_COORDINATE_INDEX]
    right_monitor_configs[POSITION_COORDINATE_INDEX] = center_monitor_configs[POSITION_COORDINATE_INDEX]
    center_monitor_configs[POSITION_COORDINATE_INDEX] = left_monitor_configs[POSITION_COORDINATE_INDEX]

    if secondary_monitor_left:
        waybar_position = f'{WAYBAR_OUTPUT_START}{right_monitor_configs[0]}{WAYBAR_OUTPUT_END}'
    else:
        waybar_position = f'{WAYBAR_OUTPUT_START}{center_monitor_configs[0]}{WAYBAR_OUTPUT_END}'
elif left_monitor_connected and not center_monitor_connected and right_monitor_connected:

    if verbose:
        print('... center monitor not connected')

    builtin_monitor_configs[POSITION_COORDINATE_INDEX] = right_monitor_configs[POSITION_COORDINATE_INDEX]
    right_monitor_configs[POSITION_COORDINATE_INDEX] = center_monitor_configs[POSITION_COORDINATE_INDEX]

    if secondary_monitor_left:
        waybar_position = f'{WAYBAR_OUTPUT_START}{right_monitor_configs[0]}{WAYBAR_OUTPUT_END}'
    else:
        waybar_position = f'{WAYBAR_OUTPUT_START}{left_monitor_configs[0]}{WAYBAR_OUTPUT_END}'
elif left_monitor_connected and center_monitor_connected and not right_monitor_connected:

    if verbose:
        print('... right monitor not connected')

    builtin_monitor_configs[POSITION_COORDINATE_INDEX] = right_monitor_configs[POSITION_COORDINATE_INDEX]

    if secondary_monitor_left:
        waybar_position = f'{WAYBAR_OUTPUT_START}{center_monitor_configs[0]}{WAYBAR_OUTPUT_END}'
    else:
        waybar_position = f'{WAYBAR_OUTPUT_START}{left_monitor_configs[0]}{WAYBAR_OUTPUT_END}'
elif left_monitor_connected and not center_monitor_connected and not right_monitor_connected:

    if verbose:
        print('... center and right monitors not connected')

    builtin_monitor_configs[POSITION_COORDINATE_INDEX] = center_monitor_configs[POSITION_COORDINATE_INDEX]
    waybar_position = f'{WAYBAR_OUTPUT_START}{left_monitor_configs[0]}{WAYBAR_OUTPUT_END}'
elif not left_monitor_connected and center_monitor_connected and not right_monitor_connected:

    if verbose:
        print('... left and right monitors not connected')

    builtin_monitor_configs[POSITION_COORDINATE_INDEX] = center_monitor_configs[POSITION_COORDINATE_INDEX]
    center_monitor_configs[POSITION_COORDINATE_INDEX] = left_monitor_configs[POSITION_COORDINATE_INDEX]
    waybar_position = f'{WAYBAR_OUTPUT_START}{center_monitor_configs[0]}{WAYBAR_OUTPUT_END}'
elif not left_monitor_connected and not center_monitor_connected and right_monitor_connected:

    if verbose:
        print('... left and center monitors not connected')

    builtin_monitor_configs[POSITION_COORDINATE_INDEX] = center_monitor_configs[POSITION_COORDINATE_INDEX]
    right_monitor_configs[POSITION_COORDINATE_INDEX] = left_monitor_configs[POSITION_COORDINATE_INDEX]
    waybar_position = f'{WAYBAR_OUTPUT_START}{right_monitor_configs[0]}{WAYBAR_OUTPUT_END}'
elif not left_monitor_connected and not center_monitor_connected and not right_monitor_connected:

    if verbose:
        print('... No external monitors are connected')

    builtin_monitor_configs[POSITION_COORDINATE_INDEX] = left_monitor_configs[POSITION_COORDINATE_INDEX]
    waybar_position = f'{WAYBAR_OUTPUT_START}{builtin_monitor_configs[0]}{WAYBAR_OUTPUT_END}'

left_monitor = ''
center_monitor = ''
right_monitor = ''
builtin_monitor = ''

if left_monitor_configs:
    if not validate_monitor_config_args(left_monitor_configs):
        exit(1)

    left_monitor = (f'monitor = {left_monitor_configs[0]}, {left_monitor_configs[1]}'
                    f'@{left_monitor_configs[2]}, {left_monitor_configs[3]}, {left_monitor_configs[4]}')

if center_monitor_configs:
    if not validate_monitor_config_args(center_monitor_configs):
        exit(1)

    center_monitor = (f'monitor = {center_monitor_configs[0]}, {center_monitor_configs[1]}'
                      f'@{center_monitor_configs[2]}, {center_monitor_configs[3]}, {center_monitor_configs[4]}')

if right_monitor_configs:
    if not validate_monitor_config_args(right_monitor_configs):
        exit(1)

    right_monitor = (f'monitor = {right_monitor_configs[0]}, {right_monitor_configs[1]}'
                     f'@{right_monitor_configs[2]}, {right_monitor_configs[3]}, {right_monitor_configs[4]}')

if builtin_monitor_configs:
    if not validate_monitor_config_args(builtin_monitor_configs):
        exit(1)

    builtin_monitor = (f'monitor = {builtin_monitor_configs[0]}, {builtin_monitor_configs[1]}'
                       f'@{builtin_monitor_configs[2]}, {builtin_monitor_configs[3]}, {builtin_monitor_configs[4]}')

monitor_configs = [
    left_monitor,
    center_monitor,
    right_monitor,
    builtin_monitor
]

if verbose:

    for monitor_config in monitor_configs:
        print(monitor_config)

# TODO: Update the config files for the currently connected monitors
