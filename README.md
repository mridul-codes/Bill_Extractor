# 🧾 AI Smart Bill Extractor & Expense Tracker

A powerful automation tool that uses Google Gemini AI to extract detailed line-item data from invoice images and PDFs. It automatically parses unstructured bills into a structured Excel report for easy expense tracking.

---

## 🚀 Key Features

* **Multi-Format Support:** Handles PDF, JPG, PNG, and JPEG files.
* **Deep Extraction:** Captures not just the total, but individual line items including:
    * Seller Details (Name, GSTIN)
    * Invoice Metadata (Number, Date)
    * Item Details (Description, HSN, Quantity, Tax Rate, Amounts).
* **Smart Model Selection:** Automatically cycles through Gemini models (`gemini-2.5-flash`, `gemini-3-flash`, `gemini-2.5-flash-lite`) to find the best balance of speed and accuracy, preventing crashes if one model is busy.
* **Secure:** Implements environment variable protection (`.env`) to keep API keys safe.
* **Dual Interface:**
    * **CLI Mode:** Batch process a folder of bills automatically.
    * **GUI Mode:** Drag-and-drop web interface using Streamlit.

---

## 🛠️ Installation & Setup


### 1. Clone the Repository
Download the project files to your local machine.

### 2. Install Dependencies
Open your terminal/command prompt in the project folder and run:

```bash
pip install google-genai pandas python-dotenv openpyxl streamlit xlsxwriter
```
### 3. Secure Configuration (`.env`)
This project uses a `.env` file to manage secrets securely.

1.  **Get your API Key:** Visit [Google AI Studio](https://aistudio.google.com/) and generate a Gemini API key.
2.  **Create the file:** Create a new file in your project root named `.env`.
3.  **Add the key:** Paste the following line into the file (replace with your actual key):

```text
GOOGLE_API_KEY=AIzaSy_Your_Actual_Key_Here
```
---
###  🏃‍♂️ How to Run
---
Option A: 
Batch Processing (CLI)Best for processing many files at once.
Place all your bill images/PDFs inside the scanned_bills folder.
Run the main script:
```bash
    python main.py
```
The script will process each file and append the data to Final_Expenses.xlsx.
Option B: 
Web Interface (GUI)Best for visual feedback and uploading individual files.
Start the Streamlit app:
```bash
    streamlit run app.py
```
## 📊 Output Data Format

The generated `Final_Expenses.xlsx` will contain the following columns:

| Column Header | Description |
| :--- | :--- |
| **Purchase From** | Name of the shop/seller |
| **INVOICE** | Invoice Number |
| **GST NO** | Seller's Tax Identification Number |
| **DATE** | Billing Date (YYYY-MM-DD) |
| **DESCRIPTION** | Item Name |
| **HSN CODE** | Harmonized System of Nomenclature code |
| **QTY** | Quantity Purchased |
| **GST** | Tax Rate (Decimal, e.g., 0.18) |
| **PRICE (inc Tax)** | Unit price including tax |
| **AMOUNT (inc Tax)** | Total line amount |

---

## ⚠️ Troubleshooting

* **Quota Exceeded Error:**
    The script uses the free tier of Gemini. If you process too many bills too fast, you may hit a rate limit. The CLI script has a built-in pause (approx. 4 seconds) to help prevent this.

* **ModuleNotFoundError:**
    Ensure you installed the requirements in step 2, specifically `python-dotenv`.

* **API Key Not Found:**
    Make sure your `.env` file is named exactly `.env` (with the dot) and is in the same folder as `main.py`.

---

## 🛡️ Security Note

This project adheres to security best practices by ignoring sensitive user data:

* **`.env`**: Ignored to protect credentials.
* **`scanned_bills/`**: Ignored to protect personal financial documents.
* **`*.xlsx`**: Ignored to protect the financial output report.