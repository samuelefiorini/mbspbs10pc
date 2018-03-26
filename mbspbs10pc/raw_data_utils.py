"""This module keeps the functions for sequences extraction from MBS files."""
from __future__ import division, print_function

import datetime
import os

import numpy as np
import pandas as pd
from mbspbs10pc import __path__ as home
from mbspbs10pc.concessionals_utils import flatten
from tqdm import tqdm

MIN_SEQ_LENGTH = 10  # threshold for the minimum sequence length


def timespan_encoding(days):
    """Convert the input days in the desired timespan encoding.

    This function follows this encoding:
    --------------------------------
    Time duration        | Encoding
    --------------------------------
    [same day - 2 weeks] | 0
    (2 weeks  - 1 month] | 1
    (1 month  - 3 monts] | 2
    (3 months - 1 year]  | 3
    more than 1 year     | 4
    --------------------------------

    Parameters:
    --------------
    days: int
        The number of days between any two examinations.

    Returns:
    --------------
    enc: string
        The corresponding encoding.
    """
    if days < 0:
        raise ValueError('Unsupported negative timespans')
    elif days >= 0 and days <= 14:
        enc = 0
    elif days > 14 and days <= 30:  # using the "business" month duration
        enc = 1
    elif days > 30 and days <= 90:  # using the "business" month duration
        enc = 2
    elif days > 90 and days <= 360:  # using the "business" year duration
        enc = 3
    else:
        enc = 4
    return str(enc)


def get_raw_data(mbs_files, sample_pin_lookout, exclude_pregnancy=False, source=None, n_jobs=4):
    """Extract the sequences and find the additional features.

    This function, given the input list of patient identifiers `source` scans
    the `mbs_files` and extract the MBS items sequence. It also finds additional
    info on the patient such as age and sex from the `sample_pin_lookout` file.
    Unstructured sequences and additional info are referred to as raw_data.

    Parameters:
    --------------
    mbs_files: list
        List of input MBS files.

    sample_pin_lookout: string
        Location of the `SAMPLE_PIN_LOOKUP.csv` file.

    exclude_pregnancy: bool
        Exclude subjectes underatking pregnancy-related items.

    source: string
        Location of the 'PTNT_ID' csv file generated by `labels_assignment.py`.

    n_jobs: integer
        The number of processes that have asyncronous access to the input files.

    Returns:
    --------------
    raw_data: pandas.DataFrame
        Having `PIN` as index and `['seq', 'avg_age', 'last_pinstate', 'sex']` as
        columns.
    """
    # Step 0: load the source file, the btos4d file and the diabetes drugs file
    dfs = pd.read_csv(source, header=0, index_col=0)
    dfs['PTNT_ID'] = dfs.index  # FIXME: this is LEGACY CODE
    btos4d = pd.read_csv(os.path.join(home[0], 'data', 'btos4d.csv'), header=0,
                         usecols=['ITEM', 'BTOS-4D'])

    # check weather or not exclude pregnant subjects
    if exclude_pregnancy:
        pregnancy_items = pd.read_csv(os.path.join(home[0], 'data', 'pregnancy_items.csv'),
                                      header=0, usecols=['ITEM'])
        pregnancy_items = set(pregnancy_items['ITEM'])

    # Step 1: get sex and age
    df_pin_lookout = pd.read_csv(sample_pin_lookout, header=0)
    df_pin_lookout['AGE'] = datetime.datetime.now().year - df_pin_lookout['YOB']  # this is the age as of TODAY
    dfs = pd.merge(dfs, df_pin_lookout, how='left', left_on='PTNT_ID', right_on='PIN')[['PIN', 'SEX', 'AGE', 'START_DATE', 'END_DATE', 'YOB']]
    dfs = dfs.set_index('PIN')  # set PIN as index (easier access below)
    # SPPLY_DT is the date of the FIRST diabetes drug supply

    # Step 2: follow each patient in the mbs files
    # at first create a very large DataFrame with all the MBS files
    # (keeping only the relevant columns)
    # It is possible here to exclude pregnant subjects
    mbs_df = pd.DataFrame(columns=['PIN', 'ITEM', 'DOS', 'PINSTATE'])
    for mbs in tqdm(mbs_files, desc='MBS files loading', leave=False):
        dd = pd.read_csv(mbs, header=0, usecols=['PIN', 'ITEM', 'DOS', 'PINSTATE'], engine='c')
        if exclude_pregnancy: dd = dd.loc[~dd['ITEM'].isin(pregnancy_items), :]
        dd = dd.loc[dd['PIN'].isin(dfs.index), :]  # keep only the relevant samples
        dd = pd.merge(dd, btos4d, how='left', on='ITEM') # get the BTOS4D
        mbs_df = pd.concat((mbs_df, dd))
    mbs_df.loc[:, 'DOS'] = pd.to_datetime(mbs_df['DOS'], format='%d%b%Y')

    # Group by PIN (skip empty groups)
    grouped = mbs_df.groupby('PIN').filter(lambda x: len(x) > 1).groupby('PIN')

    def extract_sequence(group): # the variable dfs is local here
        """Extract sequence from group of MBS items.

        This function, in order to be applied to pandas groups, must be wrapped by
        `functools.partial`. For parallel application see `mbspbs10pc.utils.applyParallel`.
        """
        pin = group.PIN.values[0]  # extract the current PIN
        tmp = group.sort_values(by='DOS')  # sort by DOS
        start_date = dfs.loc[pin]['START_DATE']  # get start date
        end_date = dfs.loc[pin]['END_DATE']  # get end date
        # select sequence timespan
        tmp = tmp.loc[np.logical_and(tmp['DOS'] >= start_date, tmp['DOS'] <= end_date), :]
        if tmp.shape[0] > MIN_SEQ_LENGTH:  # keep only non-trivial sequencences
            # evaluate the first order difference and convert each entry in WEEKS
            timedeltas = map(lambda x: pd.Timedelta(x).days,
                             tmp['DOS'].values[1:] - tmp['DOS'].values[:-1])
            # then build the sequence as ['exam', idle-days, 'exam', idle-days, ...]
            seq = flatten([[item, dt] for item, dt in zip(tmp['ITEM'].values, timedeltas)])
            seq.append(tmp['ITEM'].values.ravel()[-1])  # add the last exam (ignored by zip)
            # and finally collapse everything down to a string like 'G0G1H...'
            seq = ' '.join(map(str, seq))
            # compute the average age during the treatment by computing the average year
            avg_age = np.mean(pd.DatetimeIndex(tmp['DOS'].values.ravel()).year)  - dfs.loc[pin]['YOB']
            # extract the last pinstate
            last_pinstate = tmp['PINSTATE'].values.ravel()[-1]
            # extract gender
            sex = dfs.loc[pin]['SEX']
        else:
            seq, avg_age, last_pinstate, sex = np.nan, np.nan, np.nan, np.nan

        return pd.Series({'seq': seq, 'avg_age': avg_age, 'last_pinstate': last_pinstate, 'sex': sex})

    return grouped.apply(extract_sequence).dropna()
