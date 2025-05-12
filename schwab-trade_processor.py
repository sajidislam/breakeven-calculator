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

def export_summary_csv(symbol, lot_flags, summary_data):
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{symbol}-{now}.csv"
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Section", "Trade Date", "Quantity", "Price", "Interest", "Breakeven", "Risk Note"])

        # Summary row
        writer.writerow([
            "SUMMARY", "", summary_data['Total Qty'], summary_data['Highest Price'],
            round(summary_data['Total Interest'], 2), summary_data['Final Breakeven'], ""
        ])

        # Lot-level rows
        for lot in lot_flags:
            writer.writerow([
                "LOT BREAKDOWN", lot['date'], lot['quantity'], lot['price'],
                round(lot['interest'], 2), lot['breakeven'], lot['risk']
            ])

    print(f"\n📁 Exported: {filename}")

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

    # CSV append
    filename = "trades.csv"
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='') as csvfile:
        fieldnames = ['Trade date', 'Symbol', 'Action', 'Quantity', 'Price', 'Total', 'Commission']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        print("\nTrade Breakdown:")
        print("Trade Date   Symbol   Qty   Price   Interest   Breakeven")
        print("----------------------------------------------------------")

        for trade in trades:
            writer.writerow(trade)
            interest = calculate_interest(abs(trade['Total']), trade['Trade date'])
            breakeven_price = calculate_breakeven(trade['Total'], interest, trade['Quantity'])
            print(f"{trade['Trade date']:11} {trade['Symbol']:7} {trade['Quantity']:5} "
                  f"{trade['Price']:6.2f}   {interest:7.2f}     {breakeven_price:7.2f}")

    # Group and summarize by symbol
    grouped = defaultdict(list)
    for trade in trades:
        grouped[trade['Symbol']].append(trade)

    print("\nSymbol Summary:")

    for symbol, lots in grouped.items():
        total_quantity = sum(t['Quantity'] for t in lots)
        total_cost = sum(abs(t['Total']) for t in lots)

        lot_breakevens = []
        lot_flags = []
        highest_price = max(t['Price'] for t in lots)
        total_interest = 0.0

        for t in lots:
            interest = calculate_interest(abs(t['Total']), t['Trade date'])
            total_interest += interest
            lot_breakeven = calculate_breakeven(t['Total'], interest, t['Quantity'])
            lot_breakevens.append(lot_breakeven)

            risk = "⚠️" if lot_breakeven > max(highest_price, max(lot_breakevens)) else "-"
            lot_flags.append({
                'date': t['Trade date'],
                'price': t['Price'],
                'quantity': t['Quantity'],
                'interest': interest,
                'breakeven': lot_breakeven,
                'risk': risk
            })

        final_breakeven = max(max(lot_breakevens), highest_price)

        print("\n" + "-"*70)
        print(f"Symbol: {symbol}")
        print(f"{'Total Qty':<12}{'Total Cost':<14}{'Highest Buy':<14}"
              f"{'Interest':<12}{'Breakeven':<12}")
        print(f"{total_quantity:<12}{total_cost:<14.2f}{highest_price:<14.2f}"
              f"{total_interest:<12.2f}{final_breakeven:<12.2f}")

        print("\nLot Breakdown:")
        print("Trade Date   Qty   Price   Interest   Breakeven   Risk")
        print("-------------------------------------------------------------")
        for lot in lot_flags:
            print(f"{lot['date']:11} {lot['quantity']:5} {lot['price']:7.2f}   "
                  f"{lot['interest']:7.2f}     {lot['breakeven']:7.2f}   {lot['risk']}")

        export_summary_csv(symbol, lot_flags, {
            'Total Qty': total_quantity,
            'Highest Price': highest_price,
            'Total Interest': total_interest,
            'Final Breakeven': final_breakeven
        })

if __name__ == "__main__":
    main()
