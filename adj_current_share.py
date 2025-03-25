import os
import csv
from datetime import datetime
from typing import Union, Tuple, Generator
import re
import math


def hex_to_unsigned_fixed(hex_str: str, int_bits: int, frac_bits: int) -> float:
    """
    Converts a hexadecimal string to an unsigned fixed-point number.

    Args:
        hex_str (str): The hexadecimal string to convert.
        int_bits (int): The number of integer bits in the fixed-point representation.
        frac_bits (int): The number of fractional bits in the fixed-point representation.

    Returns:
        float: The converted unsigned fixed-point number.
    """
    total_bits = int_bits + frac_bits
    max_value = (1 << total_bits) - 1
    num = int(hex_str, 16) & max_value
    return num / (1 << frac_bits)


def float_to_unsigned_fixed_hex(value: float, int_bits: int, frac_bits: int) -> str:
    """
    Converts a floating-point number to an unsigned fixed-point hexadecimal string.

    Args:
        value (float): The floating-point number to convert.
        int_bits (int): The number of integer bits in the fixed-point representation.
        frac_bits (int): The number of fractional bits in the fixed-point representation.

    Returns:
        str: The converted unsigned fixed-point hexadecimal string.
    """
    total_bits = int_bits + frac_bits  # Total number of bits in the fixed-point representation
    max_value = (1 << total_bits) - 1  # Maximum value that can be represented with the given bits
    scaled = math.floor(value * (1 << frac_bits))  # Scale the value by the fractional bits
    # Unsigned saturation to ensure the value fits within the bit limits
    saturated = max(min(scaled, max_value), 0)
    hex_length = (total_bits + 3) // 4  # Calculate the length of the hex string
    return f"{saturated:0{hex_length}X}"  # Format the saturated value as a hex string


def float_to_unsigned_fixed(value: float, int_bits: int, frac_bits: int) -> float:
    """
    Converts a floating-point number to an unsigned fixed-point number.

    Args:
        value (float): The floating-point number to convert.
        int_bits (int): The number of integer bits in the fixed-point representation.
        frac_bits (int): The number of fractional bits in the fixed-point representation.

    Returns:
        float: The converted unsigned fixed-point number.
    """
    total_bits = int_bits + frac_bits  # Total number of bits in the fixed-point representation
    max_value = (1 << total_bits) - 1  # Maximum value that can be represented with the given bits
    scaled = math.floor(value * (1 << frac_bits))  # Scale the value by the fractional bits
    # Unsigned saturation to ensure the value fits within the bit limits
    saturated = max(min(scaled, max_value), 0)
    return saturated / (1 << frac_bits)  # Convert back to float


def hex_to_signed_fixed(hex_str: str, int_bits: int, frac_bits: int) -> float:
    """
    将有符号十六进制字符串转换为定点数
    
    Args:
        hex_str (str): 十六进制字符串
        int_bits (int): 整数部分位数
        frac_bits (int): 小数部分位数
    Returns:
        float: 转换后的定点数
    """
    total_bits = int_bits + frac_bits
    mask = (1 << total_bits) - 1
    num = int(hex_str, 16) & mask  # 保留有效位数
    
    # 符号位判断（最高位）
    if num & (1 << (total_bits - 1)):
        num -= (1 << total_bits)  # 转换为负数
        
    return num / (1 << frac_bits)


def float_to_signed_fixed_hex(value: float, int_bits: int, frac_bits: int) -> str:
    """
    将浮点数转换为有符号定点数的十六进制表示
    
    Args:
        value (float): 输入浮点数
        int_bits (int): 整数部分位数
        frac_bits (int): 小数部分位数
    Returns:
        str: 十六进制字符串
    """
    total_bits = int_bits + frac_bits
    max_val = (1 << (total_bits-1)) - 1   # 最大值：2^(n-1)-1
    min_val = -(1 << (total_bits-1))      # 最小值：-2^(n-1)
    
    scaled = math.floor(value * (1 << frac_bits))  # 数值缩放
    saturated = max(min(scaled, max_val), min_val)  # 饱和处理
    
    # 转换为补码形式
    saturated_unsigned = saturated & ((1 << total_bits) - 1)
    hex_length = (total_bits + 3) // 4
    return f"{saturated_unsigned:0{hex_length}X}"


def float_to_signed_fixed(value: float, int_bits: int, frac_bits: int) -> float:
    """
    浮点数转有符号定点数（带饱和处理）
    
    Args:
        value (float): 输入浮点数
        int_bits (int): 整数部分位数
        frac_bits (int): 小数部分位数
    Returns:
        float: 转换后的定点数
    """
    total_bits = int_bits + frac_bits
    max_val = (1 << (total_bits-1)) - 1
    min_val = -(1 << (total_bits-1))
    
    scaled = math.floor(value * (1 << frac_bits))  # 数值缩放
    saturated = max(min(scaled, max_val), min_val)  # 饱和处理
    return saturated / (1 << frac_bits)


