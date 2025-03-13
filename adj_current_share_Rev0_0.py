from typing import Tuple, Optional

class CurrentShareAdjConfig:
    """电流共享调节配置系统（最终版）"""
    
    def __init__(self):
        self.mode = 'n'                # 运行模式 n=正常/t=测试
        self.enable_n_continuous = False
        self.th_pos = 0x7FFFF          # s19.0（+262143）
        self.th_neg = 0x80000          # s19.0（-262144）
        self.th_num_pos = 5            # u5.0（0-31）
        self.th_num_neg = 5            # u5.0
        self.adj_k1 = 0x28             # u6.6（仅正常模式）

    def configure(self):
        """交互式配置流程"""
        print("\n=== 系统配置 ===")
        
        # 模式选择
        while True:
            mode = input("选择模式 (n=正常/t=测试): ").lower()
            if mode in ['n', 't']:
                self.mode = mode
                break
            print("无效输入，请选择n/t")
        
        # 公共配置
        self.enable_n_continuous = self._get_bool("启用连续检测 (y/n): ")
        self.th_pos = self._get_s19("正阈值 (s19.0 DEC): ")
        self.th_neg = self._get_s19("负阈值 (s19.0 DEC): ")
        self.th_num_pos = self._get_hex("正触发次数 (u5.0 HEX): ", 2, 0x1F)
        self.th_num_neg = self._get_hex("负触发次数 (u5.0 HEX): ", 2, 0x1F)
        
        # 正常模式专属配置
        if self.mode == 'n':
            self.adj_k1 = self._get_hex("调整系数K1 (u6.6 HEX): ", 3, 0xFFF)

    def _get_hex(self, prompt: str, digits: int, max_val: int) -> int:
        """十六进制输入验证"""
        while True:
            raw = input(prompt).strip().upper()
            if not raw: return 0
            try:
                value = int(raw, 16)
                if 0 <= value <= max_val:
                    return value
                print(f"超出范围 (0-{hex(max_val)})")
            except ValueError:
                print("无效HEX输入")

    def _get_s19(self, prompt: str) -> int:
        """s19.0格式输入处理"""
        while True:
            try:
                value = int(input(prompt))
                if -262144 <= value <= 262143:
                    return value & 0x7FFFF  # 保留19位有效位
                print("超出范围 (-262144~262143)")
            except ValueError:
                print("请输入整数")

    def _get_bool(self, prompt: str) -> bool:
        """布尔值输入处理"""
        while True:
            choice = input(prompt).lower()
            if choice in ['y', 'yes']: return True
            if choice in ['n', 'no']: return False
            print("请输入 y/n")

class CurrentShareAdjCore:
    """电流共享处理核心（最终版）"""
    
    def __init__(self, config: CurrentShareAdjConfig):
        self.config = config
        self._convert_params()
        self.reset()
        
    def _convert_params(self):
        """参数格式转换"""
        if self.config.mode == 'n':
            self.adj_k1 = ((self.config.adj_k1 >> 6) & 0x3F) + (self.config.adj_k1 & 0x3F)/64.0
        
    def reset(self):
        """重置运行状态"""
        self.cnt_pos = 0     # 正触发计数器
        self.cnt_neg = 0     # 负触发计数器
        self.last_output = 0.0

    def process(self, data: int, share: int, test_error: Optional[float] = None) -> Tuple[float, bool]:
        """
        核心处理流程
        :param data: 原始数据（u12.0）
        :param share: 共享基准值（u12.0）
        :param test_error: 测试模式误差值（单位：伏特）
        :return: (输出电压, 中断标志)
        """
        # 输入预处理
        if test_error is not None:
            error = int(test_error * 1024)  # 伏特转s19.10
        else:
            data = data & 0xFFF
            share = share & 0xFFF
            adj_data = data * self.adj_k1
            error = share - adj_data

        # 连续检测逻辑
        interrupt = False
        if self.config.enable_n_continuous:
            if error >= self.config.th_pos:
                self.cnt_pos = min(self.cnt_pos + 1, 31)
                if self.cnt_pos >= self.config.th_num_pos:
                    interrupt = True
            elif error <= self.config.th_neg:
                self.cnt_neg = min(self.cnt_neg + 1, 31)
                if self.cnt_neg >= self.config.th_num_neg:
                    interrupt = True
            else:
                self.cnt_pos = 0
                self.cnt_neg = 0
        else:
            interrupt = error >= self.config.th_pos or error <= self.config.th_neg
        
        # 直接输出计算结果
        self.last_output = error / 1024.0  # s19.10 → 伏特
        return self.last_output, interrupt

def main():
    """主控制系统"""
    print("=== 电流共享调节系统 ===")
    
    # 系统配置
    config = CurrentShareAdjConfig()
    try:
        config.configure()
    except KeyboardInterrupt:
        print("\n配置已取消")
        return
    
    # 初始化处理核心
    core = CurrentShareAdjCore(config)
    
    # 运行循环
    while True:
        try:
            if config.mode == 'n':
                data, share = _get_two_hex_input()
                output, irq = core.process(data, share)
            else:
                error = float(input("\n输入误差值（伏特）: "))
                output, irq = core.process(0, 0, test_error=error)
            
            # 显示结果
            print(f"\n[输出电压] {output:.4f}V")
            print(f"[中断状态] {'触发' if irq else '未触发'}")
            print("━" * 40)
            
        except KeyboardInterrupt:
            print("\n返回主菜单")
            main()
        except Exception as e:
            print(f"\n错误: {str(e)}")

def _get_two_hex_input() -> Tuple[int, int]:
    """获取并验证两个HEX输入"""
    while True:
        raw = input("\n输入data和share（两个HEX数，空格分隔，示例：FFF 800）: ").strip()
        parts = raw.split()
        
        if len(parts) != 2:
            print("错误：需要输入两个数值，用空格分隔")
            continue
            
        try:
            data = int(parts, 16)
            share = int(parts, 16)
            if not (0 <= data <= 0xFFF) or not (0 <= share <= 0xFFF):
                print("数值范围需在000-FFF之间")
                continue
            return data, share
        except ValueError:
            print("无效的HEX格式，请使用类似'1A3 F0'的格式")

if __name__ == "__main__":
    main()
