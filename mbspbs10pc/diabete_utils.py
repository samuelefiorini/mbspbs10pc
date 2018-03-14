"""This module has all the functions needed to detect diabetics."""

import multiprocessing as mp
import os
import warnings
from multiprocessing import Manager

import numpy as np
import pandas as pd
from mbspbs10pc import __path__ as home
from tqdm import tqdm

___PBS_FILES_DICT__ = dict()
warnings.filterwarnings('ignore')


def find_metafter(dd, pos_id, target_year=2012):
    """"Find the people on metformin + other drug.

    This function finds the patients that were prescribed to some non-metformin
    diabetes drug after an initial metformin prescription.

    Remark: There is no difference between someone that changes metformin for a
    new drug, and someone who end up using both the drugs.

    Parameters:
    --------------
    dd: dictionary
        The output of find_diabetics().

    pos_id: pd.DataFrame
        The DataFrame generated from the output of find_positive_samples().

    target_year: integer (default=2012)
        The target year

    Returns:
    --------------
    out: dictionary
        Dictionary having target patient IDs (metformin + other drug) as keys
        and SPPLY_DT as values.
    """
    # Take only the relevant dd values
    _dd = dd['PBS_SAMPLE_10PCT_'+str(target_year)+'.csv']

    # Load the metformin items
    met_items = set(pd.read_csv(os.path.join(home[0], 'data', 'metformin_items.csv'),
                    header=0).values.ravel())

    # Build the DataFrame of interest
    df = pd.DataFrame(columns=['PTNT_ID', 'ITM_CD', 'SPPLY_DT'])

    # Iterate on the positive indexes and fill up the data frame
    i = 0
    for idx in pos_id.index:
        for itm, dt in zip(_dd[idx]['ITM_CD'], _dd[idx]['SPPLY_DT']):
            df.loc[i, 'PTNT_ID'] = idx
            df.loc[i, 'ITM_CD'] = itm
            df.loc[i, 'SPPLY_DT'] = pd.to_datetime(dt, format='%d%b%Y')
            i += 1

    # Keep only patients that have at least one metformin prescription
    metonce = []
    for _, row in df.iterrows():
        if row['ITM_CD'] in met_items:
            metonce.append(row['PTNT_ID'])
    metonce = set(metonce)

    # Iterate on them
    metafter = []
    for idx in metonce:
        tmp = df.loc[df['PTNT_ID'] == idx, ['ITM_CD', 'SPPLY_DT']]
        # Sort by date
        tmp.sort_values(by='SPPLY_DT', inplace=True)
        # Get where the metformin was prescribed
        mask = [s in met_items for s in tmp['ITM_CD']]
        mask = np.where(map(lambda x: not x, mask))[0]
        # If the non-metformin drug is prescribed after the position 0
        # it is likely that the patient started to take a new medication
        if len(mask) > 0 and not (mask[0] == 0):
            metafter.append(idx)

    # Retrieve the metafter subjects and create the output dictionary
    out = {idx: min(df.loc[df['PTNT_ID'] == idx, 'SPPLY_DT']) for idx in metafter}

    return out


def find_metonly(dd, pos_id, target_year=2012):
    """"Find the people on metformin only.

    Parameters:
    --------------
    dd: dictionary
        The output of find_diabetics().

    pos_id: pd.DataFrame
        The DataFrame generated from the output of find_positive_samples().

    target_year: integer (default=2012)
        The target year

    Returns:
    --------------
    out: dictionary
        Dictionary having target patient IDs (metformin only) as keys and
        SPPLY_DT as values.
    """
    # Take only the relevant dd values
    _dd = dd['PBS_SAMPLE_10PCT_'+str(target_year)+'.csv']

    # Load the metformin items
    met_items = set(pd.read_csv(os.path.join(home[0], 'data', 'metformin_items.csv'),
                    header=0).values.ravel())

    # Build the DataFrame of interest
    df = pd.DataFrame(columns=['PTNT_ID', 'ITM_CD', 'SPPLY_DT'])

    # Iterate on the positive indexes and fill up the data frame
    i = 0
    for idx in pos_id.index:
        for itm, dt in zip(_dd[idx]['ITM_CD'], _dd[idx]['SPPLY_DT']):
            df.loc[i, 'PTNT_ID'] = idx
            df.loc[i, 'ITM_CD'] = itm
            df.loc[i, 'SPPLY_DT'] = dt
            i += 1

    # Keep the pantients in metformin ONLY
    metonly = []
    for idx in df['PTNT_ID']:
        items = df.loc[df['PTNT_ID'] == idx, 'ITM_CD'].values.ravel().tolist()
        if set(items).issubset(met_items):
            metonly.append(idx)

    # Retrieve the metonly subjects and create the output dictionary
    out = {}
    for idx in metonly:
        # (but change to the correct datetime format first)
        out[idx] = min(map(lambda x: pd.to_datetime(x, format='%d%b%Y'),
                           df.loc[df['PTNT_ID'] == idx, 'SPPLY_DT']))

    return out


