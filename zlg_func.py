import datetime
import logging
import multiprocessing
import os
import time

import pandas as pd


def time_function(func):
    def wrapper(*args, **kwargs):
        time1 = time.time()
        func(*args, **kwargs)
        time2 = time.time()
        print(time2 - time1)

    return wrapper


def remove_all_piece_asc(files_path):
    for root, dirs, files in os.walk(files_path):
        for _ in files:
            if _[-4:] == '.asc' and _[10:15] == 'Frame':
                os.remove(os.path.join(root, _))


def zlg2asc(zlg_str, last_step_time):
    """将周立功采集的数据格式转化为asc格式，其中周立功采集数据的时间单位是10ms，所以需要除以100才是s。
    input: 1,接收,240059.0458,000001BB H,标准帧,数据帧,8,00 00 00 04 61 00 65 00 ,
    output: 42.980800	1 653	Rx	d	8	10 0f a0 70 d8 50 09 a0  """

    frame_info = zlg_str.split(',')
    try:
        output = []
        # output.append(float(frame_info[2]) / 100)  # 周立功有设计缺陷，文件当中应该需要强制写清楚时间的单位，以及采集的起始时间。

        if frame_info[1] == '接收' or frame_info[1] == 'Receive':
            step_time = float(frame_info[2]) / 100
            output.append(step_time)
            output.append('1')  # CAN数据记录的通道，默认写1通道
            output.append(frame_info[3][0:8])  # 信号帧ID
            output.append('Rx')
        elif frame_info[1] == '发送':
            output.append(last_step_time)
            output.append('1')  # CAN数据记录的通道，默认写1通道
            output.append(frame_info[3][0:8])  # 信号帧ID
            output.append('Tx')
            step_time = last_step_time

        output.append('d')  # asc里面有一个d，我忘了是什么意思
        output.append(frame_info[6])  # 信号帧长度
        output.append(frame_info[7])  # 信号帧内容
        # print(output)
    except ValueError:
        print('ValueError: ', zlg_str)
        output = 'wrong frame'
        # except KeyError:
        #     print('KeyError: ', zlg_str)
        #     output = 'wrong frame'
        # except IndexError:
        #     print('KeyError: ', zlg_str)
        #     output = 'wrong frame'
        step_time = 0
    return output, step_time


def zlg_file2asc_file(file_path):
    """用于将周立功数据转为asc数据，但输出文件还没有增加前后缀。
    在输出asc文件的时候会修改文件名，以保证按照os.walk的默认排序方式，文件的排序是正确的"""
    import os
    zlg_file = os.path.basename(file_path)
    file_dir = os.path.dirname(file_path)
    x = '00000000000'
    for _ in range(len(zlg_file)):
        if zlg_file[_] == '(':
            start_bit = _
        if zlg_file[_] == '-':
            end_bit = _

    output_filename = x[0:10 - (end_bit - start_bit)] + zlg_file[start_bit + 1:end_bit + 1] + zlg_file[0:-3] + '.asc'

    with open(os.path.join(file_dir, output_filename), 'w') as output_file:
        with open(file_path, 'r') as source:
            i = 0
            last_step_time = 'N.A.'
            for _ in source:
                i += 1
                if i == 2 and _.split(',')[2] == '无':
                    pass
                elif i > 2:
                    can_data_output, step_time = zlg2asc(_, last_step_time)
                    last_step_time = step_time
                    if can_data_output == 'wrong frame':
                        logging.info('File: ' + file_path + '  , Wrong Frame: ' + _)
                        pass
                    else:
                        output_file.write(' '.join(str(i) for i in can_data_output) + '\n')


def convert_all_zlg_csv(files_path, concurrent=None):
    """将一个文件夹当中的所有周立功数据挨个转换为asc数据"""
    import os
    file_list = []
    for root, dirs, files in os.walk(files_path):
        for _ in files:
            if _[-3:] == 'csv' or _[-3:] == 'txt':
                logging.info("Found file: " + _)

                if not concurrent:
                    zlg_file2asc_file(os.path.join(root, _))
                    logging.info(_ + ' Done')
                else:
                    file_list.append(os.path.join(root, _))

    if concurrent:
        pool = multiprocessing.Pool(concurrent)
        pool.map(zlg_file2asc_file, file_list)
        pool.close()
        pool.join()


