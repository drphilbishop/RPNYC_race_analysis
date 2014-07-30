# functions.py
#
# A collection of functions to be used in Phil's notebooks for
# handicapping and analysis of RPNYC yacht racing.

import pandas as pd
import numpy as np
import datetime as dt
import os
import re


# Read selected columns from raw CSV file and make boat name the index
def input_csv(path,filename,CSVcolNums,CSVcolHdrs):
    raw_data = pd.read_csv(path + filename, sep=',', header=None, usecols=CSVcolNums)
    raw_data.columns = CSVcolHdrs
    raw_data = raw_data.set_index('Boat name')
    return raw_data


# Convert elapsed time (hh:mm:ss or mm:ss or <xxx>) to seconds as an integer
def et2seconds(x):
    if '<' in x:
        return np.nan    # np.nan is preferable to 'NaN', NaN, or 0
    else:
        if len(x) > 5:
            hours = int(x.split(':')[0])
            minutes = int(x.split(':')[1])
            seconds = int(x.split(':')[2])
            return seconds + minutes*60 + hours*60*60
        else:
            minutes = int(x.split(':')[0])
            seconds = int(x.split(':')[1])
            return seconds + minutes*60


# Extract division from Stuff field
def get_division(x):
    if 'Division' in x:
        return x.split('Division')[1].replace(' ','')[0]  # assumes returned value is a single character - will fail if div is not, 1, 2, 3, A, B, etc
    else:
        if 'Open, start' in x:
            return x.split(', start')[0]
        else:
            if 'Classics, start' in x:
                return x.split(', start')[0]
            else:
                return 'Combined'
            

# Compute corrected seconds
def corrSecs(x):
    if '<' in x['Elapsed time']:
        return np.nan
    else:
        return int(x['TCF'] * x['ETsecs'])


# Determine the reference boat and time as per Yotsys, i.e. boat with median corrected time or nearest boat
# quicker than the median corrected time
def ref_boat(df):
    x = df.corrSecs.dropna()                  # x is a series formed by extracting the corrSecs column from df
    x.sort()                                  # Ensure series x is sorted in order of ascending corrected seconds, corrSecs
    m = x.median()                            # m is the median value from x  
    if (x==m).sum()==0:                       # (x==m) returns a boolean; the sum equals zero if no boat's time is the median
        refboat = x[x < m].tail(1).index[0]   # Let the last boat from those boats above the median be the reference boat
        reftime = int(x[x < m].tail(1).sum()) # Let the corrected time of the reference boat be the reference time 
    else:
        refboat = x[x==m].index[0]            # Let median boat be the reference boat
        reftime = m                           # Let the corrected time of the reference boat (also the median time) be the reference time
    return refboat, reftime


# Compute the sailed-to handicap for this race
def TCFst(x):
    if x['corrSecs'] == 'NaN':
        return np.nan
    else:
        return round( (float(x['TCF']) * float(x['refTime']) / float(x['corrSecs'])), 3)


# Compute percentage movement in TCF, i.e. sailed to versus current TCF. Use my ST calc (TCFst) coz YotSys gets it wrong)    
def pctMvmt(x):
    if x['TCFst'] == 'NaN':
        return np.nan
    else:
        return round( float(100 * (x['TCFst'] - x['TCF']) / x['TCF']), 2)


# Compute clamped sailed-to handicap 
def TCFclmp(x, loClamp = .03, upClamp = .03):
    #print x
    # case where boat is the reference boat or the boat was never scored
    if (x['corrSecs'] == x['refTime']) or (x['corrSecs'] == 'Nan'):
        return x['TCF']
    # case where boat is better than reference boat
    if x['corrSecs'] < x['refTime']:
        if abs(x['TCFst'] - x['TCF']) / x['TCF'] > upClamp:
           return round(((1 + upClamp) * x['TCF']), 3)
        else:
           return x['TCFst']
    # case where boat is worse than reference boat
    if x['corrSecs'] > x['refTime']:
        if abs(x['TCFst'] - x['TCF']) / x['TCF'] > loClamp:
           return round(((1 - loClamp) * x['TCF']), 3)
        else:
           return x['TCFst']
   
