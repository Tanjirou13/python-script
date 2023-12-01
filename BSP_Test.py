import serial
import time
import openpyxl
import pandas as pd
import os
import json
import socket


def remove_first_and_last_lines(df_output):
    # 删除字符串第一行和最后一行
    """
    执行命令后返回的结果一般为：
    第一行： 命令本身
    中间： 命令返回结果
    最后一行： root@adcu:~# 
    因此去掉这两行后的结果才是真正的输出，该输出后面可能用于判断输出正确与否
    """
    lines = df_output.split('\n')
    # 删除第一行和最后一行
    if lines:
        lines = lines[1:-1]
    # 重新将列表连接成字符串
    result = '\n'.join(lines)
    return result


class UART:
    def __init__(self, port, baudrate, output_file="", prompt="", timeout=1):
        self.port = port 
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.output_file = output_file  #输出结果到表格或txt
        self.prompt = prompt #读取标志

    def connect_serial(self):
        #连接到串口
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            #print(self.serial)
        except self.serial.SerialException as e:
            print(f"Error: {e}")

    def read_and_save_log(self, write_mode, read_mode=1):
        """
        读取log并写入txt文件
        参数：
        - output_file: log的路径。
        - write_mode: 写入模式，'a'表示继续写入，'w'表示覆盖写入。
        - read_mode: 读取模式，'1'表示全部读取，'0'表示行读取。
        - prompt: 行写入时停止条件， 否则一直等待。
        返回：
        - 命令的输出字符串。
        """
        try:
            with open(self.output_file, write_mode) as file:
                if read_mode:
                    data = self.serial.readall().decode('utf-8')
                    if data:
                        # 写入数据到文件
                        file.write(data)
                        return data 
                else:
                    while True:
                        data = self.serial.readline().decode('utf-8')
                        if data:
                            file.write(data)
                            if self.prompt in data:
                                break  # 退出循环
                    return "OK"
        except serial.SerialException as e:
            return False

    # def __del__(self):
    #     self.close_connection()

    # def close_connection(self):
    #     if self.serial and self.serial.is_open:
    #         self.serial.close()
    #         print(f"Connection to {self.port} closed.")    


def convert_memory_string_to_numeric(memory_str):
        # 定义函数用于将带有单位的内存字符串转换为数字
        if 'Gi' in memory_str:
            return float(memory_str.replace('Gi', '')) * 1024
        elif 'Mi' in memory_str:
            return float(memory_str.replace('Mi', ''))
        else:
            return float(memory_str)


