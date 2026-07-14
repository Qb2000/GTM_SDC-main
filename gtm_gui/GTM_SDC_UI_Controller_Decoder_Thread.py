#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 27 14:58:23 2022

@author: jasonpbu
"""

# Ref: https://shengyu7697.github.io/python-pyqt-qthread/

import os
import time
import numpy as np
import pandas as pd
from itertools import product
from datetime import datetime, timedelta, timezone

from PyQt5.QtCore import QThread, pyqtSignal

from GTM_SDC_UI_Controller_Decoder_Thread_C import c_decoder

class UiDecoderThread(QThread):

    # Create pyqt signal
    decoder_thread_open_tmtc_signal = pyqtSignal()
    decoder_thread_open_science_signal = pyqtSignal()
    decoder_thread_clear_layout_signal = pyqtSignal()
    decoder_thread_file_signal = pyqtSignal(list)
    decoder_thread_update_count_signal = pyqtSignal(int)
    decoder_thread_plot_tmtc_signal = pyqtSignal(list)
    decoder_thread_update_tmtc_signal = pyqtSignal(list)
    decoder_thread_plot_update_science_hg_signal = pyqtSignal(list)
    decoder_thread_plot_update_science_lg_signal = pyqtSignal(list)
    decoder_thread_plot_update_science_hg_lg_combine_signal = pyqtSignal(list)
    decoder_thread_plot_master_sync = pyqtSignal(list)
    decoder_thread_plot_slave_sync = pyqtSignal(list)
    decoder_thread_plot_light_curve =  pyqtSignal(list)
    decoder_thread_finish_signal = pyqtSignal()

    def __init__(self, parent):
        
        # Run __init__() in parent class
        # Here is for QThread
        super().__init__() # in python3, super(Class, self).xxx = super().xxx

        # Import useful info in MainWindowController, mainly parent.ui
        self.parent = parent

        # self.gtm_final_df_data = None
        # self.gtm_ref_df = None


        
    
    # Make thread happend in QThread!
    def run(self):
        self.decoder_start()

    ### decoder_start ###

    def decoder_start(self):

        # Get number of input file
        self.decoder_cached_input_file_number = len(self.parent.decoder_cached_input_file_list)
        
        if (not self.parent.ui.decoder_real_time_display_on_check_box.isChecked()) or \
        self.parent.ui.decoder_science_export_raw_radio_button.isChecked(): # only decode

            # Loop all file
            for decoder_cached_input_file_idx, decoder_cached_input_file in enumerate(self.parent.decoder_cached_input_file_list):

                # Initailize output file
                self.decoder_initailize_output_file(decoder_cached_input_file)

                # Run decoder in c
                _ = c_decoder(decoder_cached_input_file,
                              self.parent.in_space_flag,
                              self.parent.decode_mode, 
                              self.parent.export_mode, 
                              initail_file_pointer=0)

                
                # Print progress
                print(f'Finished/Total: {decoder_cached_input_file_idx+1} / {self.decoder_cached_input_file_number}')

                # Emit siganl back to parent class
                self.decoder_thread_finish_signal.emit()

        else: # decode and plot

            # Define fixed plotting variable
            self.decoder_plot_low_gain  = 2
            self.decoder_plot_high_gain = 20
            self.decoder_plot_bin_size  = 5
            self.decoder_plot_range_min  = -1000
            self.decoder_plot_range_max  = 2**14

            # Decode and plot
            self.decoder_plot()

            # Emit siganl back to parent class
            self.decoder_thread_finish_signal.emit()

    def decoder_initailize_output_file(self, filename):

        if self.parent.decode_mode == 1: # tmtc
            if os.path.exists(f'{filename}_tmtc_all.csv'):
                os.remove(f'{filename}_tmtc_all.csv')
            if os.path.exists(f'{filename}_tmtc_master.csv'):
                os.remove(f'{filename}_tmtc_master.csv')
            if os.path.exists(f'{filename}_tmtc_slave.csv'):
                os.remove(f'{filename}_tmtc_slave.csv')

        if (self.parent.decode_mode == 2) and ((self.parent.export_mode == 1) or (self.parent.export_mode == 3)): # science raw
            if os.path.exists(f'{filename}_science_raw.csv'):
                os.remove(f'{filename}_science_raw.csv')
        
        if (self.parent.decode_mode == 2) and ((self.parent.export_mode == 2) or (self.parent.export_mode == 3)): # science pipeline
            if os.path.exists(f'{filename}_science_pipeline.csv'):
                os.remove(f'{filename}_science_pipeline.csv')

    def decoder_initailize_plot_df_skip_number(self):

        # For tmtc
        self.decoder_plot_tmtc_master_df = pd.DataFrame()
        self.decoder_plot_tmtc_master_df_skip_number = 0
        self.decoder_plot_tmtc_slave_df = pd.DataFrame()
        self.decoder_plot_tmtc_slave_df_skip_number = 0

        # For science
        self.decoder_plot_science_df = pd.DataFrame()
        self.decoder_plot_science_df_skip_number = 0
        self.decoder_plot_science_grouped_df = pd.DataFrame()

    def decoder_plot(self):

        if self.parent.ui.decoder_data_import_tmtc_radio_button.isChecked(): # tmtc 

            # Emit siganl back to parent class
            self.decoder_thread_open_tmtc_signal.emit()
        
        else: # science

            # Emit siganl back to parent class
            self.decoder_thread_open_science_signal.emit()

        if (not self.parent.ui.decoder_update_time_group.isEnabled()): # only plot one time
            self.decoder_update_time_s = 0 # 0 == False

        else: 

            if self.parent.ui.decoder_update_time_combo_box.currentText() == 'None': # only plot one time
                self.decoder_update_time_s = 0 # 0 == False

            else: # plot continuously
                self.decoder_update_time_s = int(self.parent.ui.Update_Rate_comboBox.currentText())

        # Loop all file
        for decoder_cached_input_file_idx, decoder_cached_input_file in enumerate(self.parent.decoder_cached_input_file_list):
            
            self.filedir_filename_list = [os.path.dirname(decoder_cached_input_file), os.path.basename(decoder_cached_input_file)]
            # Store current file info for this iteration
            self.current_file_dirname = os.path.dirname(decoder_cached_input_file)
            self.current_file_basename = os.path.basename(decoder_cached_input_file)
            
            # Initailize output file
            self.decoder_initailize_output_file(decoder_cached_input_file)

            # Initialize changing plotting variable
            self.decoder_initailize_plot_df_skip_number()
            
            if self.parent.ui.decoder_auto_save_figure_group.isEnabled() and \
            self.parent.ui.decoder_auto_save_figure_on_check_box.isChecked(): # need auto-save figure

                # Emit siganl back to parent class
                self.decoder_thread_file_signal.emit([self.current_file_dirname, self.current_file_basename])

            else: # just display on screen
                pass

            # Run decoder in c
            new_file_pointer = c_decoder(decoder_cached_input_file,
                                         self.parent.in_space_flag,
                                         self.parent.decode_mode, 
                                         self.parent.export_mode, 
                                         initail_file_pointer=0)

            # Emit siganl back to parent class
            self.decoder_thread_clear_layout_signal.emit()

            if self.parent.ui.decoder_data_import_tmtc_radio_button.isChecked(): # tmtc 

                if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
                self.parent.ui.decoder_display_selection_slave_group.isChecked(): # master and slave

                    # Plot tmtc
                    self.decoder_plot_tmtc([f'{decoder_cached_input_file}_tmtc_master.csv', f'{decoder_cached_input_file}_tmtc_slave.csv'])
                
                elif self.parent.ui.decoder_display_selection_master_group.isChecked(): # only master

                    # Plot tmtc
                    self.decoder_plot_tmtc([f'{decoder_cached_input_file}_tmtc_master.csv'])
                
                else: # only slave

                    # Plot tmtc
                    self.decoder_plot_tmtc([f'{decoder_cached_input_file}_tmtc_slave.csv'])
            
            else: # science

                # Plot science
                self.decoder_plot_science([f'{decoder_cached_input_file}_science_pipeline.csv'])

            if self.decoder_update_time_s == 0: # only plot one time

                # Print progress
                print(f'Finished/Total: {decoder_cached_input_file_idx+1} / {self.decoder_cached_input_file_number}')
            
            else: # plot continuously

                # Initailize update counter for save fugure
                self.decoder_update_counter = 0

                # Loop until break
                while True:
                    
                    # Refresh update counter
                    self.decoder_update_counter += 1

                    # Emit siganl back to parent class
                    self.decoder_thread_update_count_signal.emit(self.decoder_update_counter)

                    # Cache new file pointer
                    new_file_pointer_cached = new_file_pointer

                    # Wait update time (s)
                    print(f'Wait {self.decoder_update_time_s} s...')
                    time.sleep(self.decoder_update_time_s)

                    # Run decoder in c
                    new_file_pointer = c_decoder(decoder_cached_input_file,
                                                 self.parent.in_space_flag,
                                                 self.parent.decode_mode, 
                                                 self.parent.export_mode, 
                                                 initail_file_pointer=new_file_pointer_cached)
                    
                    # Compare new file pointer
                    if new_file_pointer == new_file_pointer_cached:

                        # Print progress
                        print(f'Finished/Total: {decoder_cached_input_file_idx+1} / {self.decoder_cached_input_file_number}')

                        break

                    else:

                        if self.parent.ui.decoder_data_import_tmtc_radio_button.isChecked(): # tmtc 

                            if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
                            self.parent.ui.decoder_display_selection_slave_group.isChecked(): # master and slave

                                # Update plotted tmtc
                                self.decoder_update_plot_tmtc([f'{decoder_cached_input_file}_tmtc_master.csv', f'{decoder_cached_input_file}_tmtc_slave.csv'])
                            
                            elif self.parent.ui.decoder_display_selection_master_group.isChecked(): # only master

                                # Update plotted tmtc
                                self.decoder_update_plot_tmtc([f'{decoder_cached_input_file}_tmtc_master.csv'])
                            
                            else: # only slave

                                # Update plotted tmtc
                                self.decoder_update_plot_tmtc([f'{decoder_cached_input_file}_tmtc_slave.csv'])
                        
                        else: # science

                            # Update plotted science
                            self.decoder_update_plot_science([f'{decoder_cached_input_file}_science_pipeline.csv'])      

    def decoder_plot_tmtc(self, filename_list):

        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        self.parent.ui.decoder_display_selection_slave_group.isChecked(): # master and slave

            # Load df
            self.decoder_plot_tmtc_master_df, self.decoder_plot_tmtc_master_df_skip_number \
            = self.decoder_load_df(filename_list[0], self.decoder_plot_tmtc_master_df, self.decoder_plot_tmtc_master_df_skip_number)
            self.decoder_plot_tmtc_slave_df, self.decoder_plot_tmtc_slave_df_skip_number \
            = self.decoder_load_df(filename_list[1], self.decoder_plot_tmtc_slave_df, self.decoder_plot_tmtc_slave_df_skip_number)

            # Emit siganl back to parent class
            self.decoder_thread_plot_tmtc_signal.emit([self.decoder_plot_tmtc_master_df, self.decoder_plot_tmtc_slave_df])

        elif self.parent.ui.decoder_display_selection_master_group.isChecked(): # only master
            
            # Load df
            self.decoder_plot_tmtc_master_df, self.decoder_plot_tmtc_master_df_skip_number \
            = self.decoder_load_df(filename_list[0], self.decoder_plot_tmtc_master_df, self.decoder_plot_tmtc_master_df_skip_number)
            
            # Emit siganl back to parent class
            self.decoder_thread_plot_tmtc_signal.emit([self.decoder_plot_tmtc_master_df])

        else: # only slave
            
            # Load df
            self.decoder_plot_tmtc_slave_df, self.decoder_plot_tmtc_slave_df_skip_number \
            = self.decoder_load_df(filename_list[0], self.decoder_plot_tmtc_slave_df, self.decoder_plot_tmtc_slave_df_skip_number)
            
            # Emit siganl back to parent class
            self.decoder_thread_plot_tmtc_signal.emit([self.decoder_plot_tmtc_slave_df])

    def decoder_load_df(self, filename, df, skip_number):

        if df.empty: # without data
            df = pd.read_csv(filename, sep=';')
        
        else: # with data

            # Load new data
            df_new = pd.read_csv(filename, sep=';', skiprows=skip_number)
            
            # Add column from old data for concatenate
            df_new.columns = df.columns

            # Concatenate df
            df = pd.concat([df, df_new], axis=0, ignore_channel_idx=True)
        
        # Update skip number
        skip_number = df.shape[0]
        
        return df, skip_number

    def decoder_update_plot_tmtc(self, filename_list):

        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        self.parent.ui.decoder_display_selection_slave_group.isChecked(): # master and slave

            # Update df
            self.decoder_plot_tmtc_master_df, self.decoder_plot_tmtc_master_df_skip_number \
            = self.decoder_load_df(filename_list[0], self.decoder_plot_tmtc_master_df, self.decoder_plot_tmtc_master_df_skip_number)
            self.decoder_plot_tmtc_slave_df, self.decoder_plot_tmtc_slave_df_skip_number \
            = self.decoder_load_df(filename_list[1], self.decoder_plot_tmtc_slave_df, self.decoder_plot_tmtc_slave_df_skip_number)
            
            # Emit siganl back to parent class
            self.decoder_thread_update_tmtc_signal.emit([self.decoder_plot_tmtc_master_df, self.decoder_plot_tmtc_slave_df])
        
        elif self.parent.ui.decoder_display_selection_master_group.isChecked(): # only master

            # Update df
            self.decoder_plot_tmtc_master_df, self.decoder_plot_tmtc_master_df_skip_number \
            = self.decoder_load_df(filename_list[0], self.decoder_plot_tmtc_master_df, self.decoder_plot_tmtc_master_df_skip_number)
            
            # Emit siganl back to parent class
            self.decoder_thread_update_tmtc_signal.emit([self.decoder_plot_tmtc_master_df])

        else: # only slave

            # Update df
            self.decoder_plot_tmtc_slave_df, self.decoder_plot_tmtc_slave_df_skip_number \
            = self.decoder_load_df(filename_list[0], self.decoder_plot_tmtc_slave_df, self.decoder_plot_tmtc_slave_df_skip_number)
            
            # Emit siganl back to parent class
            self.decoder_thread_update_tmtc_signal.emit([self.decoder_plot_tmtc_slave_df])
    def decoder_plot_sync_data(self,orifinal_df):
        
        orifinal_df['Counts']=np.ones(len(orifinal_df))
        orifinal_df['convert to sec'] = orifinal_df['Day of Year']*86400+orifinal_df['Hour']*3600+orifinal_df['Minute']*60+orifinal_df['Second'] 
        self.decoder_plot_sync_grouped_df = orifinal_df.groupby(['GTM ID'])
           
        self.master_sync_data = self.decoder_plot_sync_grouped_df.get_group((0,))
        self.slave_sync_data = self.decoder_plot_sync_grouped_df.get_group((1,))
        # self.master_x_label = self.decoder_plot_sync_grouped_df.get_group((0,)).index
        # self.slave_x_label = self.decoder_plot_sync_grouped_df.get_group((1,)).index
        self.master_x_label = self.decoder_plot_sync_grouped_df.get_group((0,))['Day of Year'] + self.decoder_plot_sync_grouped_df.get_group((0,))['Hour']/24 + self.decoder_plot_sync_grouped_df.get_group((0,))['Minute']/1440 + self.decoder_plot_sync_grouped_df.get_group((0,))['Second']/86400
        self.slave_x_label = self.decoder_plot_sync_grouped_df.get_group((1,))['Day of Year'] + self.decoder_plot_sync_grouped_df.get_group((1,))['Hour']/24 + self.decoder_plot_sync_grouped_df.get_group((1,))['Minute']/1440 + self.decoder_plot_sync_grouped_df.get_group((1,))['Second']/86400
        self.light_curve_hist = orifinal_df.groupby(['GTM ID','PPS']).agg({'Counts':'count'})
        self.light_curve_hist_master = self.light_curve_hist.loc[0]
        self.light_curve_hist_slave = self.light_curve_hist.loc[1]
        self.light_curve_hist_master_index = self.light_curve_hist_master.index
        self.light_curve_hist_slave_index = self.light_curve_hist_slave.index
        
        self.decoder_thread_plot_master_sync.emit(['M',self.master_x_label.to_numpy(),
                                                    self.master_sync_data['Sequence Number'].to_numpy(),
                                                    self.master_sync_data['convert to sec'].to_numpy(),
                                                    self.master_sync_data['Temperature'].to_numpy(),
                                                    self.master_sync_data['PPS'].to_numpy(),
                                                    self.master_sync_data['X'].to_numpy(),
                                                    self.master_sync_data['Y'].to_numpy(),
                                                    self.master_sync_data['Z'].to_numpy(),
                                                    self.master_sync_data['Q1'].to_numpy(),
                                                    self.master_sync_data['Q2'].to_numpy(),
                                                    self.master_sync_data['Q3'].to_numpy(),
                                                    self.master_sync_data['Q4'].to_numpy(),
                                                    self.master_sync_data['Fine Time'].to_numpy(),
                                                    ])
        self.decoder_thread_plot_slave_sync.emit(['S',self.slave_x_label.to_numpy(),
                                                    self.slave_sync_data['Sequence Number'].to_numpy(),
                                                    self.slave_sync_data['convert to sec'].to_numpy(),
                                                    self.slave_sync_data['Temperature'].to_numpy(),
                                                    self.slave_sync_data['PPS'].to_numpy(),
                                                    self.slave_sync_data['X'].to_numpy(),
                                                    self.slave_sync_data['Y'].to_numpy(),
                                                    self.slave_sync_data['Z'].to_numpy(),
                                                    self.slave_sync_data['Q1'].to_numpy(),
                                                    self.slave_sync_data['Q2'].to_numpy(),
                                                    self.slave_sync_data['Q3'].to_numpy(),
                                                    self.slave_sync_data['Q4'].to_numpy(),
                                                    self.slave_sync_data['Fine Time'].to_numpy(),
                                                    ])
        self.decoder_thread_plot_light_curve.emit([np.array(self.light_curve_hist_master_index),
                                                   np.array(self.light_curve_hist_slave_index),
                                                    np.array(self.light_curve_hist_master['Counts']),
                                                    np.array(self.light_curve_hist_slave['Counts']),
                                                    ])


    def fix_pps_issue(self, df_grouped, time_precision_s=3.84E-6):
    
        # Extract fine time
        fine_time = df_grouped['Fine Time'].copy()
        
        # Calculate difference with previous row
        fine_time_diff = fine_time.diff()
        
        # Replace nan to 0 at first row
        fine_time_diff_remove_nan = fine_time_diff.fillna(0)
        
        # Find all return argument
        return_arg_array = np.argwhere(fine_time_diff_remove_nan.to_numpy() < 0)
        
        # Accumulate when encountering return argument
        for return_arg_idx, return_arg in enumerate(return_arg_array):
            
            # Define where start accumulating
            start_row = return_arg[0]
            
            # Define base value to accumulate
            base_add_row = return_arg[0]-1
            
            if return_arg_idx != len(return_arg_array)-1: # not yet final case
                
                # Define where stop accumulating
                end_row = return_arg_array[return_arg_idx+1][0]
                
                # Accumulate data
                fine_time.iloc[start_row:end_row] += fine_time.iloc[base_add_row]
            
            else: # final case
            
                # Accumulate data
                fine_time.iloc[start_row:] += fine_time.iloc[base_add_row]
        
        return fine_time * time_precision_s
    # def convert_doy_to_timestamp(self, year, doy, hour, minute, second):

    #     # 1. 將 DataFrame 中的欄位組合出可用於 pandas.to_datetime 解析的字串序列
    #     # 格式: "%Y-%j %H:%M:%S" (%j 代表 Day of Year)
    #     date_str_series = str(year) + '-' + doy.astype(str).str.zfill(3) + ' ' + \
    #                       hour.astype(str).str.zfill(2) + ':' + \
    #                       minute.astype(str).str.zfill(2) + ':' + \
    #                       second.astype(str).str.zfill(2)
        
    #     # 2. 將字串序列轉換為 datetime，並指定 UTC 時區
    #     dt_series = pd.to_datetime(date_str_series, format='%Y-%j %H:%M:%S', utc=True)
        
    #     # 3. 轉換為 Unix 時間戳 (秒)
    #     # dt_series.astype('int64') 預設會轉換為奈秒 (nanoseconds)，除以 10**9 轉換為秒
    #     return dt_series.astype('int64') // 10**9
    def simplify_label(self, df):
        sensor_name =  ['M1', 'M2', 'M3', 'M4', 'S1', 'S2', 'S3', 'S4']
        sensor_channel_shift = [16, 0, 16, 0, 16, 0, 16, 0]
        # Define condition
        condition_list = [
            (df['GTM ID'] == 0) & (df['CITIROC'] == 1) & (df['Channel'] >= 16) & (df['Channel'] <= 31),
            (df['GTM ID'] == 0) & (df['CITIROC'] == 1) & (df['Channel'] >= 0) & (df['Channel'] <= 15),
            (df['GTM ID'] == 0) & (df['CITIROC'] == 0) & (df['Channel'] >= 16) & (df['Channel'] <= 31),
            (df['GTM ID'] == 0) & (df['CITIROC'] == 0) & (df['Channel'] >= 0) & (df['Channel'] <= 15),
            (df['GTM ID'] == 1) & (df['CITIROC'] == 1) & (df['Channel'] >= 16) & (df['Channel'] <= 31),
            (df['GTM ID'] == 1) & (df['CITIROC'] == 1) & (df['Channel'] >= 0) & (df['Channel'] <= 15),
            (df['GTM ID'] == 1) & (df['CITIROC'] == 0) & (df['Channel'] >= 16) & (df['Channel'] <= 31),
            (df['GTM ID'] == 1) & (df['CITIROC'] == 0) & (df['Channel'] >= 0) & (df['Channel'] <= 15),
            ]
        
        # Select choice by condition
        df['Sensor Name'] = np.select(condition_list, sensor_name, default='Unknown')
        df['Sensor Channel Shift'] = np.select(condition_list, sensor_channel_shift)
        df['Sensor Channel'] = df['Channel'] - df['Sensor Channel Shift']
        
        return df
    def convert_day_to_timestamp(self, year, df):

        first_valid_index = (df[['Day of Year','Hour','Minute','Second']]!= 0).any(axis=1)
        minimun_utc = df[first_valid_index].iloc[0]
        
            
        base_date = datetime(year, 1, 1) \
                    + pd.to_timedelta(minimun_utc['Day of Year'].astype(int)-1, unit='d')\
                    + pd.to_timedelta(minimun_utc['Hour'].astype(int), unit='h')\
                    + pd.to_timedelta(minimun_utc['Minute'].astype(int), unit='m')\
                    + pd.to_timedelta(minimun_utc['Second'].astype(int), unit='s')

        df['utc'] = (
            base_date + pd.to_timedelta((df['PPS']-minimun_utc['PPS']).astype(int), unit='s')
        )
        df['Time Stamp'] = df['utc'].astype('int64') //10**9
        return df
    def concatenate_df(self, df_total, df_partial):
    
        if df_total.empty: # copy df_partial as df_total
            df_total = df_partial.copy()
        else: # concatenate df_partial into df_total
            df_total = pd.concat([df_total, df_partial], axis=0, ignore_index=True)
        
        return df_total

    def decoder_combine_hg_lg_data(self,orifinal_df, config_module, config_citiroc, channel_idx_channel_shift, Number_of_combine):    #01.py
        


        config_df = pd.DataFrame({'GTM ID': [int(config_module)], 'CITIROC': [int(config_citiroc)],'Channel':[int(channel_idx_channel_shift)]})
        # print(config_df)
        config_df = self.simplify_label(config_df)

        sensor_name_all = ['M1', 'M2', 'M3', 'M4', 'S1', 'S2', 'S3', 'S4']
        ctr2pix_mapping = [
            [11, 9, 3, 1 ,2 ,4 ,10 ,12 ,6 ,5 ,8 ,7 ,14 ,13 ,16 ,15], # sensor 1: 16~31
            [15, 13, 7, 5, 16, 14, 8, 6, 2, 1, 4, 3, 10, 9, 12, 11], # sensor 2: 0~15
            [11, 12, 9, 10, 3, 4, 1, 2, 6, 8, 14, 16, 5, 7, 13, 15], # sensor 3: 16~31
            [15, 16, 13, 14, 7, 8, 5, 6, 12, 10, 4, 2, 1, 3, 9, 11], # sensor 4: 0~15
            ]
        pix2position_mapping = [
            np.array([[1, 2, 5, 6],
                    [3, 4, 7, 8],
                    [9, 10, 13, 14],
                    [11, 12, 15, 16]]), # sensor 1: cable down
            np.array([[12 ,11, 16, 15],
                    [10, 9, 14, 13],
                    [4, 3, 8, 7],
                    [2, 1, 6, 5]]), # sensor 2: cable up
            np.array([[12 ,11, 16, 15],
                    [10, 9, 14, 13],
                    [4, 3, 8, 7],
                    [2, 1, 6, 5]]), # sensor 3: cable up
            np.array([[1, 2, 5, 6],
                    [3, 4, 7, 8],
                    [9, 10, 13, 14],
                    [11, 12, 15, 16]]), # sensor 4: cable down
            ]
         # Define size
        bin_size = 20 # ~ 1 keV
        plot_min = -1000
        plot_max = 11000

        if Number_of_combine < 1:

            ref_df = pd.DataFrame({'Sensor Name': [], 'Sensor Channel': [], 'Gain': [], 'Gain Ratio': [], 'Jump':[]})

            gtm_simplified_df = self.simplify_label(orifinal_df)
            gtm_simplified_df = self.convert_day_to_timestamp(2026, gtm_simplified_df)
            gtm_simplified_df = gtm_simplified_df.drop(columns=['Day of Year', 'Hour', 'Minute', 'Second', 'Subsecond', 
                    'X', 'Y','Z', 'Q1', 'Q2', 'Q3', 'Q4',
                    'CITIROC', 'Channel', 'Sensor Channel Shift']
            )
            
            # Group df for fixing time  
            gtm_grouped_1_df = gtm_simplified_df.groupby(['GTM ID'])
            gtm_fixed_temp_df = pd.DataFrame()
            for gtm_id_idx, gtm_id in enumerate(gtm_grouped_1_df.groups.keys()):
            
                # Extract data from certain module
                module_data = gtm_grouped_1_df.get_group((gtm_id,))
                
                # Calculate relative time only with fine time due to pps issue
                module_data.insert(0, 'Relative Time', self.fix_pps_issue(module_data).to_list())
                
                # Concatenate data
                gtm_fixed_temp_df = self.concatenate_df(gtm_fixed_temp_df, module_data)
            # Clean & rearrange df
            gtm_fixed_temp_df['Time Stamp'] = gtm_fixed_temp_df['Time Stamp'] + gtm_fixed_temp_df['Fine Time']*3.84e-6
            gtm_fixed_temp_df['Time Stamp'] = gtm_fixed_temp_df['Time Stamp']*1000 # sec turn into ms
            gtm_fixed_df = gtm_fixed_temp_df[['Relative Time', 'Sensor Name', 'Sensor Channel', 'Gain', 'ADC', 'Time Stamp']]

            # Group df for finding hg/lg ratio
            gtm_grouped_2_df = gtm_fixed_df.groupby(['Sensor Name', 'Sensor Channel', 'Gain'])
            
            sensor_name = sorted(np.unique(gtm_simplified_df['Sensor Name']))
            lg2hg_dict = {}
            for i in sensor_name:
                lg2hg_dict[f'{i}_hg/lg'] = []

            for sensor_idx, sensor in enumerate(sensor_name):
                
                # Loop all channels
                for channel in range(16):

                    # print(gtm_grouped_2_df.groups)
                    # Extract data
                    lg_data = gtm_grouped_2_df.get_group((sensor, channel, 0))
                    hg_data = gtm_grouped_2_df.get_group((sensor, channel, 1))
                    
                    # Bin lg to find jump
                    lg_hist, lg_bin_edges = np.histogram(lg_data['ADC'], 
                                                        bins=np.arange(plot_min, plot_max+bin_size, bin_size), 
                                                        density=False)
                    
                    # Find jump to know ratio
                    find_min_idx = np.argwhere(lg_bin_edges[:-1] == 600)[0][0] # 8192/12 ~ 682
                    find_max_idx = np.argwhere(lg_bin_edges[:-1] == 1100)[0][0] # 81492/8 ~ 1024
                    try: 
                        first_non0_idx = np.where(lg_hist[find_min_idx: find_max_idx] == 0)[0][-1] + 1 # last 0 idx + 1
                    except:
                        first_non0_idx = 0
                    diff = np.diff(lg_hist[find_min_idx+first_non0_idx: find_min_idx+first_non0_idx+5]) # diff of needed hist
                    diff_max_idx = np.argmax(diff) + 1 # add 1 because count from 0
                    lg_jump = lg_bin_edges[:-1][find_min_idx+first_non0_idx+diff_max_idx]
                    ratio = 8192/lg_jump
                    
                    # Save to dict
                    lg2hg_dict[f'{sensor}_hg/lg'].append(ratio)
                    
                    # Prepare ref_df
                    ref_df.loc[len(ref_df.index)] = [sensor, channel, 0, 1, lg_jump] # 0: lg
                    ref_df.loc[len(ref_df.index)] = [sensor, channel, 1, ratio, -1000] # 1: hg


            # Save dict to csv
            lg2hg_df = pd.DataFrame(lg2hg_dict) 
            lg2hg_df.to_csv(self.filedir_filename_list[0]+f'/{self.filedir_filename_list[1]}_{config_df["Sensor Name"].item()}_lg2hg.csv')
            
            # Merge low & high gain adc
            gtm_merged_df = pd.merge(gtm_fixed_df, ref_df)
            gtm_merged_df['Merged ADC'] = gtm_merged_df['ADC'] / gtm_merged_df['Gain Ratio']

            # Remove lg < lg_jump
            gtm_final_df = gtm_merged_df[gtm_merged_df['ADC'] >= gtm_merged_df['Jump']]
            gtm_final_df = gtm_final_df[['Relative Time', 'Sensor Name', 'Sensor Channel', 'Merged ADC', 'Time Stamp']]
            
            # Save df to pkl
            gtm_final_df.to_pickle(self.filedir_filename_list[0]+f'/{self.filedir_filename_list[1]}_lg2hg._origin.pkl')
            
            self.gtm_final_df_data = gtm_final_df.groupby(['Sensor Name', 'Sensor Channel'])
            # print(ref_df)
            self.gtm_ref_df = ref_df
            # self.gtm_final_df_data.groupby(['Sensor Name', 'Sensor Channel'])
            # Group df for finding hg/lg ratio
            # gtm_grouped_3_df = gtm_final_df.groupby(['Sensor Name', 'Sensor Channel'])
            # print(gtm_grouped_3_df.groups)
            # print((config_df['Sensor Name'][0], config_df['Sensor Channel'][0]))
            # data = gtm_grouped_3_df.get_group((config_df['Sensor Name'][0], config_df['Sensor Channel'][0]))
            
        
                                            
        
        
        # Map ctr to pixel to position
        sensor_idx = sensor_name_all.index(config_df['Sensor Name'][0])
        channel = config_df['Sensor Channel'][0]
        pixel = ctr2pix_mapping[sensor_idx % 4][channel]
        position = np.where(pix2position_mapping[sensor_idx % 4] == pixel)

        
        

        data = self.gtm_final_df_data.get_group((config_df['Sensor Name'][0], config_df['Sensor Channel'][0]))
        hist, bin_edges = np.histogram(data['Merged ADC'], 
                                            bins=np.arange(plot_min, plot_max+bin_size, bin_size), density=False)

        jump_pos = self.gtm_ref_df[(self.gtm_ref_df['Sensor Name'] == config_df['Sensor Name'][0]) &\
                                                        (self.gtm_ref_df['Sensor Channel'] == channel) &\
                                                        (self.gtm_ref_df['Gain'] == 0)]['Jump'].item()
        # Select ax
        ax_row = position[0][0]
        ax_column = position[1][0]
        # print(config_df['Sensor Name'])
        
        return hist, bin_edges, jump_pos, config_df['Sensor Name'].item(), config_df['Sensor Channel'].item(), [ax_row, ax_column]
 
        



    def decoder_plot_science(self, filename_list):
        # print('from decoder_plot_science'+filename_list[0])
        self.n_of_combine =0
        # Load df
        self.decoder_plot_science_df, self.decoder_plot_science_df_skip_number \
        = self.decoder_load_df(filename_list[0], self.decoder_plot_science_df, self.decoder_plot_science_df_skip_number)
        
        # Group df
        self.decoder_plot_science_grouped_df = self.decoder_plot_science_df.groupby(['GTM ID', 'CITIROC', 'Channel', 'Gain'])
        
        
        if self.parent.ui.decoder_plot_sync_on_check_box.isChecked():
            # print(self.decoder_plot_science_df)
            self.decoder_plot_sync_data(self.decoder_plot_science_df)
            
            
            
        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_master_s1_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_master_s2_check_box.isChecked()): # need to plot M1 and M2

            # Plot, show and save robotically
            self.decoder_plot_science_robotic(module='master',
                                              citiroc='b',
                                              channel_row=8,
                                              channel_column=4,
                                              channel_shift=0)

        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_master_s1_check_box.isChecked() and \
        not self.parent.ui.decoder_display_selection_master_s2_check_box.isChecked()): # only need to plot M1

            # Plot, show and save robotically
            self.decoder_plot_science_robotic(module='master',
                                              citiroc='b',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=16)
        
        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        (not self.parent.ui.decoder_display_selection_master_s1_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_master_s2_check_box.isChecked()): # only need to plot M2

            # Plot, show and save robotically
            self.decoder_plot_science_robotic(module='master',
                                              citiroc='b',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=0)

        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_master_s3_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_master_s4_check_box.isChecked()): # need to plot M3 and M4

            # Plot, show and save robotically
            self.decoder_plot_science_robotic(module='master',
                                              citiroc='a',
                                              channel_row=8,
                                              channel_column=4,
                                              channel_shift=0)

        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_master_s3_check_box.isChecked() and \
        not self.parent.ui.decoder_display_selection_master_s4_check_box.isChecked()): # only need to plot M3

            # Plot, show and save robotically
            self.decoder_plot_science_robotic(module='master',
                                              citiroc='a',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=16)
        
        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        (not self.parent.ui.decoder_display_selection_master_s3_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_master_s4_check_box.isChecked()): # only need to plot M4

            # Plot, show and save robotically
            self.decoder_plot_science_robotic(module='master',
                                              citiroc='a',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=0)
        
        if self.parent.ui.decoder_display_selection_slave_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_slave_s1_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_slave_s2_check_box.isChecked()): # need to plot S1 and S2

            # Plot, show and save robotically
            self.decoder_plot_science_robotic(module='slave',
                                              citiroc='b',
                                              channel_row=8,
                                              channel_column=4,
                                              channel_shift=0)

        if self.parent.ui.decoder_display_selection_slave_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_slave_s1_check_box.isChecked() and \
        not self.parent.ui.decoder_display_selection_slave_s2_check_box.isChecked()): # only need to plot S1

            # Plot, show and save robotically
            self.decoder_plot_science_robotic(module='slave',
                                              citiroc='b',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=16)
        
        if self.parent.ui.decoder_display_selection_slave_group.isChecked() and \
        (not self.parent.ui.decoder_display_selection_slave_s1_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_slave_s2_check_box.isChecked()): # only need to plot S2

            # Plot, show and save robotically
            self.decoder_plot_science_robotic(module='slave',
                                              citiroc='b',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=0)

        if self.parent.ui.decoder_display_selection_slave_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_slave_s3_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_slave_s4_check_box.isChecked()): # need to plot S3 and S4

            # Plot, show and save robotically
            self.decoder_plot_science_robotic(module='slave',
                                              citiroc='a',
                                              channel_row=8,
                                              channel_column=4,
                                              channel_shift=0)

        if self.parent.ui.decoder_display_selection_slave_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_slave_s3_check_box.isChecked() and \
        not self.parent.ui.decoder_display_selection_slave_s4_check_box.isChecked()): # only need to plot S3

            # Plot, show and save robotically
            self.decoder_plot_science_robotic(module='slave',
                                              citiroc='a',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=16)
        
        if self.parent.ui.decoder_display_selection_slave_group.isChecked() and \
        (not self.parent.ui.decoder_display_selection_slave_s3_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_slave_s4_check_box.isChecked()): # only need to plot S4

            # Plot, show and save robotically
            self.decoder_plot_science_robotic(module='slave',
                                              citiroc='a',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=0)
        
    def decoder_plot_science_robotic(self, module, citiroc, channel_row, channel_column, channel_shift, update=False):

        # Loop all channel
        for channel_idx, channel in enumerate(list(product(range(channel_row), range(channel_column)))):

            # Determine further variable (not concrete, but easier to read)
            if module == 'master':
                config_module = 0
                if citiroc == 'a':
                    config_citiroc = 0
                    hg_line_color = (250, 140, 0)
                    lg_line_color = (240, 170, 75)
                    if channel_row == 8: # plot two sensor
                        if channel[0] >= 4: # M3
                            sensor_name = 'sensor_3'
                        else: # M4
                            sensor_name = 'sensor_4'
                    else: # only plot one sensor
                        if channel_shift == 16: # M3
                            sensor_name = 'sensor_3'
                        else: # M4
                            sensor_name = 'sensor_2'
                else: 
                    config_citiroc = 1
                    hg_line_color = (255, 0, 0)
                    lg_line_color = (255, 110, 110)
                    if channel_row == 8: # plot two sensor
                        if channel[0] >= 4: # M1
                            sensor_name = 'sensor_1'
                        else: # M2
                            sensor_name = 'sensor_2'
                    else: # only plot one sensor
                        if channel_shift == 16: # M1
                            sensor_name = 'sensor_1'
                        else: # M2
                            sensor_name = 'sensor_2'
            else:
                config_module = 1
                if citiroc == 'a':
                    config_citiroc = 0
                    hg_line_color = (0, 100, 250)
                    lg_line_color = (90, 150, 252)
                    if channel_row == 8: # plot two sensor
                        if channel[0] >= 4: # S3
                            sensor_name = 'sensor_3'
                        else: # S4
                            sensor_name = 'sensor_4'
                    else: # only plot one sensor
                        if channel_shift == 16: # S3
                            sensor_name = 'sensor_3'
                        else: # S4
                            sensor_name = 'sensor_2'
                else: 
                    config_citiroc = 1
                    hg_line_color = (0, 0, 250)
                    lg_line_color = (80, 80, 250)
                    if channel_row == 8: # plot two sensor
                        if channel[0] >= 4: # S1
                            sensor_name = 'sensor_1'
                        else: # S2
                            sensor_name = 'sensor_2'
                    else: # only plot one sensor
                        if channel_shift == 16: # S1
                            sensor_name = 'sensor_1'
                        else: # S2
                            sensor_name = 'sensor_2'
            
            if update == False: # first plotting
                
                if self.parent.ui.combine_Hg_Lg_on_check_box.isChecked():

                    combine_config = ((config_module, config_citiroc, channel_idx+channel_shift))
                    # print('update = false')
                    hist, bin_edges, jump_pos, Sensor_name, Sensor_Channel, position = self.decoder_combine_hg_lg_data(self.decoder_plot_science_df, config_module, config_citiroc, channel_idx+channel_shift, self.n_of_combine)
                    # print(f'print sensor = {Sensor_name}')  
                    self.n_of_combine +=1
                    # print(f'from thread {jump_pos}')
                

                    self.decoder_thread_plot_update_science_hg_lg_combine_signal.emit([True, update, Sensor_name, citiroc, 
                                                                            position, channel_idx, channel_shift, sensor_name,
                                                                            jump_pos, hg_line_color, hist, bin_edges,
                                                                            True, self.current_file_dirname, self.current_file_basename])
            


                    # self.decoder_thread_plot_update_science_hg_signal.emit([True, update, module, citiroc, 
                    #                                                         channel, channel_idx, channel_shift, sensor_name,
                    #                                                         1, hg_line_color, hist, bin_edges,
                    #                                                         True])
                else:
                    # Create configuration for groupby
                    hg_config = ((config_module, config_citiroc, channel_idx+channel_shift, 1))
                    lg_config = ((config_module, config_citiroc, channel_idx+channel_shift, 0))

                    if hg_config in self.decoder_plot_science_grouped_df.groups.keys(): # with configuration

                        # Extract data by configuration
                        hg_config_df = self.decoder_plot_science_grouped_df.get_group(hg_config)

                        # Bin data
                        hist, bin_edges = np.histogram(hg_config_df['ADC'], 
                                                    bins=np.arange(self.decoder_plot_range_min, self.decoder_plot_range_max+self.decoder_plot_bin_size, self.decoder_plot_bin_size), 
                                                    density=False)

                        # Emit siganl back to parent class
                        self.decoder_thread_plot_update_science_hg_signal.emit([True, update, module, citiroc, 
                                                                            channel, channel_idx, channel_shift, sensor_name,
                                                                            1, hg_line_color, hist, bin_edges,
                                                                            True])
                    
                    else: # without configuration

                        # Emit siganl back to parent class
                        self.decoder_thread_plot_update_science_hg_signal.emit([True, update, module, citiroc, 
                                                                                channel, channel_idx, channel_shift, sensor_name,
                                                                                1, hg_line_color, 0, 0,
                                                                                False])

                    if lg_config in self.decoder_plot_science_grouped_df.groups.keys(): # configuration exist

                        # Extract data by configuration
                        lg_config_df = self.decoder_plot_science_grouped_df.get_group(lg_config)

                        # Bin data
                        hist, bin_edges = np.histogram(lg_config_df['ADC'], 
                                                    bins=np.arange(self.decoder_plot_range_min, self.decoder_plot_range_max+self.decoder_plot_bin_size, self.decoder_plot_bin_size), 
                                                    density=False)
                        
                        # Emit siganl back to parent class
                        self.decoder_thread_plot_update_science_lg_signal.emit([True, update, module, citiroc, 
                                                                                channel, channel_idx, channel_shift, sensor_name,
                                                                                0, lg_line_color, hist, bin_edges,
                                                                                True])
                    
                    else: # without configuration

                        # Emit siganl back to parent class
                        self.decoder_thread_plot_update_science_lg_signal.emit([True, update, module, citiroc, 
                                                                                channel, channel_idx, channel_shift, sensor_name,
                                                                                0, lg_line_color, 0, 0,
                                                                                False])
                
            
            else: # update plotting
                if self.parent.ui.combine_Hg_Lg_on_check_box.isChecked():
                    # print('update = true')

                    combine_config = ((config_module, config_citiroc, channel_idx+channel_shift))
                    hist, bin_edges, jump_pos, Sensor_name, Sensor_Channel, position = self.decoder_combine_hg_lg_data(self.decoder_plot_science_df, config_module, config_citiroc, channel_idx+channel_shift)
                    # print(f'from thread {jump_pos}')
                    self.decoder_thread_plot_update_science_hg_lg_combine_signal.emit([True, update, Sensor_name, citiroc, 
                                                                            position, channel_idx, channel_shift, sensor_name,
                                                                            jump_pos, hg_line_color, hist, bin_edges,
                                                                            True, self.current_file_dirname, self.current_file_basename])
 
                else:
                    # Create configuration for groupby
                    hg_config = ((config_module, config_citiroc, channel_idx+channel_shift, 1))
                    lg_config = ((config_module, config_citiroc, channel_idx+channel_shift, 0))

                    if hg_config in self.decoder_plot_science_grouped_df.groups.keys(): # configuration exist

                        # Extract data by configuration
                        hg_config_df = self.decoder_plot_science_grouped_df.get_group(hg_config)

                        # Bin data
                        hist, bin_edges = np.histogram(hg_config_df['ADC'], 
                                                    bins=np.arange(self.decoder_plot_range_min, self.decoder_plot_range_max+self.decoder_plot_bin_size, self.decoder_plot_bin_size), 
                                                    density=False)

                        # Emit siganl back to parent class
                        self.decoder_thread_plot_update_science_hg_signal.emit([True, update, module, citiroc, 
                                                                                channel, channel_idx, channel_shift, sensor_name,
                                                                                1, hg_line_color, hist, bin_edges,
                                                                                True])
                    
                    else: # without configuration

                        # Emit siganl back to parent class
                        self.decoder_thread_plot_update_science_hg_signal.emit([True, update, module, citiroc, 
                                                                                channel, channel_idx, channel_shift, sensor_name,
                                                                                1, hg_line_color, 0, 0,
                                                                                False])

                    if lg_config in self.decoder_plot_science_grouped_df.groups.keys(): # configuration exist

                        # Extract data by configuration
                        lg_config_df = self.decoder_plot_science_grouped_df.get_group(lg_config)

                        # Bin data
                        hist, bin_edges = np.histogram(lg_config_df['ADC'], 
                                                    bins=np.arange(self.decoder_plot_range_min, self.decoder_plot_range_max+self.decoder_plot_bin_size, self.decoder_plot_bin_size), 
                                                    density=False)

                        # Emit siganl back to parent class
                        self.decoder_thread_plot_update_science_lg_signal.emit([True, update, module, citiroc, 
                                                                                channel, channel_idx, channel_shift, sensor_name,
                                                                                0, lg_line_color, hist, bin_edges])
                    
                    else: # without configuration

                        # Emit siganl back to parent class
                        self.decoder_thread_plot_update_science_lg_signal.emit([True, update, module, citiroc, 
                                                                                channel, channel_idx, channel_shift, sensor_name,
                                                                                0, lg_line_color, 0, 0, ])
        # Emit siganl back to parent class
        if self.parent.ui.combine_Hg_Lg_on_check_box.isChecked():
            # print('gg')
            self.decoder_thread_plot_update_science_hg_lg_combine_signal.emit([False, update, Sensor_name, citiroc, 
                                                                              self.current_file_dirname, self.current_file_basename])
        else:    
            self.decoder_thread_plot_update_science_lg_signal.emit([False, update, module, citiroc])

    def decoder_update_plot_science(self, filename_list):

        # Update df
        self.decoder_plot_science_df, self.decoder_plot_science_df_skip_number \
        = self.decoder_load_df(filename_list[0], self.decoder_plot_science_df, self.decoder_plot_science_df_skip_number)
        
        # Re-group df
        self.decoder_plot_science_grouped_df = self.decoder_plot_science_df.groupby(['GTM ID', 'CITIROC', 'Channel', 'Gain'])

        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_master_s1_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_master_s2_check_box.isChecked()): # need to plot M1 and M2

            # Update, respond and save robotically
            self.decoder_plot_science_robotic(module='master',
                                              citiroc='b',
                                              channel_row=8,
                                              channel_column=4,
                                              channel_shift=0,
                                              update=True)

        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_master_s1_check_box.isChecked() and \
        not self.parent.ui.decoder_display_selection_master_s2_check_box.isChecked()): # only need to plot M1

            # Update, respond and save robotically
            self.decoder_plot_science_robotic(module='master',
                                              citiroc='b',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=16,
                                              update=True)
        
        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        (not self.parent.ui.decoder_display_selection_master_s1_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_master_s2_check_box.isChecked()): # only need to plot M2

            # Update, respond and save robotically
            self.decoder_plot_science_robotic(module='master',
                                              citiroc='b',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=0,
                                              update=True)

        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_master_s3_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_master_s4_check_box.isChecked()): # need to plot M3 and M4

            # Update, respond and save robotically
            self.decoder_plot_science_robotic(module='master',
                                              citiroc='a',
                                              channel_row=8,
                                              channel_column=4,
                                              channel_shift=0,
                                              update=True)

        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_master_s3_check_box.isChecked() and \
        not self.parent.ui.decoder_display_selection_master_s4_check_box.isChecked()): # only need to plot M3

            # Update, respond and save robotically
            self.decoder_plot_science_robotic(module='master',
                                              citiroc='a',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=16,
                                              update=True)
        
        if self.parent.ui.decoder_display_selection_master_group.isChecked() and \
        (not self.parent.ui.decoder_display_selection_master_s3_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_master_s4_check_box.isChecked()): # only need to plot M4

            # Update, respond and save robotically
            self.decoder_plot_science_robotic(module='master',
                                              citiroc='a',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=0,
                                              update=True)
        
        if self.parent.ui.decoder_display_selection_slave_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_slave_s1_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_slave_s2_check_box.isChecked()): # need to plot S1 and S2

            # Update, respond and save robotically
            self.decoder_plot_science_robotic(module='slave',
                                              citiroc='b',
                                              channel_row=8,
                                              channel_column=4,
                                              channel_shift=0,
                                              update=True)

        if self.parent.ui.decoder_display_selection_slave_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_slave_s1_check_box.isChecked() and \
        not self.parent.ui.decoder_display_selection_slave_s2_check_box.isChecked()): # only need to plot S1

            # Update, respond and save robotically
            self.decoder_plot_science_robotic(module='slave',
                                              citiroc='b',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=16,
                                              update=True)
        
        if self.parent.ui.decoder_display_selection_slave_group.isChecked() and \
        (not self.parent.ui.decoder_display_selection_slave_s1_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_slave_s2_check_box.isChecked()): # only need to plot S2

            # Update, respond and save robotically
            self.decoder_plot_science_robotic(module='slave',
                                              citiroc='b',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=0,
                                              update=True)

        if self.parent.ui.decoder_display_selection_slave_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_slave_s3_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_slave_s4_check_box.isChecked()): # need to plot S3 and S4

            # Update, respond and save robotically
            self.decoder_plot_science_robotic(module='slave',
                                              citiroc='a',
                                              channel_row=8,
                                              channel_column=4,
                                              channel_shift=0,
                                              update=True)

        if self.parent.ui.decoder_display_selection_slave_group.isChecked() and \
        (self.parent.ui.decoder_display_selection_slave_s3_check_box.isChecked() and \
        not self.parent.ui.decoder_display_selection_slave_s4_check_box.isChecked()): # only need to plot S3

            # Update, respond and save robotically
            self.decoder_plot_science_robotic(module='slave',
                                              citiroc='a',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=16,
                                              update=True)
        
        if self.parent.ui.decoder_display_selection_slave_group.isChecked() and \
        (not self.parent.ui.decoder_display_selection_slave_s3_check_box.isChecked() and \
        self.parent.ui.decoder_display_selection_slave_s4_check_box.isChecked()): # only need to plot S4

            # Update, respond and save robotically
            self.decoder_plot_science_robotic(module='slave',
                                              citiroc='a',
                                              channel_row=4,
                                              channel_column=4,
                                              channel_shift=0,
                                              update=True)

    ### decoder_start_end ###