def find_positive_samples(dd, cc, target_year=2012):
    """Filter the population of interest according to the input target year.

    This function returns the `'PTNT_ID'` of the subjects that started taking
    diabetes drugs in the target year.

    Parameters:
    --------------
    dd: dictionary
        The output of find_diabetics().

    cc: set
        The intersection between the output of find_continuously_concessionals()
        and find_consistently_concessionals().

    target_year: integer (default=2012)
        The target year

    Returns:
    --------------
    positive_subjects: dict
        Dictionary having target patient IDs (positive class) as keys and
        SPPLY_DT as values.
    """
    _dd = dd['PBS_SAMPLE_10PCT_'+str(target_year)+'.csv']
    # Init the postive subjects with the full list of people taking
    # diabetes drugs in the target year
    positive_subjects = set(_dd.keys())
    positive_subjects = positive_subjects.intersection(cc)  # keep only the concessionals

    for year in np.arange(2008, target_year)[::-1]:
        curr = set(dd['PBS_SAMPLE_10PCT_'+str(year)+'.csv'].keys())
        curr = curr.intersection(cc)  # keep only the concessionals
        positive_subjects = set(filter(lambda x: x not in curr, positive_subjects))

    # Retrieve the list of positive subjects
    out = {}
    for k in list(positive_subjects):
        # (but change to the correct datetime format first)
        out[k] = min(map(lambda x: pd.to_datetime(x, format='%d%b%Y'),
                         _dd[k]['SPPLY_DT']))

    return out


def find_negative_samples(pbs_files, dd, cc):
    """Find the negative samples PTNT_ID.

    Negative samples are subjects that were NEVER prescribed to diabetes
    controlling drugs.

    Parameters:
    --------------
    pbs_files: list
        List of input PBS filenames.

    dd: dictionary
        The output of find_diabetics().

    cc: set
        The intersection between the output of find_continuously_concessionals()
        and find_consistently_concessionals().

    Returns:
    --------------
    negative_subjects: list
        The list of non target patient IDs (negative class).
    """
    # Start with an empty set, the iterate on each year and iteratively add
    # to the negative subjects list, the patient id that are not selected
    # as diabetic at the previous step.
    negative_subjects = set()

    diabetic_overall = set()
    for pbs in pbs_files:  # get all the patients using diabetes drugs
        diabetic_overall |= set(dd[os.path.split(pbs)[-1]])
    diabetic_overall = diabetic_overall.intersection(cc)   # keep only the concessionals

    for pbs in tqdm(pbs_files): # TODO maybe use multiprocessing here
        curr = set(pd.read_csv(pbs, header=0, usecols=['PTNT_ID']).values.ravel())
        curr = curr.intersection(cc)  # keep only the concessionals
        # iteratively increase the set of indexes
        negative_subjects |= set(filter(lambda x: x not in diabetic_overall, curr))

    return list(negative_subjects)


