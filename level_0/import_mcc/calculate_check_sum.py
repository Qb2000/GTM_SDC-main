# -*- coding: utf-8 -*-
"""
Created on Fri Jan  2 02:17:47 2026

@author: 2000
"""
cfg_new={'step_1':[],'step_2':[],'step_3':[],'step_4':[],'M_CTR_A_new':[],'M_CTR_B_new':[],'S_CTR_A_new':[],'S_CTR_B_new':[]} 

# with open(r'C:\Users\2000\Downloads\0 V1\NEW\BUS_A_NEW\Ground Commands\GTM_PROC250623_00_ON.prc', 'r') as f: 
with open(r'C:\Users\2000\Desktop\master\GTM_repository\GTM_SDC-main\level_0\import_mcc\new_prc_HV setting - 4\GTM_PROC250101_00_ON.prc', 'r') as f: 
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

check_sum = []

def calculate_check_sum(data):
    data_as_ints = [int(x, 16) for x in data]
    summation = sum(data_as_ints)
    return hex(summation%256)

for i in range(len(cfg_new)):
    check_sum.append(calculate_check_sum(cfg_new[list(cfg_new.keys())[i]][3:-3]))


#%%final check

for index, value in enumerate(check_sum):
    print(f'calculation: {value}')
    print(f'check in prc file: {cfg_new[list(cfg_new.keys())[index]][-3]}')
    print(value == cfg_new[list(cfg_new.keys())[index]][-3])










