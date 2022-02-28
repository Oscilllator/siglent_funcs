#!/usr/bin/env python
#-*- coding:utf-8 –*-
#-----------------------------------------------------------------------------
# $Header: $
#-----------------------------------------------------------------------------
# Python Version:       3.4.3		 
#
# Authors:		Angel.Xu
#
# Started:		2018.07.12
#
# Copyright 2013-2018 Siglent Corporation. All Rights Reserved.
#
#-----------------------------------------------------------------------------

import struct
from decimal import *
import csv
import gc
import math
import time
import numpy as np
import matplotlib.pyplot as plt

INT_BYTE_LEN = 4
DOUBLE_BYTE_LEN = 8

BIN_HEAD={0:{"UNIT_BYTE_LEN":4,
             "RESERVE_BYTE_LEN": 0x800 - 0x11c},
          1:{"UNIT_BYTE_LEN":4,
             "RESERVE_BYTE_LEN": 0x800 - 0x11c},
          2:{"UNIT_BYTE_LEN":28,
             "RESERVE_BYTE_LEN":0x800-0x261}}

TWO_PREC = '0.00'
FIVE_PREC = '0.00000'
TEN_PREC = '0.0000000000'
ELEV_PREC = '0.00000000000'


HORI_DIV_NUM = 10#TODO:Modify according to the model.
VERT_DIV_CODE = 30#TODO:Modify according to the model.
Magnitude = [10e-24,10e-21,10e-18,10e-15,\
             10e-12,10e-9,10e-6,10e-3,1,\
             10e3,10e6,10e9,10e12,10e15,\
             10e18,10e21,10e24]

def deal_to_data_unit(f, para_num, bin_ver):
    if para_num == 1:
        stream = f.read(DOUBLE_BYTE_LEN)
        data = struct.unpack('d',stream)[0]
        stream = f.read(INT_BYTE_LEN)
        unit = struct.unpack('i',stream)[0]
        stream = f.read(INT_BYTE_LEN)
        para = data*Magnitude[unit]
    else:
        para = []
        for i in range(0,para_num):
            stream = f.read(DOUBLE_BYTE_LEN)
            data = struct.unpack('d',stream)[0]
            stream = f.read(INT_BYTE_LEN)
            unit = struct.unpack('i',stream)[0]
            stream = f.read(BIN_HEAD[bin_ver]["UNIT_BYTE_LEN"])
            data_unit = data*Magnitude[unit]
            para.append(data_unit)
    return para
    
def deal_to_int(f, para_num):
    if para_num == 1:
        stream = f.read(INT_BYTE_LEN)
        para = struct.unpack('i',stream)[0]
    else:
        para = []
        for i in range(0,para_num):
            stream = f.read(INT_BYTE_LEN)
            data= struct.unpack('i',stream)[0]
            para.append(data)
    return para

def get_bit_from_byte(byData,bit):
    n0 = 1 if((byData & (1<<bit))== (1<<bit)) else 0
    return n0

def extract_header(f):
    bin_ver = deal_to_int(f, 1)
    ch_state = deal_to_int(f, 4)
    ch_vdiv = deal_to_data_unit(f, 4, bin_ver)
    ch_ofst = deal_to_data_unit(f, 4, bin_ver)
    digit_state = deal_to_int(f, 17)
    hori_list = deal_to_data_unit(f, 2, bin_ver)
    wave_len = deal_to_int(f, 1)
    print(wave_len)
    sara = deal_to_data_unit(f, 1, bin_ver)
    di_wave_len = deal_to_int(f, 1)
    print(di_wave_len)
    di_sara = deal_to_data_unit(f, 1, bin_ver)
    _ = f.read(BIN_HEAD[bin_ver]["RESERVE_BYTE_LEN"])
    return ch_state, ch_vdiv, ch_ofst, digit_state, hori_list, wave_len, sara, di_sara

def extract_body(buf: bytes, size_per_ch: int, vdiv: list):
    parsed = np.frombuffer(buf, dtype=np.uint8)[81:]

    assert(parsed.size % size_per_ch == 0)
    num_channels = parsed.size // size_per_ch
    assert(num_channels == len(vdiv))
    parsed = (parsed.astype('float') / 256).reshape((num_channels, size_per_ch))
    parsed *= np.array(vdiv).reshape((num_channels, 1))
    return parsed

def extract_data(f):
    ch_state, ch_vdiv, ch_ofst, digit_state, hori_list, wave_len, sara, di_sara = extract_header(f)
    data = f.read()
    volts = extract_data(data, wave_len, ch_vdiv)
    return 1/sara, volts

