import pandas as pd
import yfinance as yf
from datetime import datetime, date

def get_year_end_price(symbol, year):
    """Get the adjusted close price of a symbol on the last trading day of a given year."""
    start_date = f"{year}-12-20"
    end_date = f"{year}-12-31"
    data = yf.download(symbol, start=start_date, end=end_date, progress=False, auto_adjust=False)
    if data.empty or 'Adj Close' not in data.columns:
        return None, None
    adj_close = data['Adj Close'].dropna()
    if adj_close.empty:
        return None, None
    last_date = adj_close.index[-1]
    return adj_close.iloc[-1].item(), last_date.strftime('%Y-%m-%d')

def calculate_investment_performance(input_csv_path, output_csv_path):
    df_input = pd.read_csv(input_csv_path)
    df_input['Date Invested'] = pd.to_datetime(df_input['Date Invested'], format='%Y-%m-%d', errors='coerce')

    results = []
    yearly_growth = []
    current_year = datetime.today().year

    for _, row in df_input.iterrows():
        symbol = row['Symbol']
        investment_date = row['Date Invested']
        if pd.isnull(investment_date):
            continue
        amount_invested = float(row['Amount Invested'])
        investment_year = investment_date.year

        try:
            historical_data = yf.download(symbol, start=investment_date.strftime('%Y-%m-%d'),
                                          progress=False, auto_adjust=False)
            start_price = historical_data['Adj Close'].dropna().iloc[0].item()
            shares_bought = amount_invested / start_price

            latest_data = yf.download(symbol, period='5d', progress=False, auto_adjust=False)
            latest_price_series = latest_data['Adj Close'].dropna()
            latest_price = latest_price_series.iloc[-1].item()
            valuation_date = latest_price_series.index[-1].strftime('%Y-%m-%d')

            current_value = shares_bought * latest_price
            percent_growth = ((current_value - amount_invested) / amount_invested) * 100

            results.append({
                'Symbol': symbol,
                'Investment Date': investment_date.strftime('%Y-%m-%d'),
                'Start Price': round(start_price, 2),
                'Shares Bought': round(shares_bought, 4),
                'Valuation Date': valuation_date,
                'Latest Price': round(latest_price, 2),
                'Initial Investment': round(amount_invested, 2),
                'Current Value': round(current_value, 2),
                '% Growth': round(percent_growth, 2)
            })

            # Only fetch year-end price if the year has finished.
            for year in range(investment_year, current_year + 1):
                if year < current_year or (year == current_year and date.today().month == 12 and date.today().day == 31):
                    year_end_price, price_date = get_year_end_price(symbol, year)
                    if year_end_price is None:
                        continue
                    value = shares_bought * year_end_price
                    growth = ((value - amount_invested) / amount_invested) * 100
                    yearly_growth.append({
                        'Year': year,
                        'Symbol': symbol,
                        'Valuation Date': price_date,
                        'Year-End Price': round(year_end_price, 2),
                        'Value at Year-End': round(value, 2),
                        '% Growth': round(growth, 2)
                    })

        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    df_main = pd.DataFrame(results)
    df_growth = pd.DataFrame(yearly_growth)

    # Save both to one CSV
    with open(output_csv_path, 'w') as f:
        df_main.to_csv(f, index=False)
        f.write("\nYearly Growth Breakdown\n")
        df_growth.to_csv(f, index=False)

    print(f"\n✅ Results saved to: {output_csv_path}")

    if not df_main.empty:
        print("\n📊 Portfolio Summary:")
        print(df_main.to_string(index=False))
        print("\n📈 Yearly Growth Breakdown:")
        print(df_growth.to_string(index=False))
    else:
        print("\n⚠️ No valid data was processed. Please check your input file and symbols.")

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python compare.py <input_csv_path>")
    else:
        input_csv = sys.argv[1]
        output_csv = 'portfolio_performance.csv'
        calculate_investment_performance(input_csv, output_csv)
