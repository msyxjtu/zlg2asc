from datetime import datetime


def zlg_abs_time2datetime(zlg_abs_time):
    return datetime.strptime(zlg_abs_time, "%H:%M:%S.%f.0")
    # return datetime.strptime(zlg_abs_time, " %H:%M:%S.%f.0")


def remove_all_piece_asc(files_path):
    for root, dirs, files in os.walk(files_path):
        for _ in files:
            if _[-4:] == '.asc' and _[10:15] == 'Frame':
                os.remove(os.path.join(root, _))


def zlg2asc_abs_time(zlg_str, start_time, sep=','):
    """序号,传输方向,时间戳,ID,帧格式,帧类型,长度,数据,
    0,接收,16:44:48.459.0,0x00000114,标准帧,数据帧,0x08,FF 18 01 13 FF 01 00 01 ,
    1,接收,16:44:48.459.0,0x00000214,标准帧,数据帧,0x06,CA 8E C0 00 00 00 ,
    output: 42.980800	1 653	Rx	d	8	10 0f a0 70 d8 50 09 a0  """

    frame_info = zlg_str.split(sep)
    try:
        output = []
        x = (zlg_abs_time2datetime(frame_info[2]) - start_time).total_seconds()
        if x < 0:
            x += 86400
        output.append(x)
        output.append('1')  # CAN数据记录的通道，默认写1通道
        output.append(frame_info[3][-3:])  # 信号帧ID
        if frame_info[1] == '接收' or frame_info[1] == 'Receive':
            output.append('Rx')
        else:
            output.append('Tx')

        output.append('d')  # asc里面有一个d，我忘了是什么意思
        output.append(frame_info[6][-2:].replace('0', ''))  # 信号帧长度
        output.append(frame_info[7].replace('\n', ''))
        # output.append(frame_info[7].replace('\n', ''))  # 信号帧内容，将信号内容当中的‘\n’剔除
        # print(output)
    except ValueError:
        print('ValueError: ', zlg_str)
        output = 'wrong frame'
    # except KeyError:
    #     print('KeyError: ', zlg_str)
    #     output = 'wrong frame'
    # except IndexError:
    #     print('IndexError: ', zlg_str)
    #     output = 'wrong frame'

    return output


def zlg_file2asc_file(file_dir, source_filename, output_filename, start_time):
    """用于将周立功数据转为asc数据，但输出文件还没有增加前后缀。
    在输出asc文件的时候会修改文件名，以保证按照os.walk的默认排序方式，文件的排序是正确的"""

    output_filepath = os.path.join(file_dir, output_filename)
    source_filepath = os.path.join(file_dir, source_filename)
    with open(output_filepath, 'w') as output_file:
        with open(source_filepath, 'r', ) as source:
            i = 0
            for _ in source:
                i += 1
                if i > 1:
                    # can_data_output = zlg2asc_abs_time(_, start_time, sep='\t')
                    can_data_output = zlg2asc_abs_time(_, start_time, sep=',')
                    if can_data_output == 'wrong frame':
                        pass
                    else:
                        output_file.write(' '.join(str(i) for i in can_data_output) + '\n')


def convert_all_zlg_csv_abs_time(files_path, start_time):
    """将一个文件夹当中的所有周立功数据挨个转换为asc数据"""
    for root, dirs, files in os.walk(files_path):
        for _ in files:
            if _[-3:] == 'csv' or _[-3:] == 'txt':
                x = '00000000000'
                for __ in range(len(_)):
                    if _[__] == '(':
                        start_bit = __
                    if _[__] == '-':
                        end_bit = __

                output_filename = x[0:10 - (end_bit - start_bit)] + _[start_bit + 1:end_bit + 1] + _[0:-4] + '.asc'
                if os.path.exists(os.path.join(files_path, output_filename)):
                    pass
                else:
                    zlg_file2asc_file(files_path, _, output_filename, start_time)


def merge_all_asc(filepath, output_path, output_filename, start_time):
    """合并文件夹里面所有的asc文件"""
    # 生成header
    time_header = 'Mon Nov 11 ' + start_time.strftime('%H:%M:%S.%f')[0:-3] + start_time.strftime(' %p') + ' 2222'
    header = 'date ' + time_header + '\n' + \
             'base hex  timestamps absolute\n' + \
             'internal events logged\n' + '// version 8.5.0\n' + \
             'Begin Triggerblock ' + time_header + '\n' + \
             '0.0	Start of measurement\n'

    # 首先合并所有的文件
    output_filename += '_asc.asc'
    with open(os.path.join(output_path, output_filename), 'w') as merge_output:
        merge_output.write(header)
        for root, dirs, files in os.walk(filepath):
            for _ in files:
                if _[-3:] == 'asc':
                    with open(os.path.join(filepath, _)) as asc_file:
                        merge_output.write(asc_file.read())  # +"/n")
        merge_output.write('End TriggerBlock')


if __name__ == '__main__':
    # print(zlg2asc('0,接收,164796.9121,00000214 H,标准帧,数据帧,6,96 AD A0 00 00 08 ,'))
    import os
    import time

    time1 = time.time()

    data_file_dir_temp = input('请输入数据文件夹地址: ')
    data_path = data_file_dir_temp.replace('\\', '/')
    project_name = data_file_dir_temp.split('\\')[-1]
    target_dir = '/'.join(data_file_dir_temp.split('\\')[:-1])

    remove_all_piece_asc(data_path)
    for root, dirs, files in os.walk(data_path):
        for _ in files:
            print(_)
            with open(os.path.join(root, _), 'r') as first_file:
                # print(chardet.detect(first_file.readlines())['enconding'])
                start_time_str = first_file.readlines()[1].split(',')[2]
                # start_time_str = first_file.readlines()[1].split('\t')[2]

            break

    start_time = zlg_abs_time2datetime(start_time_str)

    convert_all_zlg_csv_abs_time(data_path, start_time)
    merge_all_asc(data_path, target_dir, project_name, start_time)
    remove_all_piece_asc(data_path)
    time2 = time.time()
    print('总共耗时：', time2 - time1, 's')

    # datetime.strptime()
