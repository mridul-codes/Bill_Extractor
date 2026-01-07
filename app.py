import streamlit as st
import pandas as pd
import json
import time
from io import BytesIO
from google import genai
from google.genai import types

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Smart Bill Extractor", page_icon="🧾", layout="wide")

# Custom CSS to make it look cleaner
st.markdown("""
    <style>
    .main { padding-top: 2rem; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2921/2921222.png", width=80)
    st.title("Settings")
    
    api_key = st.text_input("🔑 Google API Key", type="password", help="Paste your Gemini API Key here")
    
    st.divider()
    st.write("###  Model Status")
    st.info("Auto-Select: Gemini 2.5 Flash (Priority)")
    
    st.warning("⚠️ **Limit:** ~10 Bills / Minute (Free Tier)")

# --- SMART AI LOGIC ---
CANDIDATE_MODELS = [
    "gemini-2.5-flash",       # Best balance of Speed + Accuracy (Primary)
    "gemini-3-flash",         # Smarter, but maybe less stable (Backup 1)
    "gemini-2.5-flash-lite",  # Fastest, but least accurate (Backup 2)
    "gemini-flash-latest"     # Google's auto-choice (Safety Net)              Change this according to your available models
]

def get_working_model(client, file_bytes, mime_type, prompt):
    """Tries multiple models until one works to avoid crashes."""
    last_error = ""
    
    for model_name in CANDIDATE_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Content(
                        parts=[
                            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                            types.Part.from_text(text=prompt)
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text), model_name
        except Exception as e:
            last_error = str(e)
            if "404" in str(e) or "NOT_FOUND" in str(e):
                continue # Try next model
            elif "429" in str(e):
                continue # Quota full, try next
            else:
                continue

    return None, last_error

def process_bill(file_bytes, mime_type, api_key):
    client = genai.Client(api_key=api_key)
    
    prompt = """
    Analyze this invoice image and extract data for an Excel sheet. 
    EXTRACT THESE FIELDS SPECIFICALLY:
    1. "seller_name": The name of the shop/seller (e.g. "MAYA TRADING")
    2. "invoice_no": The Invoice Number (e.g. "GST/25-26/2038")
    3. "seller_gst": The Seller's GSTIN (e.g. "18EDAPP...")
    4. "bill_date": Date in YYYY-MM-DD format
    5. "items": A list of all items bought. For each item extract:
       - "description": Item Name (e.g. "6M SURFACE BOX")
       - "hsn": HSN Code
       - "qty": Quantity (number only)
       - "gst_rate": The GST rate as a DECIMAL (e.g. if 18%, output 0.18. If 9%+9%, output 0.18)
       - "price_inc_tax": Unit Price including tax
       - "amount_inc_tax": Total Amount for this item including tax
    
    Return ONLY valid JSON.
    """
    
    return get_working_model(client, file_bytes, mime_type, prompt)

# --- MAIN APP UI ---
st.title("AI Invoice Extractor")
st.write("Upload your bills (PDF or Images) to automatically generate your Excel report.")

uploaded_files = st.file_uploader(
    "Drop your bills here", 
    type=["pdf", "png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

if uploaded_files:
    st.write(f" **{len(uploaded_files)} files selected**")
    
    if st.button(" Start Processing Bills"):
        if not api_key:
            st.error("❌ Please enter your API Key in the sidebar first!")
            st.stop()

        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []
        
        # Create tabs for better UI
        tab1, tab2 = st.tabs([" Live Data", " Logs"])
        
        for i, file in enumerate(uploaded_files):
            status_text.write(f" Processing **{file.name}**...")
            
            # Read file
            bytes_data = file.getvalue()
            mime_type = file.type
            
            # CALL AI
            data, model_used = process_bill(bytes_data, mime_type, api_key)
            
            if data:
                with tab2:
                    st.success(f" {file.name} processed using {model_used}")
                
                # Flatten Data
                seller = data.get("seller_name", "").upper()
                inv = data.get("invoice_no", "")
                gst_no = data.get("seller_gst", "")
                date = data.get("bill_date", "")

                for item in data.get("items", []):
                    results.append({
                        "Purchase From": seller,
                        "INVOICE": inv,
                        "GST NO": gst_no,
                        "DATE": date,
                        "DESCRIPTION OF GOODS": item.get("description"),
                        "HSN CODE": item.get("hsn"),
                        "QTY": item.get("qty"),
                        "GST": item.get("gst_rate"),
                        "PRICE (inc Tax)": item.get("price_inc_tax"),
                        "AMOUNT (inc Tax)": item.get("amount_inc_tax"),
                        "Source File": file.name
                    })
            else:
                with tab2:
                    st.error(f" Failed {file.name}: {model_used}")

            # Update Live Table in Tab 1
            if results:
                df_live = pd.DataFrame(results)
                cols = ["Purchase From", "INVOICE", "GST NO", "DATE", "DESCRIPTION OF GOODS", 
                        "HSN CODE", "QTY", "GST", "PRICE (inc Tax)", "AMOUNT (inc Tax)"]
                # Filter columns that exist
                valid_cols = [c for c in cols if c in df_live.columns]
                with tab1:
                    st.dataframe(df_live[valid_cols], use_container_width=True)

            # Update Progress
            progress_bar.progress((i + 1) / len(uploaded_files))
            
            # Rate Limit Pause
            time.sleep(5)

        status_text.write(" **Processing Complete!**")
        
        # --- DOWNLOAD BUTTON ---
        if results:
            df_final = pd.DataFrame(results)
            # Ensure correct column order
            final_cols = ["Purchase From", "INVOICE", "GST NO", "DATE", "DESCRIPTION OF GOODS", 
                          "HSN CODE", "QTY", "GST", "PRICE (inc Tax)", "AMOUNT (inc Tax)"]
            df_final = df_final[[c for c in final_cols if c in df_final.columns]]

            # Convert to Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False)
            excel_data = output.getvalue()

            st.balloons()
            st.download_button(
                label="Download Excel Report",
                data=excel_data,
                file_name="Final_Expenses.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )