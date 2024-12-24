def calculate_sar(high, low, acceleration=0.02, maximum=0.2):
    """
    手動計算拋物線止損與反轉 (SAR)。
    high: 高價序列
    low: 低價序列
    acceleration: 加速因子
    maximum: 加速因子的最大值
    """
    n = len(high)
    sar = [0] * n  # 初始化 SAR
    trend = 1  # 1 表示多頭，-1 表示空頭
    ep = high[0] if trend == 1 else low[0]  # 極值點
    af = acceleration  # 初始加速因子

    # 初始化 SAR
    sar[0] = low[0] if trend == 1 else high[0]

    for i in range(1, n):
        prev_sar = sar[i - 1]
        sar[i] = prev_sar + af * (ep - prev_sar)

        # 多頭趨勢檢查
        if trend == 1:
            if high[i] > ep:
                ep = high[i]
                af = min(af + acceleration, maximum)
            if sar[i] > low[i]:
                trend = -1
                sar[i] = ep  # 反轉
                ep = low[i]
                af = acceleration
        # 空頭趨勢檢查
        else:
            if low[i] < ep:
                ep = low[i]
                af = min(af + acceleration, maximum)
            if sar[i] < high[i]:
                trend = 1
                sar[i] = ep  # 反轉
                ep = high[i]
                af = acceleration

    return sar
