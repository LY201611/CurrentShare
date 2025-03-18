import os
import csv
from datetime import datetime
from typing import Union, Tuple, Generator
import re


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
    scaled = int(value * (1 << frac_bits))  # Scale the value by the fractional bits
    # Unsigned saturation to ensure the value fits within the bit limits
    saturated = max(min(scaled, max_value), 0)
    hex_length = (total_bits + 3) // 4  # Calculate the length of the hex string
    return f"{saturated:0{hex_length}X}"  # Format the saturated value as a hex string


def flot_to_unsigned_fixed(value: float, int_bits: int, frac_bits: int) -> float:
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
    scaled = int(value * (1 << frac_bits))  # Scale the value by the fractional bits
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
    
    scaled = int(value * (1 << frac_bits))  # 数值缩放
    saturated = max(min(scaled, max_val), min_val)  # 饱和处理
    
    # 转换为补码形式
    saturated_unsigned = saturated & ((1 << total_bits) - 1)
    hex_length = (total_bits + 3) // 4
    return f"{saturated_unsigned:0{hex_length}X}"


def flot_to_signed_fixed(value: float, int_bits: int, frac_bits: int) -> float:
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
    
    scaled = int(value * (1 << frac_bits))  # 数值缩放
    saturated = max(min(scaled, max_val), min_val)  # 饱和处理
    return saturated / (1 << frac_bits)







class CurrentShareError(Exception):
    """基础异常类"""
    pass

class ParameterRangeError(CurrentShareError):
    """参数范围异常"""
    def __init__(self, param_name: str, min_val: int, max_val: int):
        super().__init__(
            f"参数 {param_name} 超出范围 [0x{min_val:X}-0x{max_val:X}]"
        )

class CurrentShareConfig:
    """配置管理系统"""
    
    def __init__(self):
        self.mode = 'n'                # 运行模式 (n/t)
        self.enable_n_continuous = False
        self.th_pos = 0x7FFFF          # 正阈值
        self.th_neg = 0x80000          # 负阈值
        self.th_num_pos = 0
        self.th_num_neg = 0
        self.adj_k1 = 0x28             # 调整系数

    def configure(self):
        """交互式配置"""
        print("\n=== 系统配置 ===")
        self.mode = self._get_choice("运行模式", ['n', 't'])
        self.enable_n_continuous = self._get_bool("启用连续检测 (y/n): ")
        
        if self.enable_n_continuous:
            self._configure_thresholds()
            self.th_num_pos = self._get_hex("正触发次数", 0x1F)
            self.th_num_neg = self._get_hex("负触发次数", 0x1F)

        if self.mode == 'n':
            self.adj_k1 = self._get_hex("调整系数K1", 0xFFF)

    def _configure_thresholds(self):
        """阈值配置"""
        self.th_pos = self._get_full_range("正阈值")
        self.th_neg = self._get_full_range("负阈值")

    def _get_choice(self, prompt: str, options: list) -> str:
        """选项输入"""
        while True:
            choice = input(f"{prompt} ({'/'.join(options)}): ").lower()
            if choice in options:
                return choice
            print(f"无效选项，请从 {options} 中选择")

    def _get_bool(self, prompt: str) -> bool:
        """布尔输入"""
        while True:
            choice = input(prompt).lower()
            if choice in ('y', 'yes'):
                return True
            if choice in ('n', 'no'):
                return False
            print("请输入 y/n")

    def _get_hex(self, prompt: str, max_val: int) -> int:
        """十六进制输入"""
        while True:
            raw = input(f"{prompt} (0x00-0x{max_val:X}): ").strip().upper()
            try:
                value = int(raw, 16) if raw else 0
                if 0 <= value <= max_val:
                    return value
                print(f"超出范围 0x{max_val:X}")
            except ValueError:
                print("无效的十六进制数")

    def _get_full_range(self, prompt: str) -> int:
        """全范围输入"""
        while True:
            raw = input(f"{prompt} (0x00000-0xFFFFF): ").strip().upper()
            try:
                if raw.startswith("0X"):
                    value = int(raw, 16)
                else:
                    value = int(raw)
                
                if 0x00000 <= value <= 0xFFFFF:
                    return value
                print("超出有效范围")
            except ValueError:
                print("请输入十进制或十六进制数值")

