from google import genai

# --- CONFIGURATION ---
API_KEY = "Give your API key from google AI studio"

client = genai.Client(api_key=API_KEY)

print("--- SEARCHING FOR AVAILABLE MODELS ---\n")
try:
    # We just ask for the list and print the names directly
    for model in client.models.list():
        # The new library returns the name cleanly
        print(f"Found: {model.name}")

except Exception as e:
    print(f"\nError: {e}")

print("-" * 60)
print("TIP: Look for 'gemini-2.5-flash' or 'gemini-2.5-flash-lite' in the list above. They Usually work")