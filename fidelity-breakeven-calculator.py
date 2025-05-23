# Complete, optimized and debugged version of the breakeven calculator and benchmark comparison script

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pandas as pd
import yfinance as yf
import os
import time
import random
import argparse

# Constants
SAVINGS_RATE = 0.05
DATE_FORMAT = "%b-%d-%Y"
TODAY = datetime.today()


def process_symbol_lot(symbol, trade, today):
    results = []
    failures = []
    yf_symbol = symbol.replace('.', '-')
    purchase_date = trade['Purchase Date'].date()
    investment_amount = trade['Original Cost Basis']

    try:
        data = yf.download(yf_symbol, start=purchase_date, end=today + pd.Timedelta(days=1),
                           progress=False, auto_adjust=True)
        if data.empty:
            raise ValueError("No data returned for symbol on or after purchase date.")

        price = data.loc[data.index >= pd.to_datetime(purchase_date), 'Close']
        if price.empty:
            raise ValueError("No price available on or after trade date.")

        purchase_price = price.iloc[0].item()
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
        failures.append({
            'Symbol': symbol,
            'Date': purchase_date,
            'Error': str(e)
        })

    return results, failures


def retry_failed_symbols_once(failures, trades, today):
    retry_results = []
    retry_failures = []

    symbols_to_retry = list(set(f['Symbol'] for f in failures if f['Symbol']))
    print(f"\n🔁 Retrying {len(symbols_to_retry)} failed tickers...")

    def retry(symbol):
        return process_sp500_symbol(symbol, trades, today)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(retry, symbol): symbol for symbol in symbols_to_retry}

        for count, future in enumerate(as_completed(futures), 1):
            symbol = futures[future]
            try:
                results, failures = future.result()
                retry_results.extend(results)
                retry_failures.extend(failures)
            except Exception as e:
                retry_failures.append({'Symbol': symbol, 'Date': '', 'Error': str(e)})

            if count % 5 == 0 or count == len(symbols_to_retry):
                print(f"Retry Progress: {count}/{len(symbols_to_retry)} completed")

    return retry_results, retry_failures

def process_sp500_symbol(symbol, trades, today):
    results = []
    failures = []

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
            except Exception as e:
                failures.append({
                    'Symbol': symbol,
                    'Date': purchase_date,
                    'Error': str(e)
                })

    except Exception as e:
        failures.append({
            'Symbol': symbol,
            'Date': '',
            'Error': str(e)
        })
#    time.sleep(random.uniform(0.1, 0.3))  # Sleep 100–300 ms
    time.sleep(random.uniform(1.0, 20.0))  # Sleep between 1000ms and 9000ms
    time.sleep(9.0)  # Exactly 5 seconds
    return results, failures


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
    import time
    import pandas as pd
    from datetime import datetime
    import yfinance as yf

    try:
        sp500_df = pd.read_csv("sp500_list.csv")
    except FileNotFoundError:
        print("Error: 'sp500_list.csv' not found. Please run fetch_sp500_list() first.")
        return

    symbols = sp500_df['Symbol'].dropna().unique().tolist()
    today = datetime.today().date()
    all_results = []
    all_failures = []

    print(f"🔄 Running single-threaded, high-accuracy S&P 500 comparison...")

    count = 0
    total = len(symbols) * len(trades)

    for symbol in symbols:
        yf_symbol = symbol.replace('.', '-')
        for trade in trades:
            purchase_date = trade['Purchase Date'].date()
            investment_amount = trade['Original Cost Basis']

            try:
                data = yf.download(yf_symbol, start=purchase_date, end=today + pd.Timedelta(days=1),
                                   progress=False, auto_adjust=True)
                if data.empty:
                    raise ValueError("No data returned for symbol on or after purchase date.")

                price = data.loc[data.index >= pd.to_datetime(purchase_date), 'Close']
                if price.empty:
                    raise ValueError("No price available on or after trade date.")

                purchase_price = price.iloc[0].item()
                current_price = data['Close'].iloc[-1].item()
                shares = investment_amount / purchase_price
                current_value = shares * current_price
                percent_change = ((current_value - investment_amount) / investment_amount) * 100

                all_results.append({
                    'Symbol': symbol,
                    'Purchase Date': purchase_date.strftime("%Y-%m-%d"),
                    'Investment Amount': investment_amount,
                    'Current Value': round(current_value, 2),
                    'Percent Change': round(percent_change, 2)
                })

            except Exception as e:
                all_failures.append({
                    'Symbol': symbol,
                    'Date': purchase_date,
                    'Error': str(e)
                })

            count += 1
            if count % 25 == 0 or count == total:
                print(f"Progress: {count}/{total} symbol-lot comparisons completed...")

            # Sleep to avoid DNS overload or rate-limits
            time.sleep(1.0)

    if all_results:
        df = pd.DataFrame(all_results)
        df.sort_values(by='Percent Change', ascending=False, inplace=True)
        filename = f"sp500_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        print(f"\n✅ Accurate S&P 500 performance comparison saved to '{filename}'")

    if all_failures:
        fail_df = pd.DataFrame(all_failures)
        fail_filename = f"sp500_failed_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        fail_df.to_csv(fail_filename, index=False)
        print(f"⚠️  Remaining failed comparisons saved to '{fail_filename}'")

