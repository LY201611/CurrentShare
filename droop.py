"""
=== Silergy Droop Algorithm Calculator ===
版本：Rev0.2
更新日期：2024-03-15
更新内容：
1. 增加批量数据生成功能
2. 添加CSV结果输出
3. 优化滤波器状态保持
4. 修复路径处理问题
"""


import os
import csv
from datetime import datetime
from typing import Union, Tuple, Generator


def hex_to_unsigned_fixed(hex_str: str, int_bits: int, frac_bits: int) -> float:
    """无符号HEX转定点数（直接截断）"""
    total_bits = int_bits + frac_bits
    max_val = (1 << total_bits) - 1
    num = int(hex_str, 16) & max_val
    return num / (1 << frac_bits)


def float_to_unsigned_fixed_hex(value: float, int_bits: int, frac_bits: int) -> str:
    """无符号浮点数转HEX（直接截断）"""
    total_bits = int_bits + frac_bits
    max_value = (1 << total_bits) - 1

    # 无符号饱和处理
    saturated = max(min(value, max_value), 0)
    scaled = int(saturated * (1 << frac_bits))  # 直接取整

    hex_length = (total_bits + 3) // 4
    return f"{scaled:0{hex_length}X}"


def droop_algorithm(
    hex_data: str,
    hex_k: str,
    hex_r1: str,
    hex_r2: str,
    hex_th: str
) -> float:
    """
    返回浮点数结果的分段算法
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
    """安全获取HEX输入"""
    while True:
        try:
            value = input(prompt).strip().upper()
            if value in ('Q', 'EXIT'):
                return value

            if len(value) != length:
                raise ValueError

            int(value, 16)  # 验证有效性
            return value

        except ValueError:
            print(f"需要{length}位HEX，请重新输入")


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
    hex_droop = float_to_unsigned_fixed_hex(droop_result, 18, 12)  # u18.12

    # 应用加权平均
    if params['enable_filter']:
        last_out = params['last_out']
        droop_out = (droop_result / params['n']) + (last_out * (params['n'] - 1) / params['n'])
        params['last_out'] = droop_out  # 更新状态
    else:
        droop_out = droop_result
    hex_droop_out = float_to_unsigned_fixed_hex(droop_out, 18, 12)  # u18.12

    # 应用钳位
    final_value = droop_out
    if clp_enable:
        final_value = max(min(droop_out, clp_pos), clp_neg)
        final_value = max(final_value, 0)  # 确保无符号下限
    hex_adj = float_to_unsigned_fixed_hex(final_value, 6, 4)  # u6.4

    return hex_droop, hex_droop_out, hex_adj


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
    while True:
        try:
            start = input("起始值(3位HEX): ").strip().upper()
            end = input("结束值(3位HEX): ").strip().upper()
            step = int(input("步长(十进制整数): "))

            # 验证HEX格式
            if len(start) != 3 or len(end) != 3:
                raise ValueError
            int(start, 16)
            int(end, 16)

            return start, end, step
        except (ValueError, TypeError):
            print("输入格式错误，请重新输入")


def get_script_dir() -> str:
    """获取脚本所在目录的绝对路径"""
    return os.path.dirname(os.path.abspath(__file__))


def main():
    print("=== 全功能下垂算法计算器（增强版） ===")
    print("参数格式说明（全部无符号）：")
    print("  [data/th]: u12.0 → 0x000~0xFFF")
    print("  [k]: u0.12 → 0x000~0xFFF")
    print("  [r1/r2]: u6.6 → 0x000~0xFFF")
    print("  [clp]: u6.4 → 0x000~0xFFF")

    # 选择输入模式
    while True:
        mode = input("\n请选择模式：\n1. 单次输入\n2. 批量生成\n选择(1/2): ").strip()
        if mode in ('1', '2'):
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
        else:
            try:
                start, end, step = get_batch_input()
                data_list = list(generate_batch_hex(start, end, step))
                print(f"\n即将处理 {len(data_list)} 个数据点...")

                # 创建CSV文件
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                script_dir = get_script_dir()
                filename = f"droop_results_{timestamp}.csv"
                full_path = os.path.join(script_dir, filename)

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
                        dec_droop = int(hex_droop, 16) / 4096
                        dec_out = int(hex_droop_out, 16) / 4096
                        dec_adj = hex_to_unsigned_fixed(hex_adj, 6, 4)

                        # 写入CSV行
                        csv_writer.writerow([
                            data,
                            hex_droop, f"{dec_droop:.10f}",
                            hex_droop_out, f"{dec_out:.10f}",
                            hex_adj, f"{dec_adj:.10f}"
                        ])

                        # 控制台输出
                        print("\n【处理结果】")
                        print(f"输入数据    : {data}")
                        print(f"droop_result (u18.12): {hex_droop} → {dec_droop:.10f}")
                        print(f"droop_out    (u18.12): {hex_droop_out} → {dec_out:.10f}") 
                        print(f"V_droop_adj  (u6.4) : {hex_adj} → {dec_adj:.10f}")
                        print("─" * 40)

                print(f"\n结果已保存至：{full_path}")

            except (ValueError, TypeError) as e:
                print(f"参数错误：{e}")
                continue
            break  # 批量处理完成后退出循环

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