class Basic(UART):
    #执行Linux基础命令类，检查返回结果
    def __init__(self, port, baudrate):
        super().__init__(port, baudrate, 'basic_log.txt', '', 1)


    def execute_command(self, command, delay):
        """
        执行系统命令，并返回命令的输出，可选地添加等待时间。
        参数：
        - command: 要执行的系统命令。
        - delay: 执行命令前的等待时间（秒）。
        返回：
        - 命令的输出字符串。
        """
        if self.serial:
            self.serial.write(command.encode('utf-8'))
            time.sleep(delay)  # 等待响应
            result = self.read_and_save_log('a', 1)
            return result
        else:
            print("Not connected to a serial port.")
            return "ERROR"   


    def S_L_bring_up_test(self):
        #启动成功测试
        self.execute_command('cd /\r', 1)
        # df_output = send_command(serial_connection, 'pwd\r', 1)
        # result = remove_first_and_last_lines(df_output)
        # l = len(result)
        # #print(f"The length of the string is: {l}")
        # if result == "/\r":
        #     print('bring up ok')
        # else:
        #     print('error:',result)


    # def convert_memory_string_to_numeric(memory_str):
    #     # 定义函数用于将带有单位的内存字符串转换为数字
    #     if 'Gi' in memory_str:
    #         return float(memory_str.replace('Gi', '')) * 1024
    #     elif 'Mi' in memory_str:
    #         return float(memory_str.replace('Mi', ''))
    #     else:
    #         return float(memory_str)


    def S_L_DDR_memory_info_test(self):
        #DDR内存信息测试
        df_output = self.execute_command('free -h\n', 1)
        result = remove_first_and_last_lines(df_output)
        #print(result)

        # 将字符串按行拆分
        lines = result.split('\n')

        # 提取第二行数据
        second_line = lines[1]
        values = second_line.split()

        # 提取所需的值
        total_memory = values[1]
        free_memory = values[3]

        total = convert_memory_string_to_numeric(total_memory)
        free = convert_memory_string_to_numeric(free_memory)
        usage = round((total - free)/total*100,4)
        if result != "":
            print("memory usage: %s%%" % usage)
        else:
            print('error:',result)


    def S_L_CPU_load_test(self):
        #CPU信息测试
        df_output = self.execute_command('mpstat -P ALL\n', 1)
        result = remove_first_and_last_lines(df_output)
        #print(result)
        if result != "":
            print("All cpu load info output success")
        else:
            print('error:',result)   
    

    def S_L_EMMC_partition_test(self):
        #EMMC分区测试
        df_output = self.execute_command('df -h\n', 1)
        result = remove_first_and_last_lines(df_output)
        #print(result)

        # 要查找的字符串列表
        strings_to_find = ['/hdmap', '/hdmap_log', '/ota', '/log', '/hjmap']

        # 将文件系统信息按行拆分
        lines = result.split('\n')

        # 记录未找到的字符串
        not_found_strings = []

        # 遍历每行
        for line in lines:
        # 检查是否包含要查找的字符串
            for string in strings_to_find:
                if string in line:
                    strings_to_find.remove(string)
                    break

        # 输出提示
        if len(strings_to_find) != 0:
            print(f"the follow partitions are mounted error: {', '.join(strings_to_find)}")
        else:
            print("All partition mount normally")


    def S_L_SPI_Nand_Driver_test(self):
        #SPI Nand 驱动程序测试
        df_output1 = self.execute_command('ls /dev/mtdblock0\r', 1)
        result1 = remove_first_and_last_lines(df_output1)
        if result1 != "/dev/mtdblock0\r":
            print('error1:',result1)
        #print(result1)
        #print(df_output1)

        df_output2 = self.execute_command('dd if=/dev/urandom of=/tmp/randomfile bs=1M count=100\n', 3)
        result2 = remove_first_and_last_lines(df_output2)
        lines2 = result2.splitlines()
        if len(lines2) != 3:
            print('error2:',result2)
        #print(result2)
        #print(df_output2)

        df_output3 = self.execute_command('dd if=/tmp/randomfile of=/dev/mtdblock0\r', 3)
        result3 = remove_first_and_last_lines(df_output3)
        lines3 = result3.splitlines()
        if len(lines3) != 3:
            print('error3:',result3)
        #print(result3)
        # print(df_output3)

        df_output4 = self.execute_command('dd if=/dev/mtdblock0 of=/tmp/block1 bs=1M count=100\r', 3) 
        result4 = remove_first_and_last_lines(df_output4)
        lines4 = result4.splitlines()
        if len(lines4) != 3:
            print('error4:',result4)
        #print(result4)
        # print(df_output4)
        
        df_output5 = self.execute_command('cmp /tmp/randomfile /tmp/block1\r', 1)
        result5 = remove_first_and_last_lines(df_output5)
        if result5 != "":
            print('error5:',result5)
        #print(result5)
        #print(df_output5)

class R_Basic(UART):
    #执行R核基础命令类，检查返回结果
    def __init__(self, port, baudrate):
        super().__init__(port, baudrate, 'R_basic_log.md', '', 1)   

    def execute_command(self, command, delay):
        """
        执行系统命令，并返回命令的输出，可选地添加等待时间。
        参数：
        - command: 要执行的系统命令。
        - delay: 执行命令前的等待时间（秒）。
        返回：
        - 命令的输出字符串。
        """
        if self.serial:
            
            self.serial.write(command.encode('utf-8'))
            time.sleep(delay)  # 等待响应
            result = self.read_and_save_log('a', 1)
            if result == None:
                print("返回结果为空")
            return result
        else:
            print("Not connected to a serial port.")
            return "ERROR"

    def S_R_bring_up_test(self):
        #启动成功测试
        result = self.execute_command('ps tsk\n', 2)
        print(result)
        # df_output = send_command(serial_connection, 'pwd\r', 1)
        # result = remove_first_and_last_lines(df_output)
        # l = len(result)
        # #print(f"The length of the string is: {l}")
        # if result == "/\r":
        #     print('bring up ok')
        # else:
        #     print('error:',result)


