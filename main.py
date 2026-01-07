import os
import time
import json
import mimetypes
import pandas as pd
from google import genai
from google.genai import types
from dotenv import load_dotenv        # This is only if you are using .env file to mask you API key

# --- CONFIGURATION ---
# API_KEY = "Give your API key from google AI studio"

load_dotenv() # Load variables from .env file

# Fetch the key securely 
API_KEY = os.getenv("GOOGLE_API_KEY")

# SETUP CLIENT
client = genai.Client(api_key=API_KEY)

# PATHS SETUP
script_directory = os.path.dirname(os.path.abspath(__file__))
INPUT_FOLDER = os.path.join(script_directory, "scanned_bills")      # This is folder or storing the images 
OUTPUT_FILE = os.path.join(script_directory, "Final_Expenses.xlsx") # This is the output excel file


def get_mime_type(file_path):
    """Detects if file is PDF or Image"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/pdf"

# --- UPDATED MODEL LIST (Based on your account) ---
CANDIDATE_MODELS = [
    "gemini-2.5-flash",       # Best balance of Speed + Accuracy (Primary)
    "gemini-3-flash",         # Smarter, but maybe less stable (Backup 1)
    "gemini-2.5-flash-lite",  # Fastest, but least accurate (Backup 2)
    "gemini-flash-latest"     # Google's auto-choice (Safety Net)               # Change this according to your available models
]

def get_working_model(file_path, prompt):
    # Detect proper MIME type
    mime_type = get_mime_type(file_path)
    
    with open(file_path, "rb") as f:
        file_content = f.read()

    print(f"   (Size: {len(file_content)} bytes | Type: {mime_type})")

    for model_name in CANDIDATE_MODELS:
        print(f"Trying {model_name}...", end=" ")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Content(
                        parts=[
                            types.Part.from_bytes(data=file_content, mime_type=mime_type),
                            types.Part.from_text(text=prompt)
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            print("SUCCESSFULL!")
            return json.loads(response.text), model_name
        except Exception as e:
            # Print the EXACT error so we can see it
            if "429" in str(e):
                print("QUOTA EXCEEDED (Wait or swap key)")
            elif "503" in str(e):
                print("OVERLOADED (Server busy)")
            elif "404" in str(e):
                print("NOT FOUND (Model name wrong)")
            else:
                print(f"ERROR: {str(e)[:100]}") # Print first 100 chars of error
            continue
    
    raise Exception("All models failed to respond.")

def process_bill(pdf_path):
    print(f"   Processing: {os.path.basename(pdf_path)}")

    prompt = """
    Extract invoice data into JSON:
    1. "seller_name": Shop Name
    2. "invoice_no": Invoice Number
    3. "seller_gst": GSTIN
    4. "bill_date": Date (YYYY-MM-DD)
    5. "items": List of items with "description", "hsn", "qty", "gst_rate" (decimal), "price_inc_tax", "amount_inc_tax"
    """

   
    data, used_model = get_working_model(pdf_path, prompt)
    return data

def save_to_excel(data):
    rows = []
    seller = data.get("seller_name", "").upper()
    inv = data.get("invoice_no", "")
    gst_no = data.get("seller_gst", "")
    date = data.get("bill_date", "")

    for item in data.get("items", []):
        rows.append({
            "Purchase From": seller,
            "INVOICE": inv,
            "GST NO": gst_no,
            "DATE": date,
            "DESCRIPTION OF GOODS": item.get("description"),
            "HSN CODE": item.get("hsn"),
            "QTY": item.get("qty"),
            "GST": item.get("gst_rate"),
            "PRICE (inc Tax)": item.get("price_inc_tax"),
            "AMOUNT (inc Tax)": item.get("amount_inc_tax")
        })

    if not rows: return

    df = pd.DataFrame(rows)
    columns = ["Purchase From", "INVOICE", "GST NO", "DATE", "DESCRIPTION OF GOODS", 
               "HSN CODE", "QTY", "GST", "PRICE (inc Tax)", "AMOUNT (inc Tax)"]
    
    # Filter only columns that exist
    df = df[[c for c in columns if c in df.columns]]

    if os.path.exists(OUTPUT_FILE):
        # FIX: Changed engine to 'openpyxl' for appending
        with pd.ExcelWriter(OUTPUT_FILE, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
            try:
                start_row = writer.sheets['Sheet1'].max_row
            except KeyError:
                start_row = 0
            df.to_excel(writer, index=False, header=(start_row==0), startrow=start_row)
    else:
        # For new files, simple write is fine
        df.to_excel(OUTPUT_FILE, index=False)

def main():
    if not os.path.exists(INPUT_FOLDER):
        os.makedirs(INPUT_FOLDER)
        print(f"Put bills in: {INPUT_FOLDER}")
        return

    # Updated to find images too
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png'))]
    print(f"Found {len(files)} bills.")
    print("-" * 40)

    for i, file_name in enumerate(files):
        print(f"Processing [{i+1}/{len(files)}]: {file_name}")
        try:
            full_path = os.path.join(INPUT_FOLDER, file_name)
            data = process_bill(full_path)
            save_to_excel(data)
            print("Success!")
        except Exception as e:
            print(f"\n   FAILED: {e}")
        
        time.sleep(4) # Safety pause

    print("-" * 40)
    print(f"DONE! File: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()