# old garbage code from siglent, ignore:
def main(file):
    start = time.time()
    with open(file,'rb+') as f:
        ch_state, ch_vdiv, ch_ofst, digit_state, hori_list, wave_len, sara, di_sara = extract_header(f)
        print("things:", ch_state, ch_vdiv, ch_ofst, digit_state, hori_list, wave_len, sara, di_sara)
        data = f.read()
    print('Read data from bin file finished!')
    print(f'read data from file in {time.time() - start:.3f}s')
    volts = extract_data(data, wave_len, ch_vdiv)
    plt.plot(volts.T, '.-')
    plt.show()

    ##--------------------get csv head------------------
    csv_len = [['Record Length']]
    csv_vdiv = [['Vertical Scale']]
    csv_ofst = [['Vertical Offset']]
    csv_tdiv = [['Horizontal Scale']]
    csv_sara = [['Sample Rate']]
    csv_para = [['Second']]
        
    ch_state_sum = 0
    for i in range(0, len(ch_state)):
        ch_state_sum += ch_state[i]
        if ch_state[i]:
            csv_vdiv[0].append('C{0}:{1}'.format(i+1, Decimal(str(ch_vdiv[i])).quantize(Decimal(TWO_PREC))))
            csv_ofst[0].append('C{0}:{1}'.format(i+1, Decimal(str(ch_ofst[i])).quantize(Decimal(FIVE_PREC))))
            csv_para[0].append('Volt')
    if ch_state_sum > 0:
        csv_len[0].append('Analog:{}'.format(wave_len))
        csv_sara[0].append('Analog:{}'.format(sara))
          
    csv_tdiv[0].append(Decimal(str(hori_list[0])).quantize(Decimal(TEN_PREC)))
   
    digit_state_sum = 0
    if digit_state[0]:
        for i in range(1, len(digit_state)):
            digit_state_sum += digit_state[i]
            if digit_state[i]:
                if 'Second' not in csv_para[0]:
                    csv_para[0].append('Second')
                csv_para[0].append('D{}'.format(i-1))
            else:
                pass
            
    if digit_state_sum > 0:
        csv_len[0].append('Digital:{}'.format(di_wave_len))
        csv_sara[0].append('Digital:{}'.format(di_sara))

    print('Writing to csv head...')
    with open('test.csv','a',newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(csv_len)    
        writer.writerows(csv_sara)
        writer.writerows(csv_vdiv)
        writer.writerows(csv_ofst)    
        writer.writerows(csv_tdiv)
        writer.writerows(csv_para)

    ##-------------------------分块获取所有通道数据，写入csv------------------------------
    if len(data) >= 14e6 or wave_len >= 1E6:
        BLOCK_LEN = 1000000
        print('start to block')
    else:
        BLOCK_LEN = wave_len

    block_num = int(wave_len//BLOCK_LEN)
    last_block_len = wave_len%BLOCK_LEN
    div_flag = False
    if  last_block_len!= 0:
        block_num = block_num +1
        div_flag = True

    for k in range(0,block_num):
        CH1_DATA_BLOCK = range(BLOCK_LEN*k,BLOCK_LEN*(k+1))
        if k == (block_num -1) and div_flag:
            CH1_DATA_BLOCK = range(BLOCK_LEN*k,BLOCK_LEN*k+last_block_len)
        print('BLOCK{0} {1} converting...'.format(k,CH1_DATA_BLOCK))
        csv_ch_time_volt = []
        #-------------------------analog data convert------------------------------
        print('analog converting...')
        for i in CH1_DATA_BLOCK:
            ch_state_num = 0
            volt = []
            time_data = float(-hori_list[0]*HORI_DIV_NUM/2+ i*(1/sara))
            for j in range(0,len(ch_state)):
                if ch_state[j]: 
                    volt_data = int(data[i+ (ch_state_num * wave_len)])  
                    a = (volt_data -128)*ch_vdiv[j]/VERT_DIV_CODE - ch_ofst[j]
                    volt.append(Decimal(str(a)).quantize(Decimal(FIVE_PREC)))
                    ch_state_num += 1
                else:
                    pass
            if ch_state_num > 0:
                volt.insert(0,Decimal(str(time_data)).quantize(Decimal(ELEV_PREC)))

            #-------------------------digital data convert------------------------------
            #-------------------------TO DO:数字通道待定------------------------------
            '''
            if digit_state_sum > 0:
                digit_state_num = 0
                digit_time = float(-hori_list[0]*HORI_DIV_NUM/2 +i*(1/di_sara))
                #print('Data of digital converting...')
                di_byte_len = math.ceil(di_wave_len/8)
                for m in range(1,len(digit_state)):
                    if i > di_wave_len:#i表示CH1数据点
                        print('Digital data convert finished!')
                        continue
                    else:
                        if digit_state[m]:
                            dx_start = (ch_state_num * wave_len)+(digit_state_num * di_byte_len)
                            byt,bit = i/8,i%8 #表示dx的第几个点
                            dx_index = int(dx_start + byt)
                            a = get_bit_from_byte(data[dx_index],bit)
                            volt.append(a)
                            digit_state_num += 1
                        else:
                            pass
                volt.insert(ch_state_sum+1,Decimal(str(digit_time)).quantize(Decimal(ELEV_PREC)))
            else:
                pass
            '''
            csv_ch_time_volt.append(volt)
            
        #-------------------------分块写入csv------------------------------
        print('BLOCK{} writing to csv...'.format(k))    
        with open('test.csv','a',newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(csv_ch_time_volt)
            del csv_ch_time_volt
            gc.collect()
  
          
if __name__ == "__main__":
    main(r'usr_wf_data (3).bin')

