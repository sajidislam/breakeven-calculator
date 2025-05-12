import yfinance as yf
from datetime import datetime
import pandas as pd
import os

SAVINGS_RATE = 0.05
DATE_FORMAT = "%b-%d-%Y"
TODAY = datetime.today()

def get_spy_performance(trades):
    spy_data = yf.download('SPY',
                           start=min(t['Purchase Date'] for t in trades).date(),
                           end=datetime.today().date() + pd.Timedelta(days=1),
                           progress=False,
                           auto_adjust=True)

    spy_returns = {}

    for trade in trades:
        purchase_date = trade['Purchase Date'].date()

        try:
            purchase_price = spy_data.loc[spy_data.index >= pd.to_datetime(purchase_date), 'Close'].iloc[0].item()
            current_price = spy_data['Close'].iloc[-1].item()
            percent_change = ((current_price - purchase_price) / purchase_price) * 100
            spy_returns[trade['Purchase Date'].strftime("%Y-%m-%d")] = round(percent_change, 2)
        except Exception as e:
            spy_returns[trade['Purchase Date'].strftime("%Y-%m-%d")] = None
            print(f"Warning: Could not calculate SPY return for {purchase_date}: {e}")

    return spy_returns


def get_output_filename(prefix="breakeven_output"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.csv"

def compute_interest_adjusted_cost(purchase_date, cost_basis_total):
    days_held = (TODAY - purchase_date).days
    interest = cost_basis_total * ((1 + SAVINGS_RATE / 365) ** days_held - 1)
    return cost_basis_total + interest

def parse_line(line):
    parts = line.strip().split('\t')
    purchase_date = datetime.strptime(parts[0], DATE_FORMAT)
    quantity = int(parts[5])
    cost_basis_total = float(parts[7].replace('$','').replace(',',''))
    return purchase_date, quantity, cost_basis_total

def compare_against_benchmark(trades):

    symbols_input = input("Enter one or more benchmark symbols (comma-separated). SPY will always be included: ")
    user_symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
    symbols = ['SPY'] + [s for s in user_symbols if s != 'SPY']


    today = datetime.today().date()
    results = []

    for symbol in symbols:
        for trade in trades:
            purchase_date = trade['Purchase Date'].date()
            investment_amount = trade['Original Cost Basis']

            try:
                data = yf.download(symbol, start=purchase_date, end=today + pd.Timedelta(days=1), progress=False, auto_adjust=True)
                if data.empty:
                    print(f"No data found for {symbol} on or after {purchase_date}")
                    continue

                purchase_price = data.loc[data.index >= pd.to_datetime(purchase_date), 'Close'].iloc[0].item()
                current_price = data['Close'].iloc[-1].item()

                shares = investment_amount / purchase_price
                current_value = shares * current_price
                percent_change = ((current_value - investment_amount) / investment_amount) * 100

                results.append({
                    'Symbol': symbol,
                    'Purchase Date': purchase_date.strftime("%Y-%m-%d"),
                    'Investment Amount': investment_amount,
                    'Current Value': round(current_value, 2),
                    'Percent Change': round(percent_change, 2)
                })
            except Exception as e:
                print(f"Error fetching data for {symbol} on {purchase_date}: {e}")
                continue

    benchmark_df = pd.DataFrame(results)
    print("\nBenchmark Comparison:\n")
    print(benchmark_df.to_string(index=False))
    return benchmark_df, symbols

def main():
    results = []
    benchmark_trades = []

    with open('input.txt', 'r') as f:
        for line in f:
            if not line.strip() or line.lower().startswith('acquired'):
                continue

            purchase_date, quantity, cost_basis_total = parse_line(line)
            adjusted_cost = compute_interest_adjusted_cost(purchase_date, cost_basis_total)
            breakeven_price = adjusted_cost / quantity

            results.append({
                'Purchase Date': purchase_date.strftime("%Y-%m-%d"),
                'Quantity': quantity,
                'Original Cost Basis': round(cost_basis_total, 2),
                'Interest-Adjusted Total Cost': round(adjusted_cost, 2),
                'Breakeven Price': round(breakeven_price, 4)
            })

            benchmark_trades.append({
                'Purchase Date': purchase_date,
                'Original Cost Basis': cost_basis_total
            })

    total_adjusted_cost = sum(r['Interest-Adjusted Total Cost'] for r in results)
    total_quantity = sum(r['Quantity'] for r in results)
    avg_sale_price_required = round(total_adjusted_cost / total_quantity, 4)

    results.append({
        'Purchase Date': '---',
        'Quantity': total_quantity,
        'Original Cost Basis': '---',
        'Interest-Adjusted Total Cost': round(total_adjusted_cost, 2),
        'Breakeven Price': avg_sale_price_required
    })

    df = pd.DataFrame(results)
    print("\nTrade Summary:\n")
    print(df.to_string(index=False))

    spy_performance = get_spy_performance(benchmark_trades)

    for r in results:
        if r['Purchase Date'] != '---':
            spy_return = spy_performance.get(r['Purchase Date'], None)
            if spy_return is not None:
                r['Vs SPY (%)'] = round(-spy_return, 2)  # Your return is 0% at breakeven
            else:
                r['Vs SPY (%)'] = 'N/A'
        else:
            r['Vs SPY (%)'] = '---'

    # Run benchmark comparison
    #compare_against_benchmark(benchmark_trades)
    #benchmark_df = compare_against_benchmark(benchmark_trades)
    benchmark_df, benchmark_symbols = compare_against_benchmark(benchmark_trades)

    # Combine both trade data and benchmark data
    trade_df = pd.DataFrame(results)
    print("\nTrade Summary:\n")
    print(trade_df.to_string(index=False))

    if not benchmark_df.empty:
        #print("\nBenchmark Comparison:\n")
        print("\nBenchmark Comparison (vs: " + ", ".join(benchmark_symbols) + "):\n")
        print(benchmark_df.to_string(index=False))

        # Add symbols row above the benchmark data
        symbols_header = pd.DataFrame([{
            'Symbol': f"Benchmarks used: {', '.join(benchmark_symbols)}"
        }])

        # Add an empty row and then the benchmark section to CSV
        empty_row = pd.Series(dtype=object)
        final_output = pd.concat([trade_df, pd.DataFrame([empty_row]), benchmark_df], ignore_index=True)
    else:
        final_output = trade_df

    # Save to CSV
    output_file = get_output_filename()
    final_output.to_csv(output_file, index=False)
    print(f"\n✅ Results saved to {output_file}")

#------------------------
#------------------------
if __name__ == "__main__":
    main()

