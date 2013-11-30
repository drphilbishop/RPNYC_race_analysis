# functions.py
#
# A collection of functions to be used in Phil's notebooks for
# handicapping and analysis of RPNYC yacht racing.

import pandas as pd
import numpy as np
import datetime as dt
import math
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
            

# Compute TCFactual - what the TCF should have been on the day. It might be different to the TCF applied on the day.
def TCFactual(df):      
    key = (df['Boat name'],index[1])                  
    if math.isnan(df['TCFapplied']) == False and '<' not in df['Elapsed time']:
        if not newTCFvalue[key]:                       # If newTCFvalue dictionary is empty, this boat hasn't yet had a race for this handicap. So return TCFapplied as TCFactual
            newTCFvalue[key].append(df['TCFapplied'])
        return round(newTCFvalue[key][len(newTCFvalue[key])-1], 3)  # Return the value of the last item, which is always the previous 'newTCF'  
    else:
        return np.nan                                       # Return nan for TCFactual     


# Compute corrected seconds
def corrSecs(df):    
    if '<' in df['Elapsed time'] or math.isnan(df['TCFactual']):
        return np.nan
    else:
        return int(df['TCFactual'] * df['ETsecs']) 

    
# Determine the reference boat and time as per method E, i.e. boat with median
# corrected time or nearest boat quicker than the median corrected time
def ref_boat(df):
    x = df.corrSecs.dropna()                  # x is a series formed by extracting the corrSecs column from df
    x.sort()                                  # Ensure series x is sorted in order of ascending corrected seconds, corrSecs
    m = x.median()  
    if (x==m).sum()==0:                       # (x==m) returns a boolean; the sum equals zero if no boat's time is the median
        refboat = x[x < m].tail(1).index[0]   # Let the last boat from those boats above the median be the reference boat
        reftime = int(x[x < m].tail(1).sum()) # Let the corrected time of the reference boat be the reference time 
    else:
        refboat = x[x==m].index[0]            # Let median boat be the reference boat
        reftime = m                           # Let the corrected time of the reference boat (also the median time) be the reference time
    return reftime
#   return refboat, reftime


# Adjust refTime
def adjustRefTime(df):
    if math.isnan(df['ETsecs']):
        return np.nan
    else:
        return df['refTime']


# Compute the sailed-to handicap for this race
def TCFst(x):
    if x['corrSecs'] == 'NaN':
        return np.nan
    else:
        return round( (float(x['TCFactual']) * float(x['refTime']) / float(x['corrSecs'])), 3)


# Compute percentage movement in TCF, i.e. sailed-to TCF versus actual TCF, i.e. TCFactual.
def pctMvmt(x):
    if x['TCFst'] == 'NaN':
        return np.nan
    else:
        return round( float(100 * (x['TCFst'] - x['TCFactual']) / x['TCFactual']), 2)


# Compute clamped sailed-to TCF, TCFclmp
def TCFclmp(x, loClamp = .03, upClamp = .03):
    #print x
    # case where boat is the reference boat or the boat was never scored
    if (x['corrSecs'] == x['refTime']) or (x['corrSecs'] == 'Nan'):        
        return x['TCFactual']
    # case where boat is better than reference boat
    if x['corrSecs'] < x['refTime']:
        if abs(x['TCFst'] - x['TCFactual']) / x['TCFactual'] > upClamp:            
            return round(((1 + upClamp) * x['TCFactual']), 3)
        else:
            return x['TCFst']
    # case where boat is worse than reference boat
    if x['corrSecs'] > x['refTime']:
        if abs(x['TCFst'] - x['TCFactual']) / x['TCFactual'] > loClamp:            
            return round(((1 - loClamp) * x['TCFactual']), 3)
        else:    
            return x['TCFst']