def get_hex_input(prompt: str, length: int) -> str:
    """安全获取HEX输入 (符合ISO 26262 ASIL-B标准)"""
    hex_pattern = re.compile(f"^[0-9A-F]{{{length}}}$")  # 预编译正则表达式
    
    while True:
        try:
            raw_input = input(prompt).strip().upper()
            
            # 退出指令检测
            if raw_input in ('Q', 'EXIT'):
                return raw_input
                
            # 空值检测
            if not raw_input:
                raise ValueError("输入不能为空")
                
            # 非法字符检测（精确到具体字符）
            if not hex_pattern.match(raw_input):
                invalid_chars = set(re.findall(r"[^0-9A-F]", raw_input))
                raise ValueError(f"包含非法字符：{', '.join(invalid_chars)}")
            
            # 长度验证（独立检测以区分错误类型）
            if len(raw_input) != length:
                raise ValueError(f"需要{length}位字符，实际{len(raw_input)}位")
                
            return raw_input
            
        except ValueError as ve:
            # 精确错误提示
            error_msg = f"无效输入: {str(ve)}" if str(ve) else "格式错误"
            print(f"! {error_msg}，请重新输入 (Q退出)")
            
        except KeyboardInterrupt:
            print("\n输入已终止")
            return 'Q'


def get_two_hex_input(prompt: str, length1: int, length2: int) -> Tuple[str, str]:
    """安全获取双HEX输入（符合ISO 26262 ASIL-B标准）
    
    参数：
        prompt: 输入提示语
        length1: 第一个HEX长度
        length2: 第二个HEX长度
    
    返回：
        包含两个合法HEX字符串的元组，或退出指令
    
    安全机制：
        1. 输入分割验证
        2. 独立字符集检查
        3. 精确长度校验
        4. 错误类型隔离
    """
    # 预编译正则表达式（提高性能）
    hex_pattern1 = re.compile(f"^[0-9A-F]{{{length1}}}$")
    hex_pattern2 = re.compile(f"^[0-9A-F]{{{length2}}}$")
    
    while True:
        try:
            raw_input = input(prompt).strip().upper()
            
            # 退出指令检测
            if raw_input in ('Q', 'EXIT'):
                return (raw_input, '')
                
            # 分割输入
            parts = raw_input.split()
            if len(parts) != 2:
                raise ValueError("需要两个HEX值，用空格分隔")
                
            hex1, hex2 = parts
            
            # 第一HEX验证
            if not hex_pattern1.match(hex1):
                invalid_chars = set(re.findall(r"[^0-9A-F]", hex1))
                raise ValueError(f"HEX1非法字符：{', '.join(invalid_chars)}")
                
            # 第二HEX验证
            if not hex_pattern2.match(hex2):
                invalid_chars = set(re.findall(r"[^0-9A-F]", hex2))
                raise ValueError(f"HEX2非法字符：{', '.join(invalid_chars)}")
                
            return (hex1, hex2)
            
        except ValueError as ve:
            error_type = str(ve)
            if "需要两个HEX值" in error_type:
                msg = "输入格式错误：需要两个值用空格分隔"
            elif "HEX1" in error_type:
                msg = f"第一个值错误：{error_type.split('：')[-1]}"
            elif "HEX2" in error_type:
                msg = f"第二个值错误：{error_type.split('：')[-1]}"
            else:
                msg = "未知格式错误"
                
            print(f"! {msg}，请重新输入 (Q退出)")
            
        except KeyboardInterrupt:
            print("\n输入已终止")
            return ('Q', )
        

def get_positive_int(prompt: str) -> int:
    """安全获取正整数输入"""
    while True:
        try:
            value = int(input(prompt))
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            print("请输入有效的正整数（>0）")


def get_non_zero_integer(prompt: str) -> int:
    """安全获取非零整数（支持正负数）"""
    while True:
        try:
            value = int(input(prompt))
            if value == 0:
                print("不能输入零，请重新输入")
                continue
            return value
        except ValueError:
            print("请输入有效的整数")


def get_non_negative_int(prompt: str) -> int:
    """安全获取非负整数输入（≥0）"""
    while True:
        try:
            value = int(input(prompt))
            if value < 0:
                raise ValueError
            return value
        except ValueError:
            print("请输入有效的非负整数（>=0）")


def adj_error_algorithm(
        hex_data: str, # u12.0（12位无符号整数）
        hex_k1: str,   # u6.6（6位整数 + 6位小数）
        hex_share: str # u12.0（12位无符号整数）
) -> str:
    """
    变量标注规则：
    u[m].[n] = 无符号定点数（m位整数位，n位小数位）
    s[m].[n] = 有符号定点数（1位符号位，m位整数位，n位小数位）
    """
    # 输入转换
    data = hex_to_unsigned_fixed(hex_data, 12, 0)
    k1 = hex_to_unsigned_fixed(hex_k1, 6, 6)
    share = hex_to_unsigned_fixed(hex_share, 12, 0)
    
    # 计算
    error = share - data * k1
    return float_to_signed_fixed_hex(error, 20, 6) # s19.6（19位整数位，6位小数位）