class Ethernet:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket_connection = None

        # 连接以太网
        self.connect()

    def connect(self):
        try:
            self.socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_connection.connect((self.host, self.port))
            print(f"Connected to {self.host}:{self.port}")
        except (socket.error, ConnectionError) as e:
            print(f"Error: {e}")

    def send_data(self, data):
        if self.socket_connection:
            try:
                self.socket_connection.sendall(data.encode('utf-8'))
                print(f"Data sent: {data}")
            except (socket.error, ConnectionError) as e:
                print(f"Error sending data: {e}")
        else:
            print("Not connected to Ethernet.")

    def receive_data(self, buffer_size=1024):
        if self.socket_connection:
            try:
                data = self.socket_connection.recv(buffer_size).decode('utf-8')
                print(f"Received data: {data}")
                return data
            except (socket.error, ConnectionError) as e:
                print(f"Error receiving data: {e}")
                return ""
        else:
            print("Not connected to Ethernet.")
            return ""

    def close_connection(self):
        if self.socket_connection:
            self.socket_connection.close()
            print(f"Connection to {self.host}:{self.port} closed.")

    def __del__(self):
        self.close_connection()



class CAN:
    #执行Linux基础命令类，检查返回结果
    def __init__(self, port, baudrate, timeout):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def connect_serial(self):
        #连接到串口
        try:
            self.serial = serial.Serial(self.port, self.baudrate, self.timeout)
        except serial.SerialException as e:
            print(f"Error: {e}")

    def get_log(self):
        print("")
    
    def key_exists(self):    
        print("")

    def execute_command(self, command, delay):
        """
        执行系统命令，并返回命令的输出，可选地添加等待时间。
        参数：
        - command: 要执行的系统命令。
        - delay: 执行命令前的等待时间（秒）。
        返回：
        - 命令的输出字符串。
        """
        if self.serial:
            self.serial.write(command.encode('utf-8'))
            time.sleep(delay)  # 等待响应
            response = self.serial.read_all().decode('utf-8')
            return response
        else:
            print("Not connected to a serial port.")
            return ""      

    def __del__(self):
        self.close_connection()

    def close_connection(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
            print(f"Connection to {self.port} closed.")


class SPI:
    #执行Linux基础命令类，检查返回结果
    def __init__(self, port, baudrate, timeout):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def connect_serial(self):
        #连接到串口
        try:
            self.serial = serial.Serial(self.port, self.baudrate, self.timeout)
        except serial.SerialException as e:
            print(f"Error: {e}")

    def get_log(self):
        print("")
    
    def key_exists(self):    
        print("")

    def execute_command(self, command, delay):
        """
        执行系统命令，并返回命令的输出，可选地添加等待时间。
        参数：
        - command: 要执行的系统命令。
        - delay: 执行命令前的等待时间（秒）。
        返回：
        - 命令的输出字符串。
        """
        if self.serial:
            self.serial.write(command.encode('utf-8'))
            time.sleep(delay)  # 等待响应
            response = self.serial.read_all().decode('utf-8')
            return response
        else:
            print("Not connected to a serial port.")
            return ""      

    def __del__(self):
        self.close_connection()

    def close_connection(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
            print(f"Connection to {self.port} closed.")



class BOOT(UART):
    def __init__(self, port, baudrate, output_file):
        super().__init__(port, baudrate, output_file, 'adcu login:', 1)



def main():
    # 串口配置
    with open('data.json', 'r') as json_file:
        data = json.load(json_file)
    serial_port = data.get('serial_port')
    serial_baudrate = data.get('serial_baudrate')
    serial_timeout = data.get('serial_timeout')
    # print(serial_port)
    # print(serial_baudrate)
    # print(serial_timeout)





    # A_core = BOOT(serial_port, serial_baudrate, 'L_boot_log.txt')  
    # A_core.connect_serial()
    # print("Power on")
    # A_core.read_and_save_log('w', 0)

    # basic = Basic(serial_port, serial_baudrate)
    # basic.connect_serial()
    # # response = uart.execute_command('root\n cd ..\n', 0.5)
    # f = basic.execute_command('root\ncd ..\n', 0.5)
    # basic.S_L_bring_up_test()
    # basic.S_L_DDR_memory_info_test()
    # basic.S_L_CPU_load_test()
    # basic.S_L_EMMC_partition_test()
    # basic.S_L_SPI_Nand_Driver_test()


    #R核--------------------------------------

    R_core = BOOT(serial_port, serial_baudrate,'R_boot_log.txt')  
    R_core.connect_serial()
    print("Power on")
    R_core.read_and_save_log('w', 0)

    rbasic = R_Basic(serial_port, serial_baudrate)
    rbasic.connect_serial()
    rbasic.execute_command('\n', 0.5)
    rbasic.S_R_bring_up_test()



if __name__ == "__main__":
    main()