# Compute
def updateTcfClampAndSeed(df,numSeeds=2,numFinish=4,pctFinished=0.5):
    key = (df['Boat name'],index[1])           # Construct a key from boat name
    # If tcfClampHistoryAndSeeds[key] is empty (meaning hasnt raced before), add seeds. 
    percentFinished =  len(race.dropna(subset=['ETsecs']))/len(race)
    if '<' not in df['Elapsed time'] and len(race.dropna(subset=['ETsecs'])) >= numFinish and percentFinished >= pctFinished:
        if not TCFclampHistoryAndSeeds[key]:       
            seedValue = df['TCFactual']            # Get seed value from TCFactual
            if math.isnan(seedValue) == False:     # Make sure TCFactual is not a nan, or else do not add anything.
                for i in range(0,numSeeds):        # Loop through 0 to numSeeds, appending a seed to the list each time
                    TCFclampHistoryAndSeeds[key].append(seedValue)     
        # Now update the TCFclamp value from this race to the dictionary    
        # Update TCFclamp value
        if TCFclampHistoryAndSeeds[key]:         # If tcfClampHistoryAndSeeds[key] is not empty append the TCFclmp value
            TCFclampHistoryAndSeeds[key].append(df['TCFclmp'])
        else: #Otherwise do nothing at all
            pass


# Compute
def updateTcfClampAndSeed(df,numSeeds=2,pctFinished=0.5):
    key = (df['Boat name'],index[1])           # Construct a key from boat name
    # If tcfClampHistoryAndSeeds[key] is empty (meaning hasnt raced before), add seeds. 
    percentFinished =  len(race.dropna(subset=['ETsecs']))/len(race)
    if '<' not in df['Elapsed time'] and len(race.dropna(subset=['ETsecs'])) >= 4 and percentFinished >= 0.5:
        if not TCFclampHistoryAndSeeds[key]:       
            seedValue = df['TCFactual']            # Get seed value from TCFactual
            if math.isnan(seedValue) == False:     # Make sure TCFactual is not a nan, or else do not add anything.
                for i in range(0,numSeeds):        # Loop through 0 to numSeeds, appending a seed to the list each time
                    TCFclampHistoryAndSeeds[key].append(seedValue)     
        # Now update the TCFclamp value from this race to the dictionary    
        # Update TCFclamp value
        if TCFclampHistoryAndSeeds[key]:         # If tcfClampHistoryAndSeeds[key] is not empty append the TCFclmp value
            TCFclampHistoryAndSeeds[key].append(df['TCFclmp'])
        else: #Otherwise do nothing at all
            pass


            

# Compute newTCF - the TCF calculated after this race to apply for the next race
def newTCF(df,numFinish=4,pctFinished=0.5):
    key = (df['Boat name'],index[1])                      # Construct a key from boat name and handicap type
    values=TCFclampHistoryAndSeeds[key]                   # Get list of seeds and previous TFCclamp values
    percentFinished =  len(race.dropna(subset=['ETsecs']))/len(race)
    # If there are 4 or more finishers in this race, compute the newTCF
    if '<' not in df['Elapsed time'] and len(race.dropna(subset=['ETsecs'])) >= numFinish and percentFinished >= pctFinished:
        numValuesUsed = min(len(values)-1,4)              # Get the number of seed and TCFclamp values to be used in the formula
        fromIdx=max(0,len(values)-5)                      # Get the index to start summing from, will be either 0 or the len(values)-5 index depending which is larger
        sumTCFclmps = sum(values[fromIdx:len(values)-1])  # Calculate sum of values fromIdx to len(values)-1 (we sum up to second to last because we do not include this race's TCFclmp)   
        newTCF = (sumTCFclmps + df['TCFactual'])/(numValuesUsed+1) # Calculate the newTCF. Here we add the TCFactual from this race to sumTCFclmps and divide by (numValuesUsed+1)    
        newTCFvalue[key].append(newTCF)                   # Append newTCF to newTCFvalue dictionary        
        #DEBUGGING
        #print 'Boat and handicap', key, index
        #print 'TCFapplied', df['TCFapplied']
        #print 'TCFactual', df['TCFactual']
        #print 'Seeds + TCFclamp history',values
        #print 'Formula = average ( seeds clamps combination + TCFactual )',sumTCFclmps,'+',df['TCFactual'],'/',numValuesUsed+1
        #print 'newTCF',round(newTCF,3)        
        #print '----------------------------------------------'        
        return round(newTCF, 3)
    else:                                                 # If less than 4 finishers in this race
        return df['TCFactual']                            # newTCF remains the same the TCFactual    
