import argparse
import csv
import os
from datetime import datetime
from collections import defaultdict

def clean_trade_date(date_str):
    return date_str.split()[0]

def parse_multiple_trades(content):
    lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
    trades = []

    i = 0
    while i < len(lines):
        if "Buy" in lines[i] or "Sell" in lines[i]:
            trade = {}

            date_action = lines[i].split()
            trade['Trade date'] = clean_trade_date(date_action[0])
            trade['Action'] = date_action[1]
            i += 2

            trade['Symbol'] = lines[i].strip()
            i += 2

            trade['Quantity'] = int(lines[i])
            i += 1

            price_total_parts = lines[i].split()
            trade['Price'] = float(price_total_parts[0].replace('$', '').replace(',', ''))
            trade['Total'] = float(price_total_parts[-1].replace('$', '').replace(',', ''))
            trade['Commission'] = 0.00

            trades.append(trade)
        i += 1
    return trades

def calculate_interest(principal, trade_date_str, rate=0.05):
    trade_date = datetime.strptime(trade_date_str, '%m/%d/%Y')
    today = datetime.today()
    days = (today - trade_date).days
    interest = principal * rate * days / 365
    return interest

def calculate_breakeven(total, interest, quantity):
    return round((abs(total) + interest) / quantity, 2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", help="Input file name", type=str)
    parser.add_argument("-c", help="Input from command line", action='store_true')
    args = parser.parse_args()

    if args.i:
        with open(args.i, 'r') as file:
            content = file.read()
    elif args.c:
        print("Paste the trade details and press Enter twice:")
        content = ""
        while True:
            try:
                line = input()
                if not line.strip():
                    break
                content += line + "\n"
            except EOFError:
                break
    else:
        print("You must provide either -i or -c.")
        return

    trades = parse_multiple_trades(content)

    # CSV Write
    filename = "trades.csv"
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='') as csvfile:
        fieldnames = ['Trade date', 'Symbol', 'Action', 'Quantity', 'Price', 'Total', 'Commission']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        for trade in trades:
            writer.writerow(trade)

            interest = calculate_interest(abs(trade['Total']), trade['Trade date'])
            breakeven_price = calculate_breakeven(trade['Total'], interest, trade['Quantity'])

            print(f"\nTrade: {trade['Symbol']} on {trade['Trade date']}")
            print(f"  Interest accrued @5% APR: ${interest:.2f}")
            print(f"  Breakeven sell price: ${breakeven_price:.2f}")

    # Group and summarize by symbol
    grouped = defaultdict(list)
    for trade in trades:
        grouped[trade['Symbol']].append(trade)

    print("\n📊 Symbol Summary with Wash-Sale Safe Breakeven:")

    for symbol, lots in grouped.items():
        total_quantity = sum(t['Quantity'] for t in lots)
        total_cost = sum(abs(t['Total']) for t in lots)
        total_interest = sum(calculate_interest(abs(t['Total']), t['Trade date']) for t in lots)
        #**# Change: use highest price, not lowest**
        highest_price = max(t['Price'] for t in lots)

        breakeven = round((total_cost + total_interest) / total_quantity, 2)

        # Enforce wash-sale rule: must sell no lower than the highest purchase price
        if breakeven < highest_price:
            breakeven = highest_price

        print(f"\nSymbol: {symbol}")
        print(f"  Total Quantity: {total_quantity}")
        print(f"  Total Cost: ${total_cost:.2f}")
        print(f"  Total Interest @5%: ${total_interest:.2f}")
        print(f"  Minimum Allowed Sell Price (no wash-sale risk): ${highest_price:.2f}")
        print(f"  ✅ Final Breakeven Price: ${breakeven:.2f}")

if __name__ == "__main__":
    main()