def parse_cost_basis(val):
    if isinstance(val, (int, float)):
        return val
    return float(str(val).replace('$', '').replace(',', ''))

def project_future_values(results, future_disposal_date, symbol):
    """Compute future interest and adjusted cost for each lot and return rows."""
    future_rows = []

    # ✅ Filter valid trade rows (exclude TOTAL or separator rows)

    trade_lots = [
        r for r in results
        if isinstance(r.get('Quantity'), (int, float))
        and isinstance(r.get('Purchase Date'), str)
        and r['Purchase Date'] not in ['TOTAL', '---']
    ]
    total_quantity = sum(r['Quantity'] for r in trade_lots)

    total_cost_basis = sum(parse_cost_basis(r['Original Cost Basis']) for r in trade_lots)
    avg_cost_basis_per_share = round(total_cost_basis / total_quantity, 2)

    total_future_interest = 0.0
    total_future_adjusted_cost = 0.0

    for trade in trade_lots:
        purchase_date = datetime.strptime(trade['Purchase Date'], "%Y-%m-%d")
        
        cost_basis = parse_cost_basis(trade['Original Cost Basis'])


        quantity = trade['Quantity']

        days_held_future = (future_disposal_date - purchase_date).days
        future_interest = cost_basis * ((1 + SAVINGS_RATE / 365) ** days_held_future - 1)
        future_adjusted_cost = cost_basis + future_interest

        total_future_interest += future_interest
        total_future_adjusted_cost += future_adjusted_cost

        future_rows.append({
            'Symbol': trade['Symbol'],
            'Purchase Date': trade['Purchase Date'],
            'Quantity': quantity,
            'Original Cost Basis': cost_basis,
            'Holding Duration (days)': f"{days_held_future} (future)",
            'Interest Accrued': round(future_interest, 2),
            'Interest-Adjusted Total Cost': round(future_adjusted_cost, 2),
            'Breakeven Price': round(future_adjusted_cost / quantity, 4),
            'Vs SPY (%)': 'N/A'
        })

    # Add separator
    future_rows.append({
        'Symbol': '---',
        'Purchase Date': '---',
        'Quantity': '---',
        'Original Cost Basis': '---',
        'Holding Duration (days)': '---',
        'Interest Accrued': '---',
        'Interest-Adjusted Total Cost': '---',
        'Breakeven Price': '---',
        'Vs SPY (%)': '---'
    })

    # Add FUTURE TOTAL row
    future_rows.append({
        'Symbol': symbol,
        'Purchase Date': f"FUTURE ({future_disposal_date.strftime('%Y-%m-%d')})",
        'Quantity': total_quantity,
        'Original Cost Basis': f"${avg_cost_basis_per_share:,.2f}",
        'Holding Duration (days)': '---',
        'Interest Accrued': f"${total_future_interest:,.2f}",
        'Interest-Adjusted Total Cost': f"${total_future_adjusted_cost:,.2f}",
        'Breakeven Price': f"${(total_future_adjusted_cost / total_quantity):,.2f}",
        'Vs SPY (%)': '---'
    })

    return pd.DataFrame(future_rows)


