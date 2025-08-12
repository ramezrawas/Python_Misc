Here’s the polished **`README.md`** version so it looks clean and professional on GitHub:

---

````markdown
# Receipt Parsing Script

## 📜 Description
This Python script extracts **total amounts** and **service periods** from German PDF receipts.  
It is optimized for receipts containing keywords like **"Bruttorechnungsbetrag"** and **"Summe"**,  
and intelligently selects the correct amount even if multiple amounts appear.

---

## ✨ Features
- **Total amount extraction**:
  - Searches the section after `Bruttorechnungsbetrag`
  - Falls back to any line containing `Summe`
- **Service period (Zeitraum) extraction**:
  - Handles formats like:
    - `Leistungszeitraum`
    - `Für den Zeitraum`
    - `von ... bis ...`
  - Corrects missing or shortened years
- **European number format support** (comma as decimal, dot as thousand separator)
- **CSV output** with:
  - File name
  - Raw extracted total
  - Normalized numeric total
  - Duration (service period)

---

## 📦 Requirements
- Python **3.8** or later
- [pandas](https://pandas.pydata.org/)
- [pdfplumber](https://github.com/jsvine/pdfplumber)

Install dependencies:
```bash
pip install pandas pdfplumber
````

---

## 🚀 Usage

Run from the command line:

```bash
python extract_amount_from_receipts.py -i /path/to/receipts -o output.csv
```

**Options**:

| Option          | Description                                                                   |
| --------------- | ----------------------------------------------------------------------------- |
| `-i, --input`   | Directory containing PDF receipts (default: `./receipts`)                     |
| `-o, --output`  | Output CSV file path (default: `./receipt_totals_with_duration_textonly.csv`) |
| `-v, --verbose` | Enable detailed logging                                                       |

---

### Example

```bash
python extract_amount_from_receipts.py -i receipts/ -o results.csv -v
```

---

## 👤 Author

Your Name

---

## 📄 License

This project is licensed under the **MIT License**.

```

---

If you want, I can also **add this README.md file to your folder right now** so it’s ready to commit and push with your script to GitHub. That way you don’t have to manually create it.  
Do you want me to do that?
```
