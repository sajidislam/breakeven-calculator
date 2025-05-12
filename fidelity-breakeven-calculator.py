from datetime import datetime
import pandas as pd

# Settings
SAVINGS_RATE = 0.05  # 5% annual
DATE_FORMAT = "%b-%d-%Y"  # e.g., Jan-16-2025
TODAY = datetime.today()

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

def main():
    results = []

    with open('input.txt', 'r') as f:
        for line in f:
            if not line.strip() or line.lower().startswith('acquired'):
                continue  # Skip header or empty lines

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

    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    # Total interest-adjusted cost and total quantity
    total_adjusted_cost = sum(r['Interest-Adjusted Total Cost'] for r in results)
    total_quantity = sum(r['Quantity'] for r in results)
    avg_sale_price_required = round(total_adjusted_cost / total_quantity, 4)

    # Add summary row
    summary_row = {
        'Purchase Date': '---',
        'Quantity': total_quantity,
        'Original Cost Basis': '---',
        'Interest-Adjusted Total Cost': round(total_adjusted_cost, 2),
        'Breakeven Price': avg_sale_price_required
    }

    results.append(summary_row)

    df = pd.DataFrame(results)
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()