def merge_all_asc(filepath, output_path, output_filename, remove_merged_file=True):
    """合并文件夹里面所有的asc文件"""

    # 首先合并所有的文件
    output_filename += '_asc'
    with open(os.path.join(output_path, output_filename), 'w') as merge_output:
        for root, dirs, files in os.walk(filepath):
            for _ in files:
                if _[-3:] == 'asc':
                    with open(os.path.join(filepath, _)) as asc_file:
                        merge_output.write(asc_file.read())  # +"/n")

    # 然后去读合并的文件，如果时间上有突变就截断。

    merge_output = open(os.path.join(output_path, output_filename), 'r')

    number_x = 1

    output_file = open(os.path.join(output_path, output_filename + 'part' + str(number_x)) + '.asc', 'w')
    output_file.write(
        'date Fri Dec 16 10:37:28.636 am 2016\nbase hex  timestamps absolute\ninternal events logged\n// version 8.5.0\nBegin Triggerblock Fri Dec 16 10:37:28.636 am 2016\n0.0	Start of measurement\n')
    time_last_frame = 0

    with open(os.path.join(output_path, output_filename), 'r') as merged_file:
        for _ in merged_file:
            try:
                frame_time = float(_.split(' ')[0])
            except ValueError:
                print(_)
            if frame_time < time_last_frame - 100:
                print(frame_time, time_last_frame)
                output_file.write('End TriggerBlock')
                output_file.close()
                number_x += 1
                output_file = open(os.path.join(output_path, output_filename + 'part' + str(number_x)) + '.asc', 'w')
                output_file.write(
                    'date Fri Dec 16 10:37:28.636 am 2016\nbase hex  timestamps absolute\ninternal events logged\n// version 8.5.0\nBegin Triggerblock Fri Dec 16 10:37:28.636 am 2016\n0.0	Start of measurement\n')
                output_file.write(_)
                time_last_frame = 0
            else:
                time_last_frame = frame_time
                output_file.write(_)

    output_file.write('End TriggerBlock')
    output_file.close()
    merge_output.close()

    if remove_merged_file:
        os.remove(os.path.join(output_path, output_filename))


def merge_all_asc2(filepath, output_path, output_filename):
    """合并文件夹里面所有的asc文件"""

    # 首先合并所有的文件
    merge_output = open(os.path.join(output_path, output_filename), 'w')
    for parent, dirnames, filenames in os.walk(filepath):
        for _ in filenames:
            if _[-3:] == 'asc':
                asc_file = open(os.path.join(filepath, _))
                merge_output.write(asc_file.read())  # +"/n")
    merge_output.close()

    merge_output = open(os.path.join(output_path, output_filename), 'r')
    data = pd.read_csv(os.path.join(output_path, output_filename),
                       sep=' ')  # 使用空格分隔asc文件会把CAN报文切割开，但是只要重新写入的时候还是这么操作，应该就不影响。

    time_raw = data.iloc[:, 0]  # 时间在第一列

    time_raw = time_raw.apply(float)


@time_function
def zlg_folder_2_asc(data_file_dir_temp):
    data_path = data_file_dir_temp.replace('\\', '/')
    project_name = data_file_dir_temp.split('\\')[-1]
    target_dir = '/'.join(data_file_dir_temp.split('\\')[:-1])

    convert_all_zlg_csv(data_path)

    merge_all_asc(data_path, target_dir, project_name, remove_merged_file=True)
    remove_all_piece_asc(data_path)


if __name__ == '__main__':
    # print(zlg2asc('0,接收,164796.9121,00000214 H,标准帧,数据帧,6,96 AD A0 00 00 08 ,'))
    logging.basicConfig(filename='zlg2asc.log', level=logging.INFO)
    logging.info(str(datetime.datetime.now()) + ' Start:')
    zlg_folder_2_asc(input('请输入数据文件夹地址: '))
    logging.info(str(datetime.datetime.now()) + ' Done.')
