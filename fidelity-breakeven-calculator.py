# Complete, optimized and debugged version of the breakeven calculator and benchmark comparison script

from datetime import datetime
import pandas as pd
import yfinance as yf
import os

# Constants
SAVINGS_RATE = 0.05
DATE_FORMAT = "%b-%d-%Y"
TODAY = datetime.today()

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
            except Exception:
                continue

    benchmark_df = pd.DataFrame(results)
    return benchmark_df, symbols

def get_spy_performance(trades):
    spy_data = yf.download('SPY', start=min(t['Purchase Date'] for t in trades).date(),
                           end=datetime.today().date() + pd.Timedelta(days=1),
                           progress=False, auto_adjust=True)
    spy_returns = {}
    for trade in trades:
        purchase_date = trade['Purchase Date'].date()
        try:
            purchase_price = spy_data.loc[spy_data.index >= pd.to_datetime(purchase_date), 'Close'].iloc[0].item()
            current_price = spy_data['Close'].iloc[-1].item()
            percent_change = ((current_price - purchase_price) / purchase_price) * 100
            spy_returns[trade['Purchase Date'].strftime("%Y-%m-%d")] = round(percent_change, 2)
        except Exception:
            spy_returns[trade['Purchase Date'].strftime("%Y-%m-%d")] = None
    return spy_returns

def fetch_sp500_list():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        tables = pd.read_html(url)
        sp500_table = tables[0]
        sp500_table.to_csv("sp500_list.csv", index=False)
        print("✅ S&P 500 list saved to 'sp500_list.csv'")
    except Exception as e:
        print(f"Error fetching S&P 500 list: {e}")

def compare_sp500_performance(trades):
    try:
        sp500_df = pd.read_csv("sp500_list.csv")
    except FileNotFoundError:
        print("Error: 'sp500_list.csv' not found. Please run fetch_sp500_list() first.")
        return

    symbols = sp500_df['Symbol'].tolist()
    today = datetime.today().date()
    results = []
    failures = []

    total_tasks = len(symbols)
    completed = 0

    for symbol in symbols:
        yf_symbol = symbol.replace('.', '-')
        try:
            data = yf.download(yf_symbol, start=min(t['Purchase Date'] for t in trades).date(),
                               end=today + pd.Timedelta(days=1), progress=False, auto_adjust=True)
            if data.empty:
                raise ValueError("Empty data returned")

            for trade in trades:
                purchase_date = trade['Purchase Date'].date()
                investment_amount = trade['Original Cost Basis']
                try:
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
                except Exception as inner_e:
                    failures.append({
                        'Symbol': symbol,
                        'Date': purchase_date,
                        'Error': str(inner_e)
                    })

        except Exception as outer_e:
            failures.append({
                'Symbol': symbol,
                'Date': '',
                'Error': str(outer_e)
            })

        completed += 1
        if completed % 10 == 0 or completed == total_tasks:
            print(f"Progress: {completed} of {total_tasks} stocks processed...")

    if results:
        df = pd.DataFrame(results)
        df.sort_values(by='Percent Change', ascending=False, inplace=True)
        filename = f"sp500_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        print(f"\n✅ S&P 500 performance comparison saved to '{filename}'")

    if failures:
        fail_df = pd.DataFrame(failures)
        fail_filename = f"sp500_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        fail_df.to_csv(fail_filename, index=False)
        print(f"⚠️  Failed downloads logged to '{fail_filename}'")

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

    spy_performance = get_spy_performance(benchmark_trades)
    for r in results:
        if r['Purchase Date'] != '---':
            spy_return = spy_performance.get(r['Purchase Date'], None)
            r['Vs SPY (%)'] = round(-spy_return, 2) if spy_return is not None else 'N/A'
        else:
            r['Vs SPY (%)'] = '---'

    trade_df = pd.DataFrame(results)
    print("\nTrade Summary:\n")
    print(trade_df.to_string(index=False))

    benchmark_df, benchmark_symbols = compare_against_benchmark(benchmark_trades)

    if not benchmark_df.empty:
        print("\nBenchmark Comparison (vs: " + ", ".join(benchmark_symbols) + "):\n")
        print(benchmark_df.to_string(index=False))

        symbols_header = pd.DataFrame([{
            'Symbol': f"Benchmarks used: {', '.join(benchmark_symbols)}"
        }])
        empty_row = pd.Series(dtype=object)
        final_output = pd.concat([trade_df, pd.DataFrame([empty_row]), symbols_header, benchmark_df], ignore_index=True)
    else:
        final_output = trade_df

    output_file = get_output_filename()
    final_output.to_csv(output_file, index=False)
    print(f"\n✅ Results saved to {output_file}")

    run_sp500 = input("\nWould you like to compare your investments against all S&P 500 stocks? (y/n): ").strip().lower()
    if run_sp500 == 'y':
        fetch_sp500_list()
        compare_sp500_performance(benchmark_trades)

if __name__ == "__main__":
    main()