class NContinuousProcessor:
    def __init__(self, 
                 th_pos_hex: str,   # s19.0
                 th_neg_hex: str,   # s19.0
                 th_num_pos_hex: str,   # u5.0 (0-31)
                 th_num_neg_hex: str):  # u5.0 (0-31)

        # 输入安全转换
        self.th_pos = hex_to_signed_fixed(th_pos_hex, 20, 0)
        self.th_neg = hex_to_signed_fixed(th_neg_hex, 20, 0)
        self.th_num_pos =hex_to_unsigned_fixed(th_num_pos_hex, 5, 0)
        self.th_num_neg = hex_to_unsigned_fixed(th_num_neg_hex, 5, 0)
        
        # 状态初始化
        self.current_pos = 0
        self.current_neg = 0
        self.data = 0
        self.state = True  # True: pos，False: neg
        self.state_out = True  # True: pos，False: neg, 对外输出


    def process_data(self, new_data_hex: str) -> Tuple[int, int, bool, str]:
        # 输入安全转换
        data = hex_to_signed_fixed(new_data_hex, 20, 6)
        
        # 计数器更新
        if data > self.th_pos:
            if self.state: # pos
                self.current_pos += 1
            else: # neg
                self._reset_counters()
                self.current_pos += 1
                self.state = True
        elif data < self.th_neg:
            if not self.state:
                self.current_neg += 1
            else:
                self._reset_counters()
                self.current_neg += 1
                self.state = False
        else:
            self._reset_counters()
        
        # 状态判断
        if self.current_pos > self.th_num_pos:
            self.current_pos = self.th_num_pos + 1
            self.data = data
            self.state_out = True
        elif self.current_neg >= self.th_num_neg:
            self.current_neg = self.th_num_neg + 1
            self.data = data
            self.state_out = False

        return self.current_pos, self.current_neg, self.state_out, float_to_signed_fixed_hex(self.data, 20, 6)
       

    def _reset_counters(self):
        """安全计数器重置"""
        self.current_pos = 0
        self.current_neg = 0


class PIProcessor:
    def __init__(self, 
                 kp1_hex: str,   # u0.10
                 kp1_th_hex: str,   # u19.0
                 kp2_hex: str,   # u0.10
                 kp2_th_hex: str,   # u19.0

                 ki1_hex: str,   # u0.10
                 ki1_th_hex: str,   # u19.0
                 ki2_hex: str,   # u0.10
                 ki2_th_hex: str,   # u19.0
                 
                 i_clp_pos_hex: str,   # s19.10
                 i_clp_neg_hex: str,   # s19.10
                 clp_en: bool):  

        # 输入安全转换
        self.kp1 = hex_to_unsigned_fixed(kp1_hex, 0, 10)
        self.kp1_th = hex_to_unsigned_fixed(kp1_th_hex, 19, 0)
        self.kp2 = hex_to_unsigned_fixed(kp2_hex, 0, 10)
        self.kp2_th = hex_to_unsigned_fixed(kp2_th_hex, 19, 0)

        self.ki1 = hex_to_unsigned_fixed(ki1_hex, 0, 10)
        self.ki1_th = hex_to_unsigned_fixed(ki1_th_hex, 19, 0)
        self.ki2 = hex_to_unsigned_fixed(ki2_hex, 0, 10)
        self.ki2_th = hex_to_unsigned_fixed(ki2_th_hex, 19, 0)

        self.i_clp_pos =hex_to_signed_fixed(i_clp_pos_hex, 20, 10)
        self.i_clp_neg = hex_to_signed_fixed(i_clp_neg_hex, 20, 10)
        self.clp_en = clp_en
        
        # 状态初始化
        self.result_p = 0
        self.result_i = 0
        self.result_i_last = 0
        self.result_i_before_clp = 0
        self.result_pi = 0


    def pi_process(self, error_hex: str) -> Tuple[str, str, str]:
        # 输入安全转换
        error = hex_to_signed_fixed(error_hex, 20, 6)
        
        # 计算(分段)
        if error > 0:
            if error < self.kp1_th:
                self.result_p = 0
            elif error < self.kp2_th:
                self.result_p = float_to_signed_fixed((error - self.kp1_th) * self.kp1, 20, 10)
            else:
                self.result_p = float_to_signed_fixed((error - self.kp2_th) * self.kp2 + (self.kp2_th - self.kp1_th) * self.kp1, 20, 10)
        else:
            if error > -self.kp1_th:
                self.result_p = 0
            elif error > -self.kp2_th:
                self.result_p = float_to_signed_fixed((error + self.kp1_th) * self.kp1, 20, 10)
            else:
                self.result_p = float_to_signed_fixed((error + self.kp2_th) * self.kp2 - (self.kp2_th - self.kp1_th) * self.kp1, 20, 10)

        if error > 0:
            if error < self.ki1_th:
                i = 0
            elif error < self.ki2_th:
                i = float_to_signed_fixed((error - self.ki1_th) * self.ki1, 20, 10)
            else:
                i = float_to_signed_fixed((error - self.ki2_th) * self.ki2 + (self.ki2_th - self.ki1_th) * self.ki1, 20, 10)
        else:
            if error > -self.ki1_th:
                i = 0
            elif error > -self.ki2_th:
                i = float_to_signed_fixed((error + self.ki1_th) * self.ki1, 20, 10)
            else:
                i = float_to_signed_fixed((error + self.ki2_th) * self.ki2 - (self.ki2_th - self.ki1_th) * self.ki1, 20, 10)

        self.result_i_before_clp = float_to_signed_fixed(self.result_i_last + i, 20, 10)

        if self.clp_en:
            if self.result_i_before_clp > self.i_clp_pos:
                self.result_i = self.i_clp_pos
            elif self.result_i_before_clp < self.i_clp_neg:
                self.result_i = self.i_clp_neg
            else:
                self.result_i = self.result_i_before_clp
        else:
            self.result_i = self.result_i_before_clp
        self.result_i_last = self.result_i
        self.result_pi = self.result_p + self.result_i

        return float_to_signed_fixed_hex(self.result_p, 20, 10), float_to_signed_fixed_hex(self.result_i, 20, 10), float_to_signed_fixed_hex(self.result_pi, 21, 10)
       

