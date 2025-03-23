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


def float_to_unsigned_fixed_hex_round(value: float, int_bits: int, frac_bits: int) -> str:
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
    scaled = round(value * (1 << frac_bits))  # Scale the value by the fractional bits
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
    scaled = int(value * (1 << frac_bits))  # Scale the value by the fractional bits
    # Unsigned saturation to ensure the value fits within the bit limits
    saturated = max(min(scaled, max_value), 0)
    return saturated / (1 << frac_bits)  # Convert back to float


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

def analog_current_share_algorithm(
    hex_data: str,  # u12.0（12位无符号整数）
    hex_trim: str,  # u1.12（1位整数 + 12位小数）
    int_adc: int,   # int（8-12）
    int_prd_pwm: int,  # int（0-3）
) -> Tuple[str, str, int, int]:
    """
    变量标注规则：
    u[m].[n] = 无符号定点数（m位整数位，n位小数位）
    s[m].[n] = 有符号定点数（1位符号位，m位整数位，n位小数位）
    """
    # 输入转换
    data = hex_to_unsigned_fixed(hex_data, 12, 0)
    trim = hex_to_unsigned_fixed(hex_trim, 1, 12)
    adc_bits = int_adc
    prd_pwm = (int_prd_pwm + 1) * 100  # 100, 200, 300, 400

    duty_pwm = data * trim / (1 << adc_bits) * (hex_to_unsigned_fixed('CCD', 0, 12))  # 计算占空比, 0.8近似为0xCCD

    hex_duty_pwm = float_to_unsigned_fixed_hex_round(duty_pwm, 13, 12)  # 转换为u13.12格式
    float_duty_pwm = hex_to_unsigned_fixed(hex_duty_pwm, 13, 12)  # 转换为浮点数
    hex_duty_pwm_clamped = float_to_unsigned_fixed_hex_round(float_duty_pwm, 0, 12)  # 转换为u0.12格式
    float_duty_pwm_clamped = hex_to_unsigned_fixed(hex_duty_pwm_clamped, 0, 12)  # 转换为u0.12格式
    # float_duty_pwm = hex_to_unsigned_fixed(hex_duty_pwm_clamped, 0, 12)  # 转换为浮点数
    pwm_high = int(float_duty_pwm_clamped * prd_pwm + 0.5)  # PWM高电平时间,四舍五入
    pwm_low = prd_pwm - pwm_high  # PWM低电平时间

    return hex_duty_pwm, hex_duty_pwm_clamped, pwm_high, pwm_low


def generate_batch_hex(start_hex: str, end_hex: str, step: int) -> Generator[str, None, None]:
    """生成HEX序列的生成器"""
    start = int(start_hex, 16)
    end = int(end_hex, 16)

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
    start = get_hex_input("起始值(3位HEX): ", 3)
    end = get_hex_input("结束值(3位HEX): ", 3)
    step = get_positive_int("步长(十进制整数): ")
    return start, end, step


def get_script_dir() -> str:
    """获取脚本所在目录的绝对路径"""
    return os.path.dirname(os.path.abspath(__file__))


