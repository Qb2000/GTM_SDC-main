# -*- coding: utf-8 -*-
"""
Created on Fri Dec 26 13:50:07 2025

@author: 2000
"""


import pandas as pd

cfg_new={'M_CTR_A_new':[],'M_CTR_B_new':[],'S_CTR_A_new':[],'S_CTR_B_new':[]} 


with open('GTM_PROC250101_00_ON.prc', 'r') as f: 
    lines = f.readlines() # 直接把所有行變成 
    counter = 0 
    rev_lines = list(reversed(lines))
    for i,line in enumerate(rev_lines): 
        if line.split() and line.split()[0]=='GTM_CFG': 
            counter += 1 
            for j in range(13): 
                for x in rev_lines[i-j].split():
                    if x != '\\':
                        cfg_new[list(cfg_new.keys())[-counter]].append(x) 
        if counter>=4: 
            break
                    

    
        
cfg_old={'M_CTR_A_old':[],'M_CTR_B_old':[],'S_CTR_A_old':[],'S_CTR_B_old':[]}         
with open('GTM_PROC250626_00_ON.prc', 'r') as f: 
    lines = f.readlines() # 直接把所有行變成 
    counter = 0 
    rev_lines = list(reversed(lines))
    for i,line in enumerate(rev_lines): 
        if line.split() and line.split()[0]=='GTM_CFG': 
            counter += 1 
            for j in range(13): 
                for x in rev_lines[i-j].split():
                    if x != '\\':
                        cfg_old[list(cfg_old.keys())[-counter]].append(x) 
        if counter>=4: 
            break 

def compare(cfg_a, cfg_b):
    diff = []
    for i in range(len(cfg_a)):
        if cfg_a[i]==cfg_b[i]:
            diff.append(None)
        else:
            diff.append('changed')
    return diff



with pd.ExcelWriter("compare.xlsx", engine="openpyxl") as writer:
    for i in range(len(cfg_old)):
        diff = compare(cfg_new[list(cfg_new.keys())[i]], cfg_old[list(cfg_old.keys())[i]])
        df_old = pd.DataFrame(cfg_old[list(cfg_old.keys())[i]], columns=['old'])
        df_new = pd.DataFrame(cfg_new[list(cfg_new.keys())[i]], columns=['new'])
        df_diff = pd.DataFrame(diff, columns=['diff'])  
        final_result_df = pd.concat([df_old, df_new, df_diff], axis=1)
        final_result_df = final_result_df.rename(columns=({0:'old',0:'new'}))
        final_result_df.to_excel(writer, sheet_name=list(cfg_old.keys())[i][:-4], index=False)
        
    
        
# with open('HEX1_M2_HV55_GAIN20_280.txt', 'r') as f:
#     lines = f.readlines()  # 直接把所有行變成 list
#     for i,line in enumerate(lines):
#         if int(line[0:2]) in range(44,76):
#             # print(line[3:5])
#             jason.append(line[3:5])
# with open('HEX1_S1_HV55_GAIN20_280.txt', 'r') as f:
#     lines = f.readlines()  # 直接把所有行變成 list
#     for i,line in enumerate(lines):
#         if int(line[0:2]) in range(44,76):
#             # print(line[3:5])
#             jason.append(line[3:5])
            
# with open('HEX1_S2_HV55_GAIN20_280.txt', 'r') as f:
#     lines = f.readlines()  # 直接把所有行變成 list
#     for i,line in enumerate(lines):
#         if int(line[0:2]) in range(44,76):
#             # print(line[3:5])
#             jason.append(line[3:5])