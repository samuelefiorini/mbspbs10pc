#!/usr/bin/env python
"""Extract raw data from the MBS files.

Given a list of PTNT_ID, this script aims at extracting a sequence of MBS
services usage of each individual. A possible list may be something like:

    123: [101, 15, 102, 7, 103]

where 101, 102 and 103 are different broad type of service BOTS (see data/imap.tsv).
While 15 and 7 are the timespan (in days) between the two examinations.
So, MBS provider in even position and days in odd positions.

Remarks:
- PTNT_ID in PBS is referred to as PIN in MBS.
"""

from __future__ import print_function

import argparse
import cPickle as pkl
import os
from datetime import datetime

import mbspbs10pc.raw_data_utils as utils
import pandas as pd
from mbspbs10pc.utils import check_input


def parse_arguments():
    """"Parse input arguments."""
    parser = argparse.ArgumentParser(description='MBS-PBS 10% data/labels '
                                                 'extraction.')
    parser.add_argument('-r', '--root', type=str,
                        help='Dataset root folder (default=../../data).',
                        default=None)
    parser.add_argument('-s', '--source', type=str,
                        help='The PTNT_ID csv file generated by '
                        'labels_assignment.py.',
                        default=None)
    parser.add_argument('-o', '--output', type=str,
                        help='Ouput file name root.',
                        default=None)
    parser.add_argument('-sic', '--skip_input_check', action='store_false',
                        help='Skip the input check (default=False).')
    parser.add_argument('-nj', '--n_jobs', type=int,
                        help='The number of processes to use.', default=4)
    # parser.add_argument('-cs', '--chunk_size', type=int,
    #                     help='The numer of rows each process has access to.',
    #                     default=1000)
    args = parser.parse_args()
    return args


def init_main():
    """Initialize the main routine."""
    args = parse_arguments()

    if args.source is None or not os.path.exists(args.source):
        raise ValueError('{} is not a valid PTNT_ID csv file'.format(args.source))

    # Check input dataset
    if args.root is None:
        args.root = os.path.join('..', '..', 'data')
    if args.skip_input_check: check_input(args.root)

    # Check output filename
    if args.output is None:
        args.output = args.source[:-4]+'_'

    return args


def main():
    """Main find_concessionas.py routine."""
    print('-------------------------------------------------------------------')
    print('MBS - PBS 10% dataset utility: extract_sequences.py')
    print('-------------------------------------------------------------------')
    args = init_main()

    print('* Root data folder: {}'.format(args.root))
    print('* PTNT_ID list: {}'.format(args.source))
    print('* Output files: {}.[pkl, csv, ...]'.format(args.output))
    print('* Number of jobs: {}'.format(args.n_jobs))
    # print('* Chunk size: {}'.format(args.chunk_size))
    print('-------------------------------------------------------------------')

    # MBS 10% dataset files
    mbs_files = filter(lambda x: x.startswith('MBS'), os.listdir(args.root))
    mbs_files_fullpath = [os.path.join(args.root, mbs) for mbs in mbs_files]
    sample_pin_lookout = filter(lambda x: x.startswith('SAMPLE'),
                                os.listdir(args.root))[0]

    # Get the features
    filename = args.output+'_raw_data_.pkl'
    if not os.path.exists(filename):
        raw_data, extra_info = utils.get_raw_data(mbs_files_fullpath,
                                                  os.path.join(args.root,
                                                               sample_pin_lookout),
                                                  args.source,
                                                  n_jobs=args.n_jobs)
        print('* Saving {} '.format(filename), end=' ')
        pkl.dump({'raw_data': raw_data, 'extra_info': extra_info}, open(filename, 'wb'))
        print(u'\u2713')


################################################################################

if __name__ == '__main__':
    main()
