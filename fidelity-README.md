# Fidelity Breakeven Calculator and Benchmark Comparison Tool

This Python script helps you calculate interest-adjusted breakeven prices for stock/ETF purchases and compare their performance against benchmarks like SPY or the S&P 500 index.

---

## 🔍 Features

- 📈 Calculates breakeven prices adjusted for interest over time
- 💰 Compares performance to SPY and user-specified benchmarks
- 📊 Optionally compares performance against all S&P 500 stocks
- 🧠 Smart retry logic for failed API calls
- 📝 Outputs a detailed CSV summary report

---

## 🗂️ Input Format

The script expects a tab-separated `.txt` file (e.g. exported from Fidelity) with columns like:

Acquired 01-Jan-2021 XYZ ... Quantity ... $Cost Basis

Only lines with valid trades will be processed.

---

## 🚀 Usage

### 📦 Requirements

- Python 3.7+
- Packages:
  - `pandas`
  - `yfinance`
  - `concurrent.futures` (standard)
  - `argparse` (standard)

Install dependencies:

```bash
pip install -r requirements.txt
🔧 Run the Script
python3 fidelity_breakeven_calculator.py -i input.txt -s AAPL
You can also run it without arguments. It will prompt for anything missing.
python3 fidelity_breakeven_calculator.py

📝 Options
| Option           | Description                         |
| ---------------- | ----------------------------------- |
| `-i`, `--input`  | Input filename (e.g. `input.txt`)   |
| `-s`, `--symbol` | Main stock or ETF symbol to analyze |

📤 Output
CSV file containing:

Breakeven calculations

Benchmark comparison

Optional full S&P 500 performance comparison

Files are saved with a timestamped name, e.g.:
breakeven_output_20250516_152530.csv
sp500_comparison_20250516_153012.csv

📈 Example Output
| Purchase Date | Quantity | Breakeven Price | Vs SPY (%) |
| ------------- | -------- | --------------- | ---------- |
| 2021-01-01    | 100      | \$105.34        | -12.8%     |

🛠️ TODO / Future Enhancements
Export to Excel with multiple tabs

GUI wrapper for non-technical users

Parallelized S&P 500 processing for speed

📄 License
MIT License

🙌 Contributions
PRs are welcome! If you have suggestions or improvements, feel free to fork the repo and open a pull request.
