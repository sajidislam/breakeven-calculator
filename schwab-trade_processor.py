import argparse
import csv
import os
from datetime import datetime

def parse_simple_input(content):
    lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
    data = {}

    # First line: Date and Action
    first_line_parts = lines[0].split()
    data['Trade date'] = first_line_parts[0]
    data['Action'] = first_line_parts[1]

    # Third line: Symbol
    data['Symbol'] = lines[2]

    # Fifth line: Quantity
    data['Quantity'] = int(lines[4])

    # Sixth line: Price and Total
    price_total_parts = lines[5].split()
    data['Price'] = float(price_total_parts[0].replace('$', '').replace(',', ''))
    data['Total'] = float(price_total_parts[-1].replace('$', '').replace(',', ''))

    # Commission is not listed, so assume 0
    data['Commission'] = 0.00

    return data

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

    data = parse_simple_input(content)

    # Write to CSV
    filename = "trades.csv"
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='') as csvfile:
        fieldnames = ['Trade date', 'Symbol', 'Action', 'Quantity', 'Price', 'Total', 'Commission']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            'Trade date': data['Trade date'],
            'Symbol': data['Symbol'],
            'Action': data['Action'],
            'Quantity': data['Quantity'],
            'Price': data['Price'],
            'Total': data['Total'],
            'Commission': data['Commission']
        })

    # Interest & Breakeven
    interest = calculate_interest(abs(data['Total']), data['Trade date'])
    breakeven_price = calculate_breakeven(data['Total'], interest, data['Quantity'])

    print(f"\nInterest accrued at 5% APR since {data['Trade date']}: ${interest:.2f}")
    print(f"Breakeven sell price per share: ${breakeven_price:.2f}")

if __name__ == "__main__":
    main()
