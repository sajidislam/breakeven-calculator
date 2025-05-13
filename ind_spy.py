import pandas as pd
import yfinance as yf
from datetime import datetime
import re

def get_valid_date(hist, target_date, prefer='after'):
    dates = hist.index
    if prefer == 'after':
        for date in dates:
            if date >= target_date:
                return date
    else:
        for date in reversed(dates):
            if date <= target_date:
                return date
    return None

def clean_investment_amount(amount_str):
    amount_str = re.sub(r'[^\d.]', '', amount_str)
    return float(amount_str)

def calculate_growth(symbol, start_date, end_date, investment_amount):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=(end_date + pd.Timedelta(days=5)).strftime("%Y-%m-%d")
        )
        
        if hist.empty or 'Close' not in hist.columns:
            return None

        hist.index = hist.index.tz_localize(None)

        actual_start = get_valid_date(hist, start_date, prefer='after')
        actual_end = get_valid_date(hist, end_date, prefer='before')

        if not actual_start or not actual_end:
            return None

        start_price = hist.loc[actual_start, 'Close']
        end_price = hist.loc[actual_end, 'Close']
        nominal_growth = (end_price - start_price) / start_price * 100

        units = investment_amount / start_price
        dividends = hist.loc[actual_start:actual_end, 'Dividends']

        for date, dividend in dividends.items():
            if dividend > 0:
                reinvest_price = hist.loc[date, 'Close']
                units += (units * dividend) / reinvest_price

        final_value = units * end_price
        dividend_growth = (final_value - investment_amount) / investment_amount * 100

        return {
            "Symbol": symbol,
            "Start Date": actual_start.date(),
            "End Date": actual_end.date(),
            "Duration (Days)": (actual_end - actual_start).days,
            "Start Price": f"${start_price:,.2f}",
            "End Price": f"${end_price:,.2f}",
            "Final Value": f"${final_value:,.2f}",
            "Nominal % Growth": f"{nominal_growth:.2f}%",
            "Dividend Reinvested % Growth": f"{dividend_growth:.2f}%"
        }
    except Exception:
        return None

def get_sp500_tickers(verbose=True, save_to_csv=True):
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tables = pd.read_html(url, match="Symbol")
    df = tables[0]

    if save_to_csv:
        df.to_csv("sp500_list.csv", index=False)
        print("✅ Saved S&P 500 list to sp500_list.csv")

    if verbose:
        print("\n📘 S&P 500 Constituents:")
        for _, row in df.iterrows():
            print(f"{row['Symbol']: <8} - {row['Security']}")

    return df[['Symbol', 'Security', 'GICS Sector']]

def analyze_sp500(start_date, end_date, investment_amount):
    df_info = get_sp500_tickers()
    df_info['Yahoo Symbol'] = df_info['Symbol'].str.replace('.', '-', regex=False)

    results = []
    failed = []

    total = len(df_info)
    for idx, row in df_info.iterrows():
        symbol = row['Yahoo Symbol']
        print(f"[{idx + 1}/{total}] Fetching {symbol}...", end='\r')

        result = calculate_growth(symbol, start_date, end_date, investment_amount)
        if result:
            result["Security"] = row['Security']
            result["Sector"] = row['GICS Sector']
            results.append(result)
        else:
            failed.append({
                "Symbol": symbol,
                "Company": row['Security'],
                "Sector": row['GICS Sector'],
                "Reason": "No data or price fetch failed"
            })

    if failed:
        pd.DataFrame(failed).to_csv("sp500_failed_fetches.csv", index=False)
        print(f"\n⚠️ Failed to fetch data for {len(failed)} symbols. Saved to sp500_failed_fetches.csv")

    print(f"\n✅ Successfully fetched data for {len(results)} / {len(df_info)} symbols.")
    return pd.DataFrame(results)

# === Run the analysis ===
start_date = datetime.strptime("2024-02-29", "%Y-%m-%d")
end_date = datetime.strptime("2025-05-07", "%Y-%m-%d")
investment_amount = 1000.00

df = analyze_sp500(start_date, end_date, investment_amount)

# Sort by best dividend reinvested growth
df['Dividend Reinvested % Growth (Num)'] = df['Dividend Reinvested % Growth'].str.rstrip('%').astype(float)
df = df.sort_values(by='Dividend Reinvested % Growth (Num)', ascending=False)
df.drop(columns=['Dividend Reinvested % Growth (Num)'], inplace=True)

# Print top 10 and bottom 10
print("\n🏆 Top 10 Performers:")
print(df.head(10).to_string(index=False))

print("\n📉 Bottom 10 Performers:")
print(df.tail(10).to_string(index=False))


# Save results with timestamp
timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
file_name = f"sp500_growth_comparison_{timestamp}.csv"
df.to_csv(file_name, index=False)

# Print all rows
#with pd.option_context('display.max_rows', None, 'display.max_columns', None):
#    print(f"\n📈 Saved results to: {file_name}")
#    print(df)