def correct_algorithm(
        pi_result_hex: str, # s20.10
        k2_hex: str,   # u6.6
        offset_hex: str,   # s6.4
        clp_pos_hex: str,   # s6.4
        clp_neg_hex: str,   # s6.4
        clp_en: bool
) -> str:
    """
    变量标注规则：
    u[m].[n] = 无符号定点数（m位整数位，n位小数位）
    s[m].[n] = 有符号定点数（1位符号位，m位整数位，n位小数位）
    """
    # 输入转换
    pi_result = hex_to_signed_fixed(pi_result_hex, 20, 10)
    k2 = hex_to_unsigned_fixed(k2_hex, 6, 6)
    offset = hex_to_signed_fixed(offset_hex, 7, 4)
    
    
    # 计算
    pi_result_after_k = float_to_signed_fixed(pi_result * k2, 27, 5)
    pi_result_after_offset = float_to_signed_fixed(pi_result_after_k + offset, 28, 4)
    if clp_en:
        clp_pos =hex_to_signed_fixed(clp_pos_hex, 7, 4)
        clp_neg = hex_to_signed_fixed(clp_neg_hex, 7, 4)
        if pi_result_after_offset > clp_pos:
            pi_result_after_clp = clp_pos
        elif pi_result_after_offset < clp_neg:
            pi_result_after_clp = clp_neg
        else:
            pi_result_after_clp = float_to_signed_fixed(pi_result_after_offset, 7, 4)
    else:
        pi_result_after_clp = float_to_signed_fixed(pi_result_after_offset, 7, 4)
    return float_to_signed_fixed_hex(pi_result_after_offset, 28, 4), float_to_signed_fixed_hex(pi_result_after_clp, 7, 4)


def generate_batch_hex(start: int, end: int, step: int) -> Generator[str, None, None]:
    """生成HEX序列的生成器"""

    if step == 0:
        raise ValueError("步长不能为0")
    if (step > 0 and start > end) or (step < 0 and start < end):
        raise ValueError("无效的步长方向")

    current = start
    while (current <= end) if step > 0 else (current >= end):
        yield f"{current:03X}"
        current += step


def get_batch_input() -> Tuple[str, str, int]:
    """获取批量输入参数"""
    start = get_hex_input("起始值(7位HEX): ", 7)
    end = get_hex_input("结束值(7位HEX): ", 7)
    step = get_non_zero_integer("步长(十进制整数): ")
    return start, end, step


def get_script_dir() -> str:
    """获取脚本所在目录的绝对路径"""
    return os.path.dirname(os.path.abspath(__file__))


