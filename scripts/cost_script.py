#!/usr/bin/env python3

"""
Converts costs TSV file to summary costs TSV file

Usage: cost_script.py [costs tsv file]
"""
#Import modules
import sys
import pandas as pd
import regex as re

file=sys.argv[1]

#initialize list called table where we'll store all the values from tsv
table = []
with open(file) as f:
    for line in f:
        L = line.split('\t') #split by tab
        table.append(L)

#delete anything that resembles 'shard' followed by a number. If there's a 3-digit shard at some point, add a re.sub(\d\d\d) line before the re.sub(\d\d) line.
#have to go in descending order of numerical digits because otherwise will delete shard# and be left with name-of-task# which won't get deleted.
for i in table:
    if "shard" in i[0]:
        if "retry" in i[0]:
#            print("retry",i[0])
            i[0] = re.sub('_shard-\d\d','',i[0])
            i[0] = re.sub('_shard-\d','',i[0])
#            print(i[0])
        else:
#            print("no retry",i[0])
            i[0] = re.sub('_shard-\d\d','',i[0])
            i[0] = re.sub('_shard-\d','',i[0])
#            print(i[0])


#convert list of lists to pandas dataframe using first list item as header. Grab specific columns we want. Drop the first row because it's just the list of column names
table_df = pd.DataFrame(table, columns=table[0])
table_df = table_df[["callName","totalCost","cpuCost","memoryCost","diskCost"]]
table_df=table_df.drop([0])

#convert all numerical values from strings to floats
table_df = table_df.astype({'totalCost':'float','cpuCost':'float','memoryCost':'float','diskCost':'float'})

#sum all rows with same callname
table_df_sum = table_df.groupby("callName").sum()

#sort by descending order of total cost
table_df_sum=table_df_sum.sort_values(by=['totalCost'], ascending=False)

#save to csv
table_df_sum.to_csv('costs_report_final.csv', index=True)