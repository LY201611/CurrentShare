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


def droop_algorithm(
    hex_data: str,  # u12.0（12位无符号整数）
    hex_k: str,     # u0.12（12位无符号小数，0整数位）
    hex_r1: str,    # u6.6（6位整数 + 6位小数）
    hex_r2: str,    # u6.6（6位整数 + 6位小数）
    hex_th: str     # u12.0（12位无符号整数）
) -> float:
    """
    变量标注规则：
    u[m].[n] = 无符号定点数（m位整数位，n位小数位）
    s[m].[n] = 有符号定点数（1位符号位，m位整数位，n位小数位）
    """
    # 输入转换
    data = hex_to_unsigned_fixed(hex_data, 12, 0)
    k = hex_to_unsigned_fixed(hex_k, 0, 12)
    r1 = hex_to_unsigned_fixed(hex_r1, 6, 6)
    r2 = hex_to_unsigned_fixed(hex_r2, 6, 6)
    th = hex_to_unsigned_fixed(hex_th, 12, 0)

    # 分段计算逻辑
    if data < th:
        return data * r1 * k
    else: 
        return (th * r1 + (data - th) * r2) * k


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


def process_droop(
    hex_data: str,
    params: dict,
    clp_enable: bool,
    clp_pos: float,
    clp_neg: float
) -> Tuple[str, str, str]:
    """返回三个处理阶段的HEX结果"""
    # 计算原始下垂结果（u18.12）
    droop_result = droop_algorithm(hex_data, params['hex_k'], params['hex_r1'],
                                   params['hex_r2'], params['hex_th'])
    hex_droop_result = float_to_unsigned_fixed_hex(droop_result, 18, 12)  # u18.12
    flot_droop_result = flot_to_unsigned_fixed(droop_result, 18, 12) # u18.12

    # 应用加权平均
    if params['enable_filter']:
        last_out = params['last_out']
        droop_out = (flot_droop_result / params['n']) + (last_out * (params['n'] - 1) / params['n'])
        hex_droop_out = float_to_unsigned_fixed_hex(droop_out, 18, 12)  # u18.12
        flot_droop_out = flot_to_unsigned_fixed(droop_out, 18, 12) # u18.12
        params['last_out'] = flot_droop_out  # 更新状态
    else:
        flot_droop_out = flot_droop_result
        hex_droop_out = hex_droop_result

    # 应用钳位
    if clp_enable:
        final_value = max(min(flot_droop_out, clp_pos), clp_neg)
        final_value = max(final_value, 0)  # 确保无符号下限
    else:
        final_value = flot_droop_out
    hex_droop_adj = float_to_unsigned_fixed_hex(final_value, 6, 4)  # u6.4

    return hex_droop_result, hex_droop_out, hex_droop_adj


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
    print("=== Droop算法计算器 ===")
    print("参数格式说明（全部无符号）：")
    print("  [data/th]: u12.0 → 0x000~0xFFF")
    print("  [k]: u0.12 → 0x000~0xFFF")
    print("  [r1/r2]: u6.6 → 0x000~0xFFF")
    print("  [clp]: u6.4 → 0x000~0xFFF")

    # 选择输入模式
    while True:
        mode = input("\n请选择模式：\n1. 单次输入\n2. 批量生成\n3. 重复测试\n选择(1/2/3): ").strip()
        if mode in ('1', '2', '3'):
            break
        print("无效选择，请重新输入")

    # 功能使能配置
    config = {
        'enable_filter': input("启用加权平均滤波？(Y/N): ").upper() == 'Y',
        'enable_clamp': input("启用输出钳位？(Y/N): ").upper() == 'Y',
        'last_out': 0.0  # 始终初始化
    }

    # 滤波器参数
    if config['enable_filter']:
        config['n'] = get_positive_int("滤波系数N: ")

    # 钳位参数
    clp_pos, clp_neg = 0.0, 0.0
    if config['enable_clamp']:
        clp_pos = hex_to_unsigned_fixed(get_hex_input("正钳位值(u6.4 HEX): ", 3), 6, 4)
        clp_neg = hex_to_unsigned_fixed(get_hex_input("负钳位值(u6.4 HEX): ", 3), 6, 4)
        print(f"钳位范围: [{clp_neg:.4f}, {clp_pos:.4f}]")

    # 基础参数输入
    base_params = {
        'hex_k': get_hex_input("比例系数K(u0.12): ", 3),
        'hex_r1': get_hex_input("阈值前R1(u6.6): ", 3),
        'hex_r2': get_hex_input("阈值后R2(u6.6): ", 3),
        'hex_th': get_hex_input("阈值TH(u12.0): ", 3)
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
                filename = f"droop_results_{timestamp}.csv"
                filename_droop_result = f"droop_result_{timestamp}.txt"
                filename_droop_out = f"droop_out_{timestamp}.txt"
                filename_droop_adj = f"droop_adj_{timestamp}.txt"
                full_path = os.path.join(script_dir, filename)
                full_path_droop_result = os.path.join(script_dir, filename_droop_result)
                full_path_droop_out = os.path.join(script_dir, filename_droop_out)
                full_path_droop_adj = os.path.join(script_dir, filename_droop_adj)

                with open(full_path, 'w', newline='', encoding='utf-8') as csv_file:
                    csv_writer = csv.writer(csv_file)
                    # 写入表头
                    csv_writer.writerow([
                        "输入数据(HEX)", 
                        "droop_result(HEX)", "droop_result(float)",
                        "droop_out(HEX)", "droop_out(float)",
                        "V_droop_adj(HEX)", "V_droop_adj(float)"
                    ])

                    for data in data_list:
                        current_params = {**config, **base_params}
                        hex_droop, hex_droop_out, hex_adj = process_droop(
                            data, current_params, config['enable_clamp'], clp_pos, clp_neg)
                        
                        if config['enable_filter']:
                            config['last_out'] = current_params['last_out']

                        # 十进制转换
                        flot_droop_result = hex_to_unsigned_fixed(hex_droop, 18, 12)
                        flot_droop_out = hex_to_unsigned_fixed(hex_droop_out, 18, 12)
                        flot_droop_adj = hex_to_unsigned_fixed(hex_adj, 6, 4)

                        dec_droop_result = int(hex_droop, 16)
                        dec_droop_out = int(hex_droop_out, 16)
                        dec_droop_adj = int(hex_adj, 16)

                        # 写入txt行
                        with open(full_path_droop_result, 'a', encoding='utf-8') as f:
                            f.write(f"{dec_droop_result}\n")
                        with open(full_path_droop_out, 'a', encoding='utf-8') as f:
                            f.write(f"{dec_droop_out}\n")
                        with open(full_path_droop_adj, 'a', encoding='utf-8') as f:
                            f.write(f"{dec_droop_adj}\n")

                        # 写入CSV行
                        csv_writer.writerow([
                            data,
                            hex_droop, f"{flot_droop_result:.10f}",
                            hex_droop_out, f"{flot_droop_out:.10f}",
                            hex_adj, f"{flot_droop_adj:.10f}"
                        ])

                        # 控制台输出
                        print("\n【处理结果】")
                        print(f"输入数据    : {data}")
                        print(f"droop_result (u18.12): {hex_droop} → {flot_droop_result:.10f}")
                        print(f"droop_out    (u18.12): {hex_droop_out} → {flot_droop_out:.10f}") 
                        print(f"V_droop_adj  (u6.4) : {hex_adj} → {flot_droop_adj:.10f}")
                        print("─" * 40)

                print(f"\n结果已保存至：{full_path}")

            except (ValueError, TypeError) as e:
                print(f"参数错误：{e}")
                continue
            break  # 批量处理完成后退出循环
        elif mode == '3':
            data = get_hex_input("\n测试数据(u12.0): ", 3)
            if data == 'Q':
                break
            n_times = get_positive_int("重复次数: ")
            data_list = [data] * n_times  # 生成重复数据列表
            
            print(f"\n即将执行 {n_times} 次重复测试...")
            
            # 创建CSV文件（复用批量模式的保存逻辑）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            script_dir = get_script_dir()
            filename = f"droop_repeat_{timestamp}.csv"
            filename_droop_result = f"droop_result_{timestamp}.txt"
            filename_droop_out = f"droop_out_{timestamp}.txt"
            filename_droop_adj = f"droop_adj_{timestamp}.txt"
            full_path = os.path.join(script_dir, filename)
            full_path_droop_result = os.path.join(script_dir, filename_droop_result)
            full_path_droop_out = os.path.join(script_dir, filename_droop_out)
            full_path_droop_adj = os.path.join(script_dir, filename_droop_adj)

            with open(full_path, 'w', newline='', encoding='utf-8') as csv_file:
                csv_writer = csv.writer(csv_file)
                # 扩展表头增加迭代次数列
                csv_writer.writerow([
                    "迭代次数", "输入数据(HEX)",
                    "droop_result(HEX)", "droop_result(float)",
                    "droop_out(HEX)", "droop_out(float)",
                    "V_droop_adj(HEX)", "V_droop_adj(float)"
                ])
                for iteration, data in enumerate(data_list, 1):
                    current_params = {**config, **base_params}
                    hex_droop, hex_droop_out, hex_adj = process_droop(
                        data, current_params, config['enable_clamp'], clp_pos, clp_neg)
                    
                    if config['enable_filter']:
                        config['last_out'] = current_params['last_out']
                    # 十进制转换
                    flot_droop_result = hex_to_unsigned_fixed(hex_droop, 18, 12)
                    flot_droop_out = hex_to_unsigned_fixed(hex_droop_out, 18, 12)
                    flot_droop_adj = hex_to_unsigned_fixed(hex_adj, 6, 4)

                    dec_droop_result = int(hex_droop, 16)
                    dec_droop_out = int(hex_droop_out, 16)
                    dec_droop_adj = int(hex_adj, 16)

                    # 写入txt行
                    with open(full_path_droop_result, 'a', encoding='utf-8') as f:
                        f.write(f"{dec_droop_result}\n")
                    with open(full_path_droop_out, 'a', encoding='utf-8') as f:
                        f.write(f"{dec_droop_out}\n")
                    with open(full_path_droop_adj, 'a', encoding='utf-8') as f:
                        f.write(f"{dec_droop_adj}\n")

                    # 写入CSV行
                    csv_writer.writerow([
                        iteration, data,
                        hex_droop, f"{flot_droop_result:.10f}",
                        hex_droop_out, f"{flot_droop_out:.10f}",
                        hex_adj, f"{flot_droop_adj:.10f}"
                    ])
                    # 控制台输出带迭代信息
                    print(f"\n【第 {iteration} 次迭代】")
                    print(f"输入数据    : {data}")
                    print(f"droop_result (u18.12): {hex_droop} → {flot_droop_result:.10f}")
                    print(f"droop_out    (u18.12): {hex_droop_out} → {flot_droop_out:.10f}") 
                    print(f"V_droop_adj  (u6.4) : {hex_adj} → {flot_droop_adj:.10f}")
                    print("─" * 40)
            print(f"\n重复测试结果已保存至：{full_path}")

        # 单次模式处理
        if mode == '1':
            current_params = {**config, **base_params}
            hex_droop, hex_droop_out, hex_adj = process_droop(
                data, current_params, config['enable_clamp'], clp_pos, clp_neg)
            
            if config['enable_filter']:
                config['last_out'] = current_params['last_out']

            # 十进制转换
            dec_droop = int(hex_droop, 16) / 4096
            dec_out = int(hex_droop_out, 16) / 4096
            dec_adj = hex_to_unsigned_fixed(hex_adj, 6, 4)

            # 结果展示
            print("\n【处理结果】")
            print(f"输入数据    : {data}")
            print(f"droop_result (u18.12): {hex_droop} → {dec_droop:.10f}")
            print(f"droop_out    (u18.12): {hex_droop_out} → {dec_out:.10f}") 
            print(f"V_droop_adj  (u6.4) : {hex_adj} → {dec_adj:.10f}")
            print("─" * 40)


if __name__ == "__main__":
    main()
