import streamlit as st
import pandas as pd
import json
import time
import os
from io import BytesIO
from google import genai
from google.genai import types

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Smart Bill Extractor", page_icon="🧾", layout="wide")

# --- CSS STYLING (YOUR ORIGINAL GLASSMORPHISM) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        padding-top: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Glassmorphism Card Effect */
    .block-container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 2rem;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
    }
    
    /* Sidebar Glassmorphism */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: transparent;
    }
    
    /* Model Status Box */
    .model-status {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.3);
        margin: 1rem 0;
    }
    
    .model-active {
        color: #10b981;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    .model-failed {
        color: #ef4444;
        font-weight: 500;
        font-size: 0.85rem;
    }
    
    /* Title Styling */
    h1 {
        color: white;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    /* File Uploader */
    [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 2px dashed rgba(255, 255, 255, 0.4);
        padding: 1.5rem;
    }
    
    /* Dataframe Styling */
    [data-testid="stDataFrame"] {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #10b981 0%, #3b82f6 100%);
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: white;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.3);
    }
    
    /* Download Button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
        transition: all 0.3s ease;
    }
    
    .stDownloadButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.6);
    }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE / HISTORY FUNCTIONS ---
DB_FILE = "invoice_history.json"

def load_history():
    """Loads existing data from the local JSON file."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_history(new_data):
    """Appends new data to history and saves to file."""
    current_history = load_history()
    # Avoid duplicates based on Source File name
    existing_files = {item['Source File'] for item in current_history}
    
    unique_new_data = [d for d in new_data if d['Source File'] not in existing_files]
    
    updated_history = current_history + unique_new_data
    with open(DB_FILE, "w") as f:
        json.dump(updated_history, f, indent=4)
    return updated_history

def get_processed_filenames():
    """Returns a set of filenames that are already in the DB."""
    history = load_history()
    return {item['Source File'] for item in history}


# --- SESSION STATE ---
if 'model_status' not in st.session_state:
    st.session_state.model_status = {"current": None, "failed": [], "success": []}

if 'processing_state' not in st.session_state:
    st.session_state.processing_state = 'idle'


# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2921/2921222.png", width=80)
    st.title("⚙️ Settings")
    
    api_key = st.text_input("🔑 Google API Key", type="password", help="Paste your Gemini API Key here")
    
    st.divider()
    st.write("### 📂 Database Memory")
    history = load_history()
    st.info(f"💾 **{len(history)}** items saved in history.")
    
    if st.button("🗑️ Clear History"):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            st.rerun()

    st.divider()
    st.write("### 🤖 Model Status")
    
    if st.session_state.model_status["current"]:
        st.markdown(f"""
        <div class="model-status">
            <div class="model-active">✅ Currently Using:</div>
            <div class="model-name">
                {st.session_state.model_status["current"]}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("🔄 No model active yet")
    
    if st.session_state.model_status["failed"]:
        with st.expander("⚠️ Failed Models"):
            for model in st.session_state.model_status["failed"]:
                st.markdown(f'<div class="model-failed">❌ {model}</div>', unsafe_allow_html=True)
    
    st.divider()
    st.warning("⚠️ **Rate Limit:** ~1500 Bills/Day (Free Tier)")


# --- SMART AI LOGIC ---
# UPDATED MODEL LIST: Put 1.5-Flash first to solve quota issues
CANDIDATE_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-2.0-flash-exp",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash"
]

def get_working_model(client, file_bytes, mime_type, prompt):
    """Tries multiple models until one works."""
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
            
            # Update model status on success
            st.session_state.model_status["current"] = model_name
            if model_name not in st.session_state.model_status["success"]:
                st.session_state.model_status["success"].append(model_name)
            
            return json.loads(response.text), model_name
        except Exception as e:
            last_error = str(e)
            if model_name not in st.session_state.model_status["failed"]:
                st.session_state.model_status["failed"].append(model_name)
            
            if "429" in str(e): # Quota exceeded
                time.sleep(2)
                continue
            else:
                continue

    return None, last_error

def process_bill(file_bytes, mime_type, api_key):
    client = genai.Client(api_key=api_key)
    
    prompt = """
    Analyze this invoice image and extract data for an Excel sheet. 
    EXTRACT THESE FIELDS SPECIFICALLY:
    1. "seller_name": The name of the shop/seller
    2. "invoice_no": The Invoice Number
    3. "seller_gst": The Seller's GSTIN
    4. "bill_date": Date in YYYY-MM-DD format
    5. "items": A list of all items bought. For each item extract:
       - "description": Item Name
       - "hsn": HSN Code
       - "qty": Quantity (number only)
       - "gst_rate": The GST rate as a DECIMAL (e.g. if 18%, output 0.18)
       - "price_inc_tax": Unit Price including tax
       - "amount_inc_tax": Total Amount for this item including tax
    
    Return ONLY valid JSON.
    """
    
    return get_working_model(client, file_bytes, mime_type, prompt)


# --- MAIN APP UI ---
st.title("🧾 Smart Bill Extractor")
st.write("Upload your bills. **History is saved automatically**, so you don't need to re-process old files.")

uploaded_files = st.file_uploader(
    "📎 Drop your bills here", 
    type=["pdf", "png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

if uploaded_files:
    # --- SMART FILTERING LOGIC ---
    processed_filenames = get_processed_filenames()
    
    # Files that need API processing
    new_files_to_process = [f for f in uploaded_files if f.name not in processed_filenames]
    # Files that are already in DB
    existing_files = [f for f in uploaded_files if f.name in processed_filenames]
    
    st.markdown(f"""
        <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 10px; margin-bottom: 20px;">
            📄 <b>Total Files:</b> {len(uploaded_files)} &nbsp;&nbsp;|&nbsp;&nbsp; 
            🆕 <b>New to Process:</b> {len(new_files_to_process)} &nbsp;&nbsp;|&nbsp;&nbsp; 
            💾 <b>Loaded from Memory:</b> {len(existing_files)}
        </div>
    """, unsafe_allow_html=True)
    
    # --- 1. STATE MANAGEMENT BUTTONS ---
    button_config = {
        'idle': {'label': f'🚀 Start Processing ({len(new_files_to_process)} New Files)', 'color': '#ef4444', 'text_color': 'white'},
        'processing': {'label': '⏳ Processing...', 'color': '#3b82f6', 'text_color': 'white'},
        'complete': {'label': '✅ Processing Complete (Click to Reset)', 'color': '#10b981', 'text_color': 'white'},
        'partial': {'label': '⚠️ Processing Complete (Some Failed)', 'color': '#f59e0b', 'text_color': 'white'}
    }
    
    current_state = st.session_state.processing_state
    
    # If no new files, change button state to allow instant download
    if len(new_files_to_process) == 0 and current_state == 'idle':
        button_config['idle']['label'] = "📂 No New Files - Click to View Report"
        button_config['idle']['color'] = "#3b82f6"

    config = button_config[current_state]
    
    # CSS for button
    st.markdown(f"""
        <style>
        div.stButton > button {{
            background-color: {config['color']};
            color: {config['text_color']};
            font-weight: 600;
            border: none;
            border-radius: 10px;
            padding: 0.75rem 2rem;
            font-size: 1rem;
            width: 100%;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
        }}
        div.stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }}
        </style>
    """, unsafe_allow_html=True)
    
    # Logic to handle button click
    if st.button(config['label'], disabled=(current_state == 'processing')):
        if current_state == 'idle':
            # If there are new files, we need API key
            if len(new_files_to_process) > 0 and not api_key:
                st.error("❌ Please enter your API Key in the sidebar first!")
            else:
                st.session_state.processing_state = 'processing'
                st.rerun()
        elif current_state in ['complete', 'partial']:
            st.session_state.processing_state = 'idle'
            st.rerun()

    # --- 2. PROCESSING LOGIC ---
    if st.session_state.processing_state == 'processing':
        
        # If there are NO new files, just skip straight to complete
        if len(new_files_to_process) == 0:
            st.session_state.processing_state = 'complete'
            st.rerun()

        progress_bar = st.progress(0)
        status_text = st.empty()
        failed_count = 0
        current_run_results = []
        
        tab1, tab2 = st.tabs(["📊 Live Data", "📋 Processing Logs"])
        
        # Loop ONLY through NEW files
        for i, file in enumerate(new_files_to_process):
            status_text.write(f"🔄 Processing **{file.name}**...")
            
            bytes_data = file.getvalue()
            mime_type = file.type
            
            data, model_used = process_bill(bytes_data, mime_type, api_key)
            
            if data:
                with tab2:
                    st.success(f"✅ {file.name} processed using **{model_used}**")
                
                # Extract Data
                seller = data.get("seller_name", "").upper()
                inv = data.get("invoice_no", "")
                gst_no = data.get("seller_gst", "")
                date = data.get("bill_date", "")

                items = data.get("items", [])
                
                if not items:
                     current_run_results.append({
                        "Purchase From": seller, "INVOICE": inv, "GST NO": gst_no, "DATE": date,
                        "DESCRIPTION OF GOODS": "No items detected", "Source File": file.name
                    })
                else:
                    for item in items:
                        current_run_results.append({
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
                failed_count += 1
                with tab2:
                    st.error(f"❌ Failed: {file.name} - {model_used}")

            # Update Live Preview
            if current_run_results:
                df_live = pd.DataFrame(current_run_results)
                with tab1:
                    st.dataframe(df_live, use_container_width=True)

            progress_bar.progress((i + 1) / len(new_files_to_process))
            time.sleep(1) 

        status_text.write("🎉 **Processing Complete!**")
        
        # SAVE NEW RESULTS TO DB HISTORY
        if current_run_results:
            save_history(current_run_results)
        
        # Update State
        if failed_count == 0:
            st.session_state.processing_state = 'complete'
        else:
            st.session_state.processing_state = 'partial'
        
        st.rerun()

    # --- 3. RESULTS DISPLAY & DOWNLOAD ---
    if st.session_state.processing_state in ['complete', 'partial']:
        
        # Load Complete History
        full_history = load_history()
        
        # FILTER: Only show data for the files currently in the uploader
        # This combines "Old data" (for files processed yesterday) + "New data" (processed just now)
        current_filenames = [f.name for f in uploaded_files]
        final_data = [row for row in full_history if row['Source File'] in current_filenames]
        
        if final_data:
            st.balloons()
            
            df_final = pd.DataFrame(final_data)
            
            # Reorder columns
            desired_cols = ["Purchase From", "INVOICE", "GST NO", "DATE", "DESCRIPTION OF GOODS", 
                            "HSN CODE", "QTY", "GST", "PRICE (inc Tax)", "AMOUNT (inc Tax)", "Source File"]
            final_cols = [c for c in desired_cols if c in df_final.columns]
            df_final = df_final[final_cols]

            # Generate Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False)
            excel_data = output.getvalue()

            st.markdown("### ✅ Final Report (New + History)")
            st.dataframe(df_final, use_container_width=True)
            
            st.download_button(
                label="📥 Download Excel Report",
                data=excel_data,
                file_name="Final_Expenses.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
        else:
            st.warning("No data found for the uploaded files.")

else:
    # Reset state when user clears the file uploader
    st.session_state.processing_state = 'idle'
    st.session_state.results_data = []