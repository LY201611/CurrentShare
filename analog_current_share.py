from typing import Tuple, List, Generator
import math
import os

class CurrentShareConfig:
    """参数配置存储器（增加0.8系数定点数）"""

    def __init__(self):
        self.trim = 0x0000
        self.bit_adc = 8
        self.pwm_code = 0
        self.pwm_periods = [100, 200, 300, 400]
        self.scale_factor = 0x0CCD  # 0.8的12位定点数近似 (3277/4096≈0.7998)

    def configure(self):
        """参数配置流程保持不变"""
        print("\n=== 参数初始化 ===")
        self.trim = self._get_hex("trim(u1.12 4位HEX): ", 4, 0x1FFF)
        self.bit_adc = self._get_int("ADC位数(8-12): ", 8, 12)
        self.pwm_code = self._get_int("PWM周期码(0-3): ", 0, 3)

    def _get_hex(self, prompt: str, length: int, max_val: int) -> int:
        """获取并验证HEX输入"""
        while True:
            try:
                raw = input(prompt).strip().upper().lstrip('0')
                if not raw:
                    return 0  # 允许空输入
                value = int(raw, 16)
                if value > max_val or len(raw) > length:
                    raise ValueError
                return value
            except ValueError:
                print(f"需输入不超过{length}位且≤{hex(max_val)}的HEX")

    def _get_int(self, prompt: str, min_val: int, max_val: int) -> int:
        """获取并验证整数输入"""
        while True:
            try:
                value = int(input(prompt))
                if min_val <= value <= max_val:
                    return value
                raise ValueError
            except ValueError:
                print(f"需输入{min_val}-{max_val}的整数")


def calculate_duty(config: CurrentShareConfig, data: int) -> Tuple[str, float, int, int]:
    """更新0.8系数定点数计算逻辑"""
    data = data & 0xFFF

    # 核心计算步骤
    trim_scaled = config.trim / 4096.0  # u1.12转浮点
    divider = 1 << config.bit_adc

    # 使用定点数近似计算
    scale_factor = config.scale_factor / 4096.0  # 0.8的近似值
    duty_raw = (data * trim_scaled) / divider * scale_factor

    # 钳位处理
    duty_clamped = max(min(duty_raw, 1.0), 0.0)  # 保持0 - 1范围

    # 转换为u13.12格式（13bit整体，其中12bit小数）
    duty_pwm = int(duty_clamped * 4096) & 0x1FFF  # 确保13bit

    # PWM生成（精确四舍五入）
    period = config.pwm_periods[config.pwm_code]
    pwm_high = int(math.floor(duty_clamped * period + 0.5))

    return (
        f"{duty_pwm:04X}",  # 4位HEX显示
        duty_clamped,
        pwm_high,
        period - pwm_high
    )


def hex_range_generator(begin: int, end: int, step: int) -> Generator[int, None, None]:
    """生成HEX数据序列的迭代器"""
    current = begin
    while current <= end:
        yield current & 0xFFF  # 确保不超过12bit
        current += step


def get_hex_range(prompt: str) -> int:
    """专用HEX范围输入函数"""
    while True:
        try:
            raw = input(prompt).strip().upper().lstrip('0')
            value = int(raw, 16) if raw else 0
            if not (0 <= value <= 0xFFF):
                raise ValueError
            return value
        except ValueError:
            print("需输入3位有效HEX值 (0x000-0xFFF)")


def batch_process(config: CurrentShareConfig, data_iter: Generator[int, None, None], output_file: str):
    """增强型批处理函数"""
    results = []
    for data in data_iter:
        try:
            hex_duty, dec_duty, high, low = calculate_duty(config, data)
            results.append((
                f"0x{data:03X}",
                hex_duty,
                f"{dec_duty:.6f}",
                f"{dec_duty * 100:.2f}%",
                str(high),
                str(low)
            ))
        except Exception as e:
            print(f"数据 0x{data:03X} 处理失败: {str(e)}")

    # 报告生成
    report = [
        "Silergy Corp. 电流共享计算报告",
        "=" * 40,
        f"参数配置:",
        f"TRIM: 0x{config.trim:04X} ({config.trim / 4096:.4f})",
        f"ADC位数: {config.bit_adc} bits",
        f"PWM周期: {config.pwm_periods[config.pwm_code]} clks",
        "=" * 40,
        "DATA\tDuty(HEX)\tDuty(DEC)\tRatio\tHIGH\tLOW"
    ]
    report += ["\t".join(item) for item in results]

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
    print(f"\n报告已生成: {os.path.abspath(output_file)}")


def main():
    print("=== 电流共享计算器（序列生成模式） ===")
    print("操作模式说明:")
    print("1. 单次输入模式")
    print("2. 批处理模式（支持序列生成）\n")

    config = CurrentShareConfig()
    config.configure()

    # 模式选择
    mode = input("\n请选择模式 (1/2): ").strip()

    if mode == '1':
        while True:
            raw = input("\n输入data(3位HEX)> ").strip().upper()
            if raw in ('Q', 'EXIT'):
                print("程序已退出")
                break

            try:
                data = int(raw, 16) if raw else 0
                if data > 0xFFF:
                    raise ValueError
            except:
                print("输入错误：需3位有效HEX")
                continue

            try:
                hex_duty, dec_duty, high, low = calculate_duty(config, data)

                print(f"\n[ DATA: 0x{data:03X} ]")
                print(f"计算系数 : 0x{config.scale_factor:04X} ({config.scale_factor / 4096:.6f})")
                print(f"输出占空比: 0x{hex_duty} (u13.12)")
                print(f"十进制值 : {dec_duty:.6f} ({dec_duty * 100:.2f}%)")
                print(f"PWM周期  : HIGH={high} | LOW={low}")
                print("─" * 40)

            except Exception as e:
                print(f"计算错误: {str(e)}")
    elif mode == '2':
        print("\n选择批处理数据来源:")
        print("1. 手动输入列表")
        print("2. 自动生成序列")
        sub_mode = input("请选择子模式 (1/2): ").strip()

        if sub_mode == '1':
            raw = input("手动输入DATA列表（空格分隔HEX）: ").upper()
            data_list = [int(x, 16) for x in raw.split() if x]
            output_file = input("输出文件名（默认report.txt）: ").strip() or "report.txt"
            batch_process(config, (data for data in data_list), output_file)
        elif sub_mode == '2':
            print("\n=== 序列参数配置 ===")
            begin = get_hex_range("起始值 (3位HEX): ")
            end = get_hex_range("结束值 (3位HEX): ")
            step = get_hex_range("步长 (3位HEX): ")

            if begin > end:
                print("错误：起始值不能大于结束值")
                return
            if step == 0:
                print("错误：步长不能为0")
                return

            data_iter = hex_range_generator(begin, end, step)
            output_file = input("输出文件名（默认seq_report.txt）: ").strip() or "seq_report.txt"
            batch_process(config, data_iter, output_file)
        else:
            print("无效的子模式选择")
    else:
        print("无效的模式选择")


if __name__ == "__main__":
    main()