def adj_process(hex_error: str, params: dict) -> Tuple[int, int, bool, str, str, str, str, str]:
    error = hex_to_signed_fixed(hex_error, 20, 6)
    if params['enable_count']:
        current_pos, current_neg, state_out, hex_error_after_count = params['count_class'].process_data(hex_error)
        float_error_after_count = hex_to_signed_fixed(hex_error_after_count, 20, 6)
        print(f"POS: {current_pos}, NEG: {current_neg}, STATE: {state_out}, error_after_count: {hex_error_after_count} → {float_error_after_count:.10f}")
    else:
        hex_error_after_count = hex_error
        float_error_after_count = hex_to_signed_fixed(hex_error_after_count, 20, 6)
        print(f"error_after_count: {hex_error_after_count} → {float_error_after_count:.10f}")
    
    if params['enable_pi']:
        hex_result_p, hex_result_i, hex_result_pi = params['pi_class'].pi_process(hex_error_after_count)
        float_result_p = hex_to_signed_fixed(hex_result_p, 20, 10)
        float_result_i = hex_to_signed_fixed(hex_result_i, 20, 10)
        float_result_pi = hex_to_signed_fixed(hex_result_pi, 21, 10)
        print(f"result_p: {hex_result_p} → {float_result_p:.10f}")
        print(f"result_i: {hex_result_i} → {float_result_i:.10f}")
        print(f"result_pi: {hex_result_pi} → {float_result_pi:.10f}")
    else:
        result_pi = float_error_after_count
        hex_result_pi = float_to_signed_fixed_hex(result_pi, 21, 10)
        float_result_pi = hex_to_signed_fixed(hex_result_pi, 21, 10)
        print(f"result_pi: {hex_result_pi} → {float_result_pi:.10f}")
    
    hex_pi_result_after_offset, hex_current_share_adj = correct_algorithm(hex_result_pi, params['k2_hex'], params['offset_hex'], params['clp_pos_hex'], params['clp_neg_hex'], params['enable_adj_clp'])
    float_pi_result_after_offset = hex_to_signed_fixed(hex_pi_result_after_offset, 28, 4)
    float_current_share_adj = hex_to_signed_fixed(hex_current_share_adj, 7, 4)
    print(f"pi_result_after_offset: {hex_pi_result_after_offset} → {float_pi_result_after_offset:.10f}")
    print(f"current_share_adj: {hex_current_share_adj} → {float_current_share_adj:.10f}")

    return_list = []
    if params['enable_count']:
        return_list.extend([current_pos, current_neg, state_out])
    else:
        return_list.extend([0, 0, True])
    return_list.extend([hex_error_after_count])
    if params['enable_pi']:
        return_list.extend([hex_result_p, hex_result_i])
    else:
        return_list.extend(['0', '0'])
    return_list.extend([hex_result_pi, hex_pi_result_after_offset, hex_current_share_adj])

    return return_list




