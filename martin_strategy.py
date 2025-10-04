import pandas as pd

def martin_backtest(prices_close, prices_high, prices_low, times, direction,
                    initial_balance, leverage, add_pct, add_multiple,
                    max_add_times, add_amount, add_amount_multiple,
                    take_profit_pct, stop_loss_pct):
    trades = []
    balance = initial_balance

    stats = {
        "total_open_trades": 0,
        "take_profit_count": 0,
        "stop_loss_count": 0,
        "total_take_profit_amount": 0.0,
        "total_stop_loss_amount": 0.0
    }

    i = 0
    while i < len(prices_close):
        entry_price = prices_close[i]
        used_margin = 0
        position_size = 0
        avg_price = 0
        add_count = 0
        last_add_price = entry_price

        add_amount_now = add_amount/2
        qty = (add_amount_now * leverage) / entry_price
        used_margin += add_amount_now
        position_size += qty
        avg_price = entry_price
        balance -= add_amount_now
        stats["total_open_trades"] += 1
        trades.append([times[i], "開倉", entry_price, position_size, balance, None, None, None])
        i += 1

        while i < len(prices_close):
            high = prices_high[i]
            low = prices_low[i]

            # 加碼條件
            price_change_from_last_add = lambda price: (price - last_add_price) / last_add_price * 100 * direction * -1

            if price_change_from_last_add(low if direction == 1 else high) >= add_pct * (add_multiple ** add_count) and add_count < max_add_times:
                trigger_price = low if direction == 1 else high
                add_amount_now = add_amount * (add_amount_multiple ** add_count)
                qty = (add_amount_now * leverage) / trigger_price
                avg_price = (avg_price * position_size + trigger_price * qty) / (position_size + qty)
                position_size += qty
                used_margin += add_amount_now
                balance -= add_amount_now
                add_count += 1
                last_add_price = trigger_price
                trades.append([times[i], "加碼", trigger_price, position_size, balance, None, None, None])

            # 止盈 / 停損
            pnl_pct_high = (high - avg_price) / avg_price * 100 * direction
            pnl_pct_low = (low - avg_price) / avg_price * 100 * direction

            if pnl_pct_high >= take_profit_pct or pnl_pct_low <= -stop_loss_pct:
                if pnl_pct_high >= take_profit_pct:
                    exit_price = avg_price * (1 + take_profit_pct / 100 * direction)
                    exit_reason = "止盈"
                else:
                    exit_price = avg_price * (1 - stop_loss_pct / 100 * direction)
                    exit_reason = "停損"

                pnl = position_size * (exit_price - avg_price) * direction
                balance += used_margin + round(pnl, 2)

                if pnl > 0:
                    stats["take_profit_count"] += 1
                    stats["total_take_profit_amount"] += pnl
                else:
                    stats["stop_loss_count"] += 1
                    stats["total_stop_loss_amount"] += pnl

                trades.append([
                    times[i], "平倉", round(exit_price, 2), 0, balance,
                    round(pnl, 2), round((exit_price - avg_price) / avg_price * 100 * direction, 2), exit_reason
                ])
                i += 1
                break

            i += 1

    df_trades = pd.DataFrame(trades, columns=["時間", "動作", "價格", "持倉數量", "餘額", "獲利 (USDT)", "獲利 (%)", "結束原因"]).set_index("時間")
    df_stats = pd.DataFrame({
        "指標": ["總開倉次數", "止盈次數", "停損次數", "止盈累計金額", "停損累計金額"],
        "數值": [
            stats["total_open_trades"],
            stats["take_profit_count"],
            stats["stop_loss_count"],
            round(stats["total_take_profit_amount"], 2),
            round(stats["total_stop_loss_amount"], 2),
        ]
    }).set_index("指標")

    return df_trades, df_stats
