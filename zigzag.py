import pandas as pd

def calculate_zigzag(df, threshold=5.0, depth=10):
    """
    計算 ZigZag 轉折點與波段統計
    df: K棒資料 (需有 '最高', '最低', '收盤', '時間')
    threshold: Deviation (%)
    depth: Pivot 前後比較長度
    """
    highs = df["最高"].values
    lows = df["最低"].values
    closes = df["收盤"].values

    zigzag_idx = []
    direction = 0
    last_pivot_price = closes[depth]
    zigzag_idx.append(depth)

    for i in range(depth, len(closes) - depth):
        window_highs = highs[i - depth:i + depth + 1]
        window_lows = lows[i - depth:i + depth + 1]
        is_pivot_high = highs[i] == max(window_highs)
        is_pivot_low = lows[i] == min(window_lows)

        if direction == 0:
            if is_pivot_high:
                direction = -1
                last_pivot_price = highs[i]
                zigzag_idx.append(i)
            elif is_pivot_low:
                direction = 1
                last_pivot_price = lows[i]
                zigzag_idx.append(i)
        elif direction == 1:
            if is_pivot_high:
                change = (highs[i] - last_pivot_price) / last_pivot_price * 100
                if change >= threshold:
                    last_pivot_price = highs[i]
                    zigzag_idx.append(i)
                    direction = -1
            elif is_pivot_low and lows[i] < last_pivot_price:
                last_pivot_price = lows[i]
                zigzag_idx[-1] = i
        elif direction == -1:
            if is_pivot_low:
                change = (last_pivot_price - lows[i]) / last_pivot_price * 100
                if change >= threshold:
                    last_pivot_price = lows[i]
                    zigzag_idx.append(i)
                    direction = 1
            elif is_pivot_high and highs[i] > last_pivot_price:
                last_pivot_price = highs[i]
                zigzag_idx[-1] = i

    # 標籤處理
    swing_points = df.iloc[zigzag_idx].copy()
    swing_prices = []
    labels = []
    for i in range(len(zigzag_idx)):
        idx = zigzag_idx[i]
        if i == 0:
            swing_prices.append(closes[idx])
            labels.append("⬆ 初始")
        else:
            prev_idx = zigzag_idx[i - 1]
            if df["收盤"].iloc[idx] > df["收盤"].iloc[prev_idx]:
                swing_prices.append(df["最高"].iloc[idx])
                labels.append("⬆ 高點")
            else:
                swing_prices.append(df["最低"].iloc[idx])
                labels.append("⬇ 低點")
    swing_points["pivot_price"] = swing_prices

    # 標籤加序號
    segment_no = []
    up_no = 1
    down_no = 1
    new_labels = []
    for i, label in enumerate(labels):
        if i == 0:
            segment_no.append(None)
            new_labels.append(label)
        else:
            prev_price = swing_points["pivot_price"].iloc[i - 1]
            curr_price = swing_points["pivot_price"].iloc[i]
            price_diff = curr_price - prev_price
            sign = "+" if price_diff >= 0 else "-"
            diff_str = f"{sign}{abs(price_diff):.2f}"
            if curr_price > prev_price:
                segment_no.append(up_no)
                new_labels.append(f"{label} {up_no} ({diff_str})")
                up_no += 1
            else:
                segment_no.append(down_no)
                new_labels.append(f"{label} {down_no} ({diff_str})")
                down_no += 1
    swing_points["label"] = new_labels
    swing_points["segment_no"] = segment_no

    # 顏色與位置
    swing_points["text_color"] = ["red" if "高點" in l else "limegreen" if "低點" in l else "dodgerblue" for l in swing_points["label"]]
    swing_points["text_position"] = ["bottom center" if "低點" in l else "top center" for l in swing_points["label"]]

    # 波段統計資料
    segment_info = []
    for i in range(1, len(swing_points)):
        prev = swing_points.iloc[i - 1]
        curr = swing_points.iloc[i]
        price_diff = curr["pivot_price"] - prev["pivot_price"]
        pct_change = price_diff / prev["pivot_price"] * 100
        direction_str = "📈 上漲" if price_diff > 0 else "📉 下跌"
        seg_no = curr["segment_no"]
        if seg_no is not None:
            seg_no = int(seg_no)
        segment_info.append((direction_str, round(price_diff, 2), round(pct_change, 2), seg_no, prev["時間"], curr["時間"]))

    if segment_info:
        increases = [x for x in segment_info if x[0] == "📈 上漲"]
        decreases = [x for x in segment_info if x[0] == "📉 下跌"]

        def get_max_min(data):
            if not data:
                return "無", "無"
            max_seg = max(data, key=lambda x: x[2])
            min_seg = min(data, key=lambda x: x[2])
            max_str = f"#{max_seg[3]}｜價差: {max_seg[1]}｜漲跌幅: {max_seg[2]}%"
            min_str = f"#{min_seg[3]}｜價差: {min_seg[1]}｜漲跌幅: {min_seg[2]}%"
            return max_str, min_str

        inc_max, inc_min = get_max_min(increases)
        dec_max, dec_min = get_max_min(decreases)

    return swing_points, segment_info, inc_max, inc_min, dec_min, dec_max