def main():
    # 交互式输入
    print("=== ADJ CALCULATOR ===")
    print("输入HEX字符串时不区分大小写")
    print("输入Q退出程序")

    # 选择输入模式
    while True:
        mode = input("\n请选择模式：\n1. 单次输入\n2. 批量生成\n3. 重复测试\n选择(1/2/3): ").strip()
        if mode in ('1', '2', '3'):
            break
        print("无效选择，请重新输入")

    # 功能使能配置
    config = {
        'enable_test_mode': input("启用test mode？(Y/N): ").upper() == 'Y',
        'enable_count': input("启用Continuous？(Y/N): ").upper() == 'Y',
        'enable_pi': input("启用PI？(Y/N): ").upper() == 'Y',
        'enable_adj_clp': input("启用adj clamp？(Y/N): ").upper() == 'Y',
    }

    error_params = {}
    if not config['enable_test_mode']:
        error_params = {
            'adj_k1_hex': get_hex_input("请输入K1（u6.6）：", 3),
        }
        
    continue_params = {}
    if config['enable_count']:
        continue_params = {
            'th_pos_hex': get_hex_input("请输入TH_POS（s19.0）：", 5),
            'th_neg_hex': get_hex_input("请输入TH_NEG（s19.0）：", 5),
            'th_num_pos_hex': get_hex_input("请输入TH_NUM_POS（u5.0）：", 2),
            'th_num_neg_hex': get_hex_input("请输入TH_NUM_NEG（u5.0）：", 2),
        }
        continue_params['count_class'] = NContinuousProcessor(continue_params['th_pos_hex'], continue_params['th_neg_hex'], continue_params['th_num_pos_hex'], continue_params['th_num_neg_hex'])
    
    pi_params = {}
    if config['enable_pi']:
        pi_params = {
            'kp1_hex': get_hex_input("请输入KP1（u0.10）：", 3),
            'kp1_th_hex': get_hex_input("请输入KP1_TH（u19.0）：", 5),
            'kp2_hex': get_hex_input("请输入KP2（u0.10）：", 3),
            'kp2_th_hex': get_hex_input("请输入KP2_TH（u19.0）：", 5),

            'ki1_hex': get_hex_input("请输入KI1（u0.10）：", 3),
            'ki1_th_hex': get_hex_input("请输入KI1_TH（u19.0）：", 5),
            'ki2_hex': get_hex_input("请输入KI2（u0.10）：", 3),
            'ki2_th_hex': get_hex_input("请输入KI2_TH（u19.0）：", 5),

            'clp_en': input("启用CLP？(Y/N): ").upper() == 'Y',
            # 'i_clp_pos_hex': get_hex_input("请输入I_CLP_POS（s19.10）：", 8),
            # 'i_clp_neg_hex': get_hex_input("请输入I_CLP_NEG（s19.10）：", 8),   
            # 'pi_class': PIProcessor('kp1_hex', 'kp1_th_hex', 'kp2_hex', 'kp2_th_hex', 'ki1_hex', 'ki1_th_hex', 'ki2_hex', 'ki2_th_hex', 'i_clp_pos_hex', 'i_clp_neg_hex', 'clp_en'),
        }
        if pi_params['clp_en']:
            pi_params['i_clp_pos_hex'] = get_hex_input("请输入I_CLP_POS（s19.10）：", 8)
            pi_params['i_clp_neg_hex'] = get_hex_input("请输入I_CLP_NEG（s19.10）：", 8)
        else:
            pi_params['i_clp_pos_hex'] = '00000000'
            pi_params['i_clp_neg_hex'] = '00000000'
        pi_params['pi_class'] = PIProcessor(pi_params['kp1_hex'], pi_params['kp1_th_hex'], pi_params['kp2_hex'], pi_params['kp2_th_hex'], pi_params['ki1_hex'], pi_params['ki1_th_hex'], pi_params['ki2_hex'], pi_params['ki2_th_hex'], pi_params['i_clp_pos_hex'], pi_params['i_clp_neg_hex'], pi_params['clp_en'])
    
    adj_clp_params = {            
        'clp_pos_hex': '',
        'clp_neg_hex': '',}
    if config['enable_adj_clp']:
        adj_clp_params = {
            'clp_pos_hex': get_hex_input("请输入CLP_POS（s6.4）：", 3),
            'clp_neg_hex': get_hex_input("请输入CLP_NEG（s6.4）：", 3),
        }

    # 基础参数输入
    base_params = {
        'k2_hex': get_hex_input("比例系数K2(u6.6): ", 3),
        'offset_hex': get_hex_input("offset(s6.4): ", 3),
    }

    params = {**config, **error_params, **continue_params, **pi_params, **adj_clp_params, **base_params}


    # 数据处理逻辑
    while True:
        if mode == '1':
            if config['enable_test_mode']:
                hex_error = get_hex_input("请输入DATA（s19.6）：", 7)
                if hex_error in ('Q', 'EXIT'):
                    return
            else:
                hex_data, hex_share = get_two_hex_input("输入data(u12.0)和share(u12.0)（格式：HEX3 HEX3）:", 3, 3)
                if hex_data in ('Q', 'EXIT'):
                    return
                hex_error = adj_error_algorithm(hex_data, params['adj_k1_hex'], hex_share)

            current_pos, current_neg, state_out, hex_error_after_count, hex_result_p, hex_result_i, hex_result_pi, hex_pi_result_after_offset, hex_current_share_adj = adj_process(hex_error, params)
            float_error_after_count = hex_to_signed_fixed(hex_error_after_count, 20, 6)
            float_result_p = hex_to_signed_fixed(hex_result_p, 20, 10)
            float_result_i = hex_to_signed_fixed(hex_result_i, 20, 10)
            float_result_pi = hex_to_signed_fixed(hex_result_pi, 21, 10)
            float_pi_result_after_offset = hex_to_signed_fixed(hex_pi_result_after_offset, 28, 4)
            float_current_share_adj = hex_to_signed_fixed(hex_current_share_adj, 7, 4)

            print("\n【处理结果】")
            if config['enable_count']:
                print(f"Current POS(int): {current_pos}")
                print(f"Current NEG(int): {current_neg}")
                print(f"State Out(bool): {state_out}")
            print(f"Error After Count(s19.6): {hex_error_after_count} → {float_error_after_count:.10f}")

            if config['enable_pi']:
                print(f"Result P(s19.10): {hex_result_p} → {float_result_p:.10f}")
                print(f"Result I(s19.10): {hex_result_i} → {float_result_i:.10f}")
            print(f"Result PI(s20.10): {hex_result_pi} → {float_result_pi:.10f}")
            print(f"PI Result After Offset(s28.4): {hex_pi_result_after_offset} → {float_pi_result_after_offset:.10f}")
            print(f"Current Share Adj(s6.4): {hex_current_share_adj} → {float_current_share_adj:.10f}")
        
        elif mode == '2':
            if not config['enable_test_mode']:
                print("非 Test mode不支持批量生成")
                return
            else:
                start_hex, end_hex, step = get_batch_input()
                start = int(hex_to_signed_fixed(start_hex, 26, 0))
                end = int(hex_to_signed_fixed(end_hex, 26, 0))
                error_list = list(generate_batch_hex(start, end, step))
                # 创建CSV文件
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                script_dir = get_script_dir()
                filename = f"adj_results_{timestamp}.csv"
                filename_result_p = f"result_p_{timestamp}.txt"
                filename_result_i = f"result_i_{timestamp}.txt"
                filename_result_pi = f"result_pi_{timestamp}.txt"
                filename_pi_result_after_offset = f"pi_result_after_offset_{timestamp}.txt"
                filename_current_share_adj = f"current_share_adj_{timestamp}.txt"
                full_path = os.path.join(script_dir, filename)
                full_path_result_p = os.path.join(script_dir, filename_result_p)
                full_path_result_i = os.path.join(script_dir, filename_result_i)
                full_path_result_pi = os.path.join(script_dir, filename_result_pi)
                full_path_pi_result_after_offset = os.path.join(script_dir, filename_pi_result_after_offset)
                full_path_current_share_adj = os.path.join(script_dir, filename_current_share_adj)

                with open(full_path, 'w', newline='') as csv_file:
                    csv_writer = csv.writer(csv_file)
                    # 写入表头
                    csv_writer.writerow([
                        "ERROR(HEX)",
                        "ERROR_AFTER_COUNT(HEX)",
                        "RESULT_P(HEX)", "RESULT_P(float)",
                        "RESULT_I(HEX)", "RESULT_I(float)",
                        "RESULT_PI(HEX)", "RESULT_PI(float)",
                        "PI_RESULT_AFTER_OFFSET(HEX)", "PI_RESULT_AFTER_OFFSET(float)",
                        "CURRENT_SHARE_ADJ(HEX)", "CURRENT_SHARE_ADJ(float)"
                    ])
                    # 批量处理
                    for error in error_list:
                        current_pos, current_neg, state_out, hex_error_after_count, hex_result_p, hex_result_i, hex_result_pi, hex_pi_result_after_offset, hex_current_share_adj = adj_process(error, params)
                        float_error_after_count = hex_to_signed_fixed(hex_error_after_count, 20, 6)
                        float_result_p = hex_to_signed_fixed(hex_result_p, 20, 10)
                        float_result_i = hex_to_signed_fixed(hex_result_i, 20, 10)
                        float_result_pi = hex_to_signed_fixed(hex_result_pi, 21, 10)
                        float_pi_result_after_offset = hex_to_signed_fixed(hex_pi_result_after_offset, 28, 4)
                        float_current_share_adj = hex_to_signed_fixed(hex_current_share_adj, 7, 4)

                        dec_error_after_count = hex_to_signed_fixed(hex_error_after_count, 26, 0)
                        dec_result_p = hex_to_signed_fixed(hex_result_p, 30, 0)
                        dec_result_i = hex_to_signed_fixed(hex_result_i, 30, 0)
                        dec_result_pi = hex_to_signed_fixed(hex_result_pi, 31, 0)
                        dec_pi_result_after_offset = hex_to_signed_fixed(hex_pi_result_after_offset, 32, 0)
                        dec_current_share_adj = hex_to_signed_fixed(hex_current_share_adj, 11, 0)
                        # dec_error_after_count = int(hex_error_after_count, 16)
                        # dec_result_p = int(hex_result_p, 16)
                        # dec_result_i = int(hex_result_i, 16)
                        # dec_result_pi = int(hex_result_pi, 16)
                        # dec_pi_result_after_offset = int(hex_pi_result_after_offset, 16)
                        # dec_current_share_adj = int(hex_current_share_adj, 16)

                        # 写入CSV
                        csv_writer.writerow([
                            error, hex_error_after_count,
                            hex_result_p, float_result_p,
                            hex_result_i, float_result_i,
                            hex_result_pi, float_result_pi,
                            hex_pi_result_after_offset, float_pi_result_after_offset,
                            hex_current_share_adj, float_current_share_adj
                        ])

                        # 写入TXT
                        with open(full_path_result_p, 'a', encoding='utf-8') as f:
                            f.write(f"{dec_result_p}\n")
                        with open(full_path_result_i, 'a', encoding='utf-8') as f:
                            f.write(f"{dec_result_i}\n")
                        with open(full_path_result_pi, 'a', encoding='utf-8') as f:
                            f.write(f"{dec_result_pi}\n")
                        with open(full_path_pi_result_after_offset, 'a', encoding='utf-8') as f:
                            f.write(f"{dec_pi_result_after_offset}\n")
                        with open(full_path_current_share_adj, 'a', encoding='utf-8') as f:
                            f.write(f"{dec_current_share_adj}\n")

                        # 控制台输出
                        print("\n【处理结果】")
                        print(f"ERROR(HEX): {error}")
                        if config['enable_count']:
                            print(f"Current POS(int): {current_pos}")
                            print(f"Current NEG(int): {current_neg}")
                            print(f"State Out(bool): {state_out}")
                        print(f"ERROR_AFTER_COUNT(HEX): {hex_error_after_count} → {float_error_after_count:.10f}")
                        if config['enable_pi']:
                            print(f"RESULT_P(HEX): {hex_result_p} → {float_result_p:.10f}")
                            print(f"RESULT_I(HEX): {hex_result_i} → {float_result_i:.10f}")
                        print(f"RESULT_PI(HEX): {hex_result_pi} → {float_result_pi:.10f}")
                        print(f"PI_RESULT_AFTER_OFFSET(HEX): {hex_pi_result_after_offset} → {float_pi_result_after_offset:.10f}")
                        print(f"CURRENT_SHARE_ADJ(HEX): {hex_current_share_adj} → {float_current_share_adj:.10f}")
            break  # 批量处理完成后退出循环   

        elif mode == '3':
            if not config['enable_test_mode']:
                hex_error = get_hex_input("请输入DATA（s19.6）：", 7)
                if hex_error in ('Q', 'EXIT'):
                    return
            else:
                hex_data, hex_share = get_two_hex_input("输入data(u12.0)和share(u12.0)（格式：HEX3 HEX3）:", 3, 3)
                if hex_data in ('Q', 'EXIT'):
                    return
                hex_error = adj_error_algorithm(hex_data, params['adj_k1_hex'], hex_share)
            
            n_times = get_positive_int("重复次数: ")
            error_list = [hex_error] * n_times  # 生成重复数据列表
            # 创建CSV文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            script_dir = get_script_dir()
            filename = f"adj_results_{timestamp}.csv"
            filename_result_p = f"result_p_{timestamp}.txt"
            filename_result_i = f"result_i_{timestamp}.txt"
            filename_result_pi = f"result_pi_{timestamp}.txt"
            filename_pi_result_after_offset = f"pi_result_after_offset_{timestamp}.txt"
            filename_current_share_adj = f"current_share_adj_{timestamp}.txt"
            full_path = os.path.join(script_dir, filename)
            full_path_result_p = os.path.join(script_dir, filename_result_p)
            full_path_result_i = os.path.join(script_dir, filename_result_i)
            full_path_result_pi = os.path.join(script_dir, filename_result_pi)
            full_path_pi_result_after_offset = os.path.join(script_dir, filename_pi_result_after_offset)
            full_path_current_share_adj = os.path.join(script_dir, filename_current_share_adj)

            with open(full_path, 'w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                # 写入表头
                csv_writer.writerow([
                    "ERROR(HEX)",
                    "ERROR_AFTER_COUNT(HEX)",
                    "RESULT_P(HEX)", "RESULT_P(float)",
                    "RESULT_I(HEX)", "RESULT_I(float)",
                    "RESULT_PI(HEX)", "RESULT_PI(float)",
                    "PI_RESULT_AFTER_OFFSET(HEX)", "PI_RESULT_AFTER_OFFSET(float)",
                    "CURRENT_SHARE_ADJ(HEX)", "CURRENT_SHARE_ADJ(float)"
                ])
                # 批量处理
                for error in error_list:
                    current_pos, current_neg, state_out, hex_error_after_count, hex_result_p, hex_result_i, hex_result_pi, hex_pi_result_after_offset, hex_current_share_adj = adj_process(error, params)
                    float_error_after_count = hex_to_signed_fixed(hex_error_after_count, 20, 6)
                    float_result_p = hex_to_signed_fixed(hex_result_p, 20, 10)
                    float_result_i = hex_to_signed_fixed(hex_result_i, 20, 10)
                    float_result_pi = hex_to_signed_fixed(hex_result_pi, 21, 10)
                    float_pi_result_after_offset = hex_to_signed_fixed(hex_pi_result_after_offset, 28, 4)
                    float_current_share_adj = hex_to_signed_fixed(hex_current_share_adj, 7, 4)

                    dec_error_after_count = int(hex_error_after_count, 16)
                    dec_result_p = int(hex_result_p, 16)
                    dec_result_i = int(hex_result_i, 16)
                    dec_result_pi = int(hex_result_pi, 16)
                    dec_pi_result_after_offset = int(hex_pi_result_after_offset, 16)
                    dec_current_share_adj = int(hex_current_share_adj, 16)

                    # 写入CSV
                    csv_writer.writerow([
                        error, hex_error_after_count,
                        hex_result_p, float_result_p,
                        hex_result_i, float_result_i,
                        hex_result_pi, float_result_pi,
                        hex_pi_result_after_offset, float_pi_result_after_offset,
                        hex_current_share_adj, float_current_share_adj
                    ])

                    # 写入TXT
                    with open(full_path_result_p, 'a', encoding='utf-8') as f:
                        f.write(f"{dec_result_p}\n")
                    with open(full_path_result_i, 'a', encoding='utf-8') as f:
                        f.write(f"{dec_result_i}\n")
                    with open(full_path_result_pi, 'a', encoding='utf-8') as f:
                        f.write(f"{dec_result_pi}\n")
                    with open(full_path_pi_result_after_offset, 'a', encoding='utf-8') as f:
                        f.write(f"{dec_pi_result_after_offset}\n")
                    with open(full_path_current_share_adj, 'a', encoding='utf-8') as f:
                        f.write(f"{dec_current_share_adj}\n")

                    # 控制台输出
                    print("\n【处理结果】")
                    print(f"ERROR(HEX): {error}")
                    if config['enable_count']:
                        print(f"Current POS(int): {current_pos}")
                        print(f"Current NEG(int): {current_neg}")
                        print(f"State Out(bool): {state_out}")
                    print(f"ERROR_AFTER_COUNT(HEX): {hex_error_after_count} → {float_error_after_count:.10f}")
                    if config['enable_pi']:
                        print(f"RESULT_P(HEX): {hex_result_p} → {float_result_p:.10f}")
                        print(f"RESULT_I(HEX): {hex_result_i} → {float_result_i:.10f}")
                    print(f"RESULT_PI(HEX): {hex_result_pi} → {float_result_pi:.10f}")
                    print(f"PI_RESULT_AFTER_OFFSET(HEX): {hex_pi_result_after_offset} → {float_pi_result_after_offset:.10f}")
                    print(f"CURRENT_SHARE_ADJ(HEX): {hex_current_share_adj} → {float_current_share_adj:.10f}")

            break  # 批量处理完成后退出循环  

if __name__ == "__main__":
    main()
