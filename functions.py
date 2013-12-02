from __future__ import division
import pandas as pd
import math
import datetime as dt
import numpy as np

# Compute TCFactual - what the TCF should have been on the day. It might be different to the TCF applied on the day.
def TCFactual(df,indexKey=None,newTCFvalue=None): 
    key = (df['Boat name'],indexKey)                                # Get the boat - handicap key
    if math.isnan(df['TCFapplied']) == False and '<' not in df['Elapsed time']:
        if not newTCFvalue[key]:                                    # If newTCFvalue[key] is empty, this boat hasn't yet had a race for this handicap.
            newTCFvalue[key].append(df['TCFapplied'])               # Append TCFapplied as TCFactual to newTCFvalue[key]
        return round(newTCFvalue[key][len(newTCFvalue[key])-1], 3)  # Return the value of the last item, which will always be the newTCF for the next race
    else:
        return np.nan                                               # Return nan for TCFactual if boat didn't race this day     

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


# Compute clamped sailed-to TCF, i.e. TCFclmp
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
def updateTCFclampAndSeed(df,numSeeds=2,numFinished=4,pctFinished=0.5,race=None,indexKey=None,TCFclampHistoryAndSeeds=None):
    key = (df['Boat name'],indexKey)               # Construct a key from boat name
    # If tcfClampHistoryAndSeeds[key] is empty (meaning hasnt raced before), add seeds. 
    percentFinished =  len(race.dropna(subset=['ETsecs']))/len(race)
    if '<' not in df['Elapsed time'] and len(race.dropna(subset=['ETsecs'])) >= numFinished and percentFinished >= pctFinished:
        if not TCFclampHistoryAndSeeds[key]:       
            seedValue = df['TCFactual']            # Get seed value from TCFactual
            if math.isnan(seedValue) == False:     # Make sure TCFactual is not a nan, or else do not add anything.
                for i in range(0,numSeeds):        # Loop through 0 to numSeeds, appending a seed to the list each time
                    TCFclampHistoryAndSeeds[key].append(seedValue)     
        # Now update the TCFclamp value from this race to the dictionary    
        # Update TCFclamp value
        if TCFclampHistoryAndSeeds[key]:           # If tcfClampHistoryAndSeeds[key] is not empty append the TCFclmp value
            TCFclampHistoryAndSeeds[key].append(df['TCFclmp'])
        else:                                      # Otherwise do nothing
            pass


# Compute newTCF - the TCF calculated after this race to apply for the next race
def newTCF(df,numFinished=4,pctFinished=0.5,numPastPerfs=4,race=None,indexKey=None,TCFclampHistoryAndSeeds=None,newTCFvalue=None): 
    #numFinished is the minimum number of finishers required to finish a race
    #pctFinished is the percentage of boats in a fleet required to finish a race
    #numPastPerfs is the total number of values used in the newTCF calculation. Includes this races actualTCF and TCFclamp history of last 4 races, using seeds if less than 4 previous races exist
    key = (df['Boat name'],indexKey)                      # Construct a key from boat name and handicap type
    values=TCFclampHistoryAndSeeds[key]                   # Get list of seeds and previous TFCclamp values
    percentFinished =  len(race.dropna(subset=['ETsecs']))/len(race)
    # If there are 4 or more finishers in this race, compute the newTCF
    if '<' not in df['Elapsed time'] and len(race.dropna(subset=['ETsecs'])) >= numFinished and percentFinished >= pctFinished:
        numValuesUsed = min(len(values)+1,numPastPerfs+1)              # Get the number of seed and TCFclamp values to be used in the formula
        fromIdx=max(0,len(values)-numPastPerfs)                      # Get the index to start summing from, will be either 0 or the len(values)-5 index depending which is larger
        sumTCFclmps = sum(values[fromIdx:len(values)])  # Calculate sum of values fromIdx to len(values)-1 (we sum up to second to last because we do not include this race's TCFclmp)   
        newTCF = (sumTCFclmps + df['TCFactual'])/numValuesUsed # Calculate the newTCF. Here we add the TCFactual from this race to sumTCFclmps and divide by (numValuesUsed+1)    
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

    
def TCFdiff(df):
    if df['newTCF'] == 'NaN':
        return np.nan
    else:
        return round(float(df['TCFapplied'] - df['TCFactual']), 3)
        