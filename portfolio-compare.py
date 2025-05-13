import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def get_last_trading_day_before(target_date):
    """Get the last trading day before or on the given date."""
    while True:
        data = yf.download("SPY",
                           start=target_date.strftime('%Y-%m-%d'),
                           end=(target_date + timedelta(days=1)).strftime('%Y-%m-%d'),
                           progress=False,
                           auto_adjust=False)
        if not data.empty:
            return data.index[-1].strftime('%Y-%m-%d')
        target_date -= timedelta(days=1)

def get_price_on_or_before(symbol, target_date_str):
    """Get the adjusted close price on or before a given date."""
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    start_date = target_date - timedelta(days=30)
    data = yf.download(symbol,
                       start=start_date.strftime('%Y-%m-%d'),
                       end=(target_date + timedelta(days=1)).strftime('%Y-%m-%d'),
                       progress=False,
                       auto_adjust=False)
    if data.empty or 'Adj Close' not in data.columns:
        return None
    adj_close = data['Adj Close'].dropna()
    if adj_close.empty:
        return None
    return adj_close.iloc[-1].item()  # FIXED: extract scalar float value


def format_currency(amount):
    return f"${amount:,.2f}"

def format_percent(value):
    return f"{value:.2f}%"

def safe_format_currency(x):
    if pd.isna(x):
        return ''
    return format_currency(x)


def safe_format_percent(x):
    if pd.isna(x):
        return ''
    return format_percent(x)

def calculate_investment_performance(input_csv_path):
    # Ask user for end date
    user_input = input("Enter end date (YYYY-MM-DD), or press Enter to use the latest trading day: ").strip()
    if user_input:
        try:
            end_date = datetime.strptime(user_input, '%Y-%m-%d')
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD.")
            return
    else:
        end_date = datetime.today()
    end_date_str = get_last_trading_day_before(end_date)

    print(f"\n📅 Using end date: {end_date_str}")

    df_input = pd.read_csv(input_csv_path)
    df_input['Date Invested'] = pd.to_datetime(df_input['Date Invested'], format='%Y-%m-%d', errors='coerce')

    results = []
    total_invested = 0
    total_value = 0
    total_spy_value = 0

    for _, row in df_input.iterrows():
        symbol = row['Symbol']
        investment_date = row['Date Invested']
        if pd.isnull(investment_date):
            continue
        amount_invested = float(row['Amount Invested'])
        investment_date_str = investment_date.strftime('%Y-%m-%d')
        total_invested += amount_invested

        try:
            start_price = get_price_on_or_before(symbol, investment_date_str)
            if start_price is None:
                print(f"⚠️ No data found for {symbol} on or before {investment_date_str}")
                continue

            shares_bought = amount_invested / start_price

            end_price = get_price_on_or_before(symbol, end_date_str)
            if end_price is None:
                print(f"⚠️ No data found for {symbol} on or before {end_date_str}")
                continue

            current_value = shares_bought * end_price
            percent_growth = ((current_value - amount_invested) / amount_invested) * 100
            total_value += current_value

            results.append({
                'Symbol': symbol,
                'Investment Date': investment_date_str,
                'Start Price': round(start_price, 2),
                'Shares Bought': round(shares_bought, 4),
                'End Date': end_date_str,
                'End Price': round(end_price, 2),
                'Initial Investment': amount_invested,
                'Current Value': current_value,
                '% Growth': percent_growth
            })

            spy_start_price = get_price_on_or_before("SPY", investment_date_str)
            spy_end_price = get_price_on_or_before("SPY", end_date_str)
            if spy_start_price is not None and spy_end_price is not None:
                spy_shares = amount_invested / spy_start_price
                spy_value = spy_shares * spy_end_price
                total_spy_value += spy_value

        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    df_main = pd.DataFrame(results)

    # Add summary rows
    total_growth = ((total_value - total_invested) / total_invested) * 100 if total_invested else 0
    spy_growth = ((total_spy_value - total_invested) / total_invested) * 100 if total_invested else 0
    vs_spy = total_growth - spy_growth

    summary_rows = [
        {
            'Symbol': 'TOTAL',
            'Investment Date': '',
            'Start Price': '',
            'Shares Bought': '',
            'End Date': '',
            'End Price': '',
            'Initial Investment': total_invested,
            'Current Value': total_value,
            '% Growth': total_growth
        },
        {
            'Symbol': 'SPY Benchmark',
            'Investment Date': '',
            'Start Price': '',
            'Shares Bought': '',
            'End Date': '',
            'End Price': '',
            'Initial Investment': total_invested,
            'Current Value': total_spy_value,
            '% Growth': spy_growth
        },
        {
            'Symbol': 'Portfolio vs SPY',
            'Investment Date': '',
            'Start Price': '',
            'Shares Bought': '',
            'End Date': '',
            'End Price': '',
            'Initial Investment': None,
            'Current Value': None,
            '% Growth': vs_spy
        }
    ]

    df_summary = pd.DataFrame(summary_rows)
    df_combined = pd.concat([df_main, df_summary], ignore_index=True)

    # Apply safe formatting
    df_display = df_combined.copy()
    df_display['Initial Investment'] = df_display['Initial Investment'].apply(safe_format_currency)
    df_display['Current Value'] = df_display['Current Value'].apply(safe_format_currency)
    df_display['% Growth'] = df_display['% Growth'].apply(safe_format_percent)

    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_csv = f"portfolio_performance_{timestamp}.csv"
    df_display.to_csv(output_csv, index=False)

    print(f"\n✅ Results saved to: {output_csv}")
    print("\n📊 Portfolio Summary:\n")
    print(df_display.to_string(index=False))

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python compare.py <input_csv_path>")
    else:
        input_csv = sys.argv[1]
        calculate_investment_performance(input_csv)