def find_diabetics(pbs_files, filter_copayments=False, n_jobs=1):
    """Search people using diabetes drugs in input PBS files.

    Parameters:
    --------------
    pbs_files: list
        List of input PBS filenames.

    filter_copayments: bool
        When True, entries in the PBS data having
        total cost < copayment(year) will be excluded. This improves
        consistency for entries that are issued after April 2012. This only
        holds for General Beneficiaries.

    n_jobs: integer
        The number of processes that have asyncronous access to the input file.

    Returns:
    --------------
    out: dictionary
        Dictionary of dictionaries as in the following example.
        E.g.: `{'PBS_SAMPLE_10PCT_2012.csv': {3928691704: pd.DataFrame(), ...}}`
        each DataFrame has
    """
    # Load the drugs used in diabetes list file
    _dd = pd.read_csv(os.path.join(home[0], 'data', 'drugs_used_in_diabetes.csv'),
                      header=0)

    # Fix 6-digit notation
    dd = set()  # dd should be a set for performance reasons
    for item in _dd.values.ravel():
        if len(item) < 6:
            dd.add(str(0)+item)
        else:
            dd.add(item)

    # Load the Co-payments thresholds
    if filter_copayments:
        co_payments = pd.read_csv(os.path.join(home[0], 'data', 'co-payments_08-18.csv'),
                                  header=0, index_col=0, usecols=['DOC', 'GBC'])

    # Load the PBS data in a global variable
    # but keep only the rows relevant with diabete
    global ___PBS_FILES_DICT__
    for pbs in tqdm(pbs_files, desc='PBS files loading'):
        pbs_dd = pd.read_csv(pbs, header=0, engine='c',
                             usecols=['ITM_CD', 'PTNT_ID', 'SPPLY_DT',
                                      'PTNT_CNTRBTN_AMT', 'BNFT_AMT'])
        ___PBS_FILES_DICT__[pbs] = pbs_dd[pbs_dd['ITM_CD'].isin(dd)]

    # Itereate on the pbs files and get the index of the individuals that
    # were prescribed to diabes drugs
    out = dict()
    for pbs in tqdm(sorted(pbs_files), desc="PBS files processing"):
        _pbs = os.path.split(pbs)[-1]  # more visually appealing

        if filter_copayments:  # Select the appropriate co-payment threshold
            year = int(_pbs.split('_')[-1].split('.')[0])
            co_payment = co_payments.loc[year]['GBC']
        else:
            co_payment = None

        out[_pbs] = find_diabetes_drugs_users(pbs, co_payment=co_payment,
                                              n_jobs=n_jobs)

    return out


def find_diabetes_drugs_users(pbs, co_payment=None, n_jobs=1):
    """Find the diabetes drugs user from a single PBS file.

    This function supports parallel asyncronous access to the input
    file.

    Parameters:
    --------------
    pbs: string
        PBS file name.

    co_payment: numeric (default=None)
        The Co-payment threshold of the current year.
        Source: [http://www.pbs.gov.au/info/healthpro/explanatory-notes/front/fee]

    n_jobs: integer
        The number of processes that have asyncronous access to the input file.

    Returns:
    --------------
    results: dictionary
        The dictionary of unique patients identifiers that were prescribed to
        dibates drugs in the input pbs file. The dictionary has PTNT_ID as index
        and [SPPLY_DT, ITM_CD] as values.
    """
    manager = Manager()
    results = manager.dict()
    pool = mp.Pool(n_jobs)  # Use n_jobs processes

    # Get the list of UNIQUE patient id
    ptnt_ids = np.unique(___PBS_FILES_DICT__[pbs]['PTNT_ID'].values.ravel())
    pin_splits = np.array_split(ptnt_ids, n_jobs)  # PTNT_ID splits

    # Submit async jobs
    jobs = [pool.apply_async(worker, (i, pbs, pin_splits[i], results, co_payment)) for i in range(len(pin_splits))]

    # Collect jobs
    jobs = [p.get() for p in jobs]

    return dict(results)


def worker(i, pbs, split, results, co_payment):
    """Load the info of a given subject id.

    When co_payment is not None, PBS items costing less than co_payments are
    filtered out.
    """
    progress = tqdm(
        total=len(split),
        position=i+1,
        desc="Processing split-{}".format(i),
        leave=False
    )

    # Select only the items of the given user
    curr_pbs = ___PBS_FILES_DICT__[pbs]

    for k, pin in enumerate(split):
        if k % 5 == 0: progress.update(5)  # update each 100 iter

        # Get the rows corresponding to the current pin
        chunk = curr_pbs.loc[curr_pbs['PTNT_ID'] == pin, :]

        # Filter for co-payment if needed
        if co_payment is not None:
            chunk = chunk[chunk['PTNT_CNTRBTN_AMT']+chunk['BNFT_AMT'] >= co_payment]

        # If the current patient is actually diabetic in the current year
        if len(chunk) > 0:
            # save the corresponding info in a way that
            # the dictionary result has 'PTNT_ID' as index and
            # {'SPPLY_DT': [...], 'ITM_CD': [...]} as values
            out = chunk[['SPPLY_DT', 'ITM_CD']]
            results[pin] = {'SPPLY_DT': out['SPPLY_DT'].values.ravel().tolist(),
                            'ITM_CD': out['ITM_CD'].values.ravel().tolist()}