class CurrentShareProcessor:
    """处理核心"""
    
    def __init__(self, config: CurrentShareConfig):
        self.config = config
        self._validate_config()
        self.reset()

    def reset(self):
        """状态重置"""
        self.cnt_pos = 0
        self.cnt_neg = 0

    def _validate_config(self):
        """配置验证"""
        if not 0x00000 <= self.config.th_pos <= 0xFFFFF:
            raise ParameterRangeError("th_pos", 0x00000, 0xFFFFF)
        if not 0x00000 <= self.config.th_neg <= 0xFFFFF:
            raise ParameterRangeError("th_neg", 0x00000, 0xFFFFF)

    def process(self, data: int, share: int) -> Tuple[float, bool]:
        """核心处理"""
        data = self._validate_input(data, 'Data')
        share = self._validate_input(share, 'Share')
        
        adj_data = (data * self.config.adj_k1) >> 6
        error = share - adj_data
        
        voltage = error / 1024.0
        return voltage, self._check_trigger(error) if self.config.enable_n_continuous else False

    def _validate_input(self, value: int, name: str) -> int:
        """输入验证"""
        if not 0x000 <= value <= 0xFFF:
            raise ParameterRangeError(name, 0x000, 0xFFF)
        return value

    def _check_trigger(self, error: int) -> bool:
        """触发检测"""
        if error >= self.config.th_pos:
            self.cnt_pos = min(self.cnt_pos + 1, 0x1F)
            if self.cnt_pos >= self.config.th_num_pos:
                self.reset()
                return True
        elif error <= self.config.th_neg:
            self.cnt_neg = min(self.cnt_neg + 1, 0x1F)
            if self.cnt_neg >= self.config.th_num_neg:
                self.reset()
                return True
        else:
            self.reset()
        return False

def main():
    """主程序"""
    print("=== 电流共享控制系统 ===")
    
    try:
        config = CurrentShareConfig()
        config.configure()
        processor = CurrentShareProcessor(config)
        
        while True:
            try:
                if config.mode == 'n':
                    data, share = get_valid_input()
                    output, irq = processor.process(data, share)
                else:
                    error = int(input("测试误差值: "), 0)
                    output = error / 1024.0
                    irq = False
                
                print(f"\n输出电压: {output:.4f}V | 中断: {'触发' if irq else '--'}")
                print("━" * 40)
                
            except (ValueError, CurrentShareError) as e:
                print(f"\n错误: {str(e)}")
            except KeyboardInterrupt:
                if input("\n退出系统？(y/n): ").lower() == 'y':
                    break
                
    except KeyboardInterrupt:
        print("\n配置已取消")

def get_valid_input() -> Tuple[int, int]:
    """输入验证（增强版）"""
    while True:
        raw = input("输入Data和Share（十六进制 空格分隔）: ").strip()
        if not raw:
            print("输入不能为空")
            continue
        
        # 处理特殊空格和不可见字符
        raw = re.sub(r'[\s\xa0\u3000]+', ' ', raw)  # 兼容全角/半角空格
        parts = raw.split(' ')
        
        if len(parts) != 2:
            print("需要两个数值，请用单个空格分隔")
            continue
            
        try:
            return (
                validate_hex(parts[0], "Data", 0xFFF),
                validate_hex(parts[1], "Share", 0xFFF)
            )
        except ValueError as e:
            print(f"输入错误: {str(e)}")

def validate_hex(value: str, name: str, max_val: int) -> int:
    """十六进制验证（最终版）"""
    # 过滤非ASCII字符
    value = str(value).encode('ascii', errors='ignore').decode().upper().strip()
    
    # 空值检查
    if not value:
        raise ValueError(f"{name} 不能为空")
    
    # 增强非法字符检测
    if re.search(r'[^0-9A-F]', value):
        invalid = set(re.findall(r'[^0-9A-F]', value))
        raise ValueError(f"{name} 包含非法字符: {', '.join(invalid)}")
    
    # 数值转换与验证
    try:
        num = int(value, 16)
    except ValueError:
        raise ValueError(f"{name} 不是有效的十六进制数")
    
    if num > max_val:
        raise ValueError(f"{name} 超出最大值 0x{max_val:X}")
    return num

if __name__ == "__main__":
    main()