def main():
    print("=== analog current share ===")
    print("参数格式说明（全部无符号）：")
    print("  [data]: u12.0 → 0x000~0xFFF       (12位整数，满量程4095)")
    print("  [trim]: u1.12 → 0x000~0xFFF       (1位整数+12位小数，范围0~1.999755859375)")
    print("  [bit_dac]: int → 0x0~0xF          (4位DAC配置值，对应实际DAC位数)")

    # 选择输入模式
    while True:
        mode = input("\n请选择模式：\n1. 单次输入\n2. 批量生成\n选择(1/2): ").strip()
        if mode in ('1', '2'):
            break
        print("无效选择，请重新输入")

    # 基础参数输入
    base_params = {
        'trim': get_hex_input("trim系数(u1.12): ", 4),
        'bit_adc': get_non_negative_int("bit_adc: "),
        'prd_pwm': get_non_negative_int("prd_pwm(0:100clk; 1:200clk; 2:300clk; 3:400clk): ")
    }

     # 数据处理逻辑
    while True:
        if mode == '1':
            data = get_hex_input("\n输入数据(u12.0): ", 3)
            if data == 'Q':
                break
            data_list = [data]
        elif mode == '2':
            try:
                start, end, step = get_batch_input()
                data_list = list(generate_batch_hex(start, end, step))
                print(f"\n即将处理 {len(data_list)} 个数据点...")

                # 创建CSV文件
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                script_dir = get_script_dir()
                filename = f"analog_current_share_results_{timestamp}.csv"
                filename_duty_pwm = f"duty_pwm_{timestamp}.txt"
                filename_duty_pwm_clamped = f"duty_pwm_clamped_{timestamp}.txt"
                filename_pwm_high = f"pwm_high_{timestamp}.txt"
                filename_pwm_low = f"pwm_low_{timestamp}.txt"
                full_path = os.path.join(script_dir, filename)
                full_path_duty_pwm = os.path.join(script_dir, filename_duty_pwm)
                full_path_duty_pwm_clamped = os.path.join(script_dir, filename_duty_pwm_clamped)
                full_path_pwm_high = os.path.join(script_dir, filename_pwm_high)
                full_path_pwm_low = os.path.join(script_dir, filename_pwm_low)

                with open(full_path, 'w', newline='', encoding='utf-8') as csv_file:
                    csv_writer = csv.writer(csv_file)
                    # 写入表头
                    csv_writer.writerow([
                        "输入数据(HEX)", 
                        "duty_pwm(HEX)", "duty_pwm(float)",
                        "duty_pwm_clamped(HEX)", "duty_pwm_clamped(float)",
                        "pwm_high(int)",
                        "pwm_low(int)"
                    ])

                    for data in data_list:
                        hex_duty_pwm, hex_duty_pwm_clamped, pwm_high, pwm_low = analog_current_share_algorithm(
                            data, base_params["trim"], base_params["bit_adc"], base_params["prd_pwm"])

                        # 十进制转换
                        float_duty_pwm = hex_to_unsigned_fixed(hex_duty_pwm, 13, 12)
                        float_duty_pwm_clamped = hex_to_unsigned_fixed(hex_duty_pwm_clamped, 0, 12)

                        dec_duty_pwm = int(hex_duty_pwm, 16)
                        dec_duty_pwm_clamped = int(hex_duty_pwm_clamped, 16)

                        # 写入txt行
                        with open(full_path_duty_pwm, 'a', encoding='utf-8') as f:
                            f.write(f"{dec_duty_pwm}\n")
                        with open(full_path_duty_pwm_clamped, 'a', encoding='utf-8') as f:
                            f.write(f"{dec_duty_pwm_clamped}\n")
                        with open(full_path_pwm_high, 'a', encoding='utf-8') as f:
                            f.write(f"{pwm_high}\n")
                        with open(full_path_pwm_low, 'a', encoding='utf-8') as f:
                            f.write(f"{pwm_low}\n")

                        # 写入CSV行
                        csv_writer.writerow([
                            data,
                            hex_duty_pwm, f"{float_duty_pwm:.10f}",
                            hex_duty_pwm_clamped, f"{float_duty_pwm_clamped:.10f}",
                            f"{pwm_high}",
                            f"{pwm_low}"
                        ])

                        # 控制台输出
                        print("\n【处理结果】")
                        print(f"输入数据    : {data}")
                        print(f"duty_pwm (u13.12): {hex_duty_pwm} → {float_duty_pwm:.10f}")
                        print(f"duty_pwm_clamped    (u0.12): {hex_duty_pwm_clamped} → {float_duty_pwm_clamped:.10f}") 
                        print(f"pwm_high  (int) : {pwm_high}")
                        print(f"pwm_low  (int) : {pwm_low}")
                        print("─" * 40)

                print(f"\n结果已保存至：{full_path}")

            except (ValueError, TypeError) as e:
                print(f"参数错误：{e}")
                continue
            break  # 批量处理完成后退出循环

        # 单次模式处理
        if mode == '1':
            hex_duty_pwm, hex_duty_pwm_clamped, pwm_high, pwm_low = analog_current_share_algorithm(
                data, base_params["trim"], base_params["bit_adc"], base_params["prd_pwm"])

            # 十进制转换
            float_duty_pwm = hex_to_unsigned_fixed(hex_duty_pwm, 13, 12)
            float_duty_pwm_clamped = hex_to_unsigned_fixed(hex_duty_pwm_clamped, 0, 12)

            # 控制台输出
            print("\n【处理结果】")
            print(f"输入数据    : {data}")
            print(f"duty_pwm (u13.12): {hex_duty_pwm} → {float_duty_pwm:.10f}")
            print(f"duty_pwm_clamped    (u0.12): {hex_duty_pwm_clamped} → {float_duty_pwm_clamped:.10f}") 
            print(f"pwm_high  (int) : {pwm_high}")
            print(f"pwm_low  (int) : {pwm_low}")
            print("─" * 40)


if __name__ == "__main__":
    main()