def main():
    parser = argparse.ArgumentParser(description="Fidelity Breakeven Calculator")
    parser.add_argument('-i', '--input', help='Input file name (e.g., input.txt)')
    parser.add_argument('-s', '--symbol', help='Stock or ETF symbol to analyze (e.g., AAPL)')
    parser.add_argument('-d', '--disposal', help='Future disposal date (e.g., 2025-12-31)')
    args = parser.parse_args()

    input_filename = args.input
    main_symbol = args.symbol

    # Prompt if missing
    if not input_filename:
        input_filename = input("Enter the name of the input file (e.g., input.txt): ").strip()
    if not main_symbol:
        main_symbol = input("Enter the stock/ETF symbol to analyze: ").strip().upper()
    else:
        main_symbol = main_symbol.strip().upper()

    # Handle disposal date
    if args.disposal:
        try:
            future_disposal_date = datetime.strptime(args.disposal, "%Y-%m-%d")
        except ValueError:
            print("❌ Invalid disposal date format. Please use YYYY-MM-DD.")
            return
    else:
        user_input = input("Enter a future disposal date (YYYY-MM-DD) or press Enter to use end of this year: ").strip()
        if user_input:
            try:
                future_disposal_date = datetime.strptime(user_input, "%Y-%m-%d")
            except ValueError:
                print("❌ Invalid date format. Please use YYYY-MM-DD.")
                return
        else:
            future_disposal_date = datetime(TODAY.year, 12, 31)

    results = []
    benchmark_trades = []

    if not os.path.exists(input_filename):
        print(f"❌ Error: File '{input_filename}' not found.")
        return

    with open(input_filename, 'r') as f:
        for line in f:
            if not line.strip() or line.lower().startswith('acquired'):
                continue

            purchase_date, quantity, cost_basis_total = parse_line(line)
            adjusted_cost = compute_interest_adjusted_cost(purchase_date, cost_basis_total)
            breakeven_price = adjusted_cost / quantity
            days_held = (TODAY - purchase_date).days
            interest_accrued = round(adjusted_cost - cost_basis_total, 2)

            results.append({
                'Symbol': main_symbol,
                'Purchase Date': purchase_date.strftime("%Y-%m-%d"),
                'Quantity': quantity,
                'Original Cost Basis': round(cost_basis_total, 2),
                'Holding Duration (days)': days_held,
                'Interest Accrued': round(interest_accrued, 2),
                'Interest-Adjusted Total Cost': round(adjusted_cost, 2),
                'Breakeven Price': round(breakeven_price, 4)
            })

            benchmark_trades.append({
                'Purchase Date': purchase_date,
                'Original Cost Basis': cost_basis_total
            })

    total_adjusted_cost = sum(r['Interest-Adjusted Total Cost'] for r in results)
    total_quantity = sum(r['Quantity'] for r in results)
    total_cost_basis = sum(r['Original Cost Basis'] for r in results if isinstance(r['Original Cost Basis'], (int, float)))
    total_interest_accrued = sum(r['Interest Accrued'] for r in results if isinstance(r['Interest Accrued'], (int, float)))
    avg_cost_basis_per_share = round(total_cost_basis / total_quantity, 2)
    avg_sale_price_required = round(total_adjusted_cost / total_quantity, 4)

    results.append({
        'Symbol': '---',
        'Purchase Date': '---',
        'Quantity': '---',
        'Original Cost Basis': '---',
        'Holding Duration (days)': '---',
        'Interest Accrued': '---',
        'Interest-Adjusted Total Cost': '---',
        'Breakeven Price': '---'
    })

    results.append({
        'Symbol': main_symbol,
        'Purchase Date': 'TOTAL',
        'Quantity': total_quantity,
        'Original Cost Basis': f"${avg_cost_basis_per_share:,.2f}",
        'Holding Duration (days)': '---',
        'Interest Accrued': f"${total_interest_accrued:,.2f}",
        'Interest-Adjusted Total Cost': f"${total_adjusted_cost:,.2f}",
        'Breakeven Price': f"${avg_sale_price_required:,.2f}"
    })

    spy_performance = get_spy_performance(benchmark_trades)
    for r in results:
        if r['Purchase Date'] != '---':
            spy_return = spy_performance.get(r['Purchase Date'], None)
            r['Vs SPY (%)'] = round(-spy_return, 2) if spy_return is not None else 'N/A'
        else:
            r['Vs SPY (%)'] = '---'

    trade_df = pd.DataFrame(results)

   
    # Insert a row of **** for spacing
    label_row = pd.Series({col: '=====' for col in trade_df.columns})
    label_row['Purchase Date'] = '=== Projected Future Values ==='
    trade_df = pd.concat([trade_df, pd.DataFrame([label_row])], ignore_index=True)


    # Compute and append future projection rows
    future_df = project_future_values(results, future_disposal_date, main_symbol)
    trade_df = pd.concat([trade_df, future_df], ignore_index=True)

    # Rename columns
    trade_df.rename(columns={
        'Symbol': 'Symbol',
        'Quantity': 'QTY',
        'Original Cost Basis': 'Cost-Basis',
        'Holding Duration (days)': 'Days-Held',
        'Interest Accrued': 'Int-Earned',
        'Interest-Adjusted Total Cost': 'Cost-Basis+INT',
        'Breakeven Price': 'Min. Sell-Price',
        'Vs SPY (%)': 'SPY%'
    }, inplace=True)

    # Format currency values
    def format_currency(val):
        return f"${val:,.2f}" if isinstance(val, (float, int)) else val

    def format_price(val):
        return f"${val:,.2f}" if isinstance(val, (float, int)) else val

    trade_df['Cost-Basis'] = trade_df['Cost-Basis'].apply(format_currency)
    trade_df['Int-Earned'] = trade_df['Int-Earned'].apply(format_currency)
    trade_df['Cost-Basis+INT'] = trade_df['Cost-Basis+INT'].apply(format_currency)
    trade_df['Min. Sell-Price'] = trade_df['Min. Sell-Price'].apply(format_price)

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
