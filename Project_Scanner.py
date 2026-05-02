import cv2
from pyzbar.pyzbar import decode
import csv
import os
import numpy as np
from datetime import datetime
import winsound  # For beep sound effect on Windows

# ================= CONFIGURATION =================
# REPLACE THIS WITH YOUR PHONE'S IP (e.g., from IP Webcam app)
URL = 'http://192.0.0.4:8080/video' 
# =================================================

# Paths
BASE_DIR = r"C:\Users\pyush\OneDrive\Desktop\Database_30"
DB_PATH = os.path.join(BASE_DIR, "Master_Database.csv")
REPORT_PATH = os.path.join(BASE_DIR, "Final_Inventory_Report.csv")

def load_db():
    data = {}
    try:
        with open(DB_PATH, 'r') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                # Key: Code -> Value: {Name, Price, Genre}
                data[row[0]] = {"name": row[1], "price": row[2], "genre": row[3]}
        return data
    except:
        print("Error: Database not found. Run generator first.")
        return {}

def initialize_report():
    # We create specific columns for segregation as requested
    if not os.path.exists(REPORT_PATH):
        with open(REPORT_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            # THE CREATIVE COLUMN STRUCTURE
            writer.writerow([
                "Date", "Time", "Scanned Code", 
                "FOOD Items", "ELECTRONICS Items", "GROCERY Items", 
                "Price (INR)", "Status"
            ])

def save_entry(code, item):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    name = item['name']
    genre = item['genre']
    price = item['price']
    
    # Logic to put the name in the correct column
    food_col = name if genre == "Food" else "-"
    elec_col = name if genre == "Electronics" else "-"
    groc_col = name if genre == "Grocery" else "-"
    
    with open(REPORT_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            date_str, time_str, code,
            food_col, elec_col, groc_col,
            price, "Verified"
        ])

def run_project():
    print(f"Initializing System... Connecting to {URL}")
    
    # Try connecting to URL, fallback to Webcam (0) if failed for testing
    cap = cv2.VideoCapture(URL)
    if not cap.isOpened():
        print("WiFi Camera not found. Trying Laptop Webcam...")
        cap = cv2.VideoCapture(0)

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    db = load_db()
    initialize_report()
    session_scans = set()

    print("\n--- FINAL YEAR PROJECT: INTELLIGENT INVENTORY SYSTEM ---")
    print("Press 'q' to Finish and Generate Report.")

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # Resize for performance
        frame = cv2.resize(frame, (900, 600))
        
        # --- CREATIVE UI OVERLAY ---
        # Draw a semi-transparent header
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (900, 50), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        cv2.putText(frame, "INTELLIGENT MANAGEMENT SYSTEM - LIVE FEED", (20, 35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        decoded_objects = decode(frame)
        
        for obj in decoded_objects:
            code = obj.data.decode('utf-8')
            
            # Database Lookup
            if code in db:
                item = db[code]
                display_text = f"{item['name']} | Rs.{item['price']}"
                color = (0, 255, 0) # Green for authorized
                
                # If new scan, save and beep
                if code not in session_scans:
                    winsound.Beep(1000, 200) # Beep sound
                    save_entry(code, item)
                    session_scans.add(code)
                    print(f"[ACCEPTED] {item['genre']}: {item['name']}")
            else:
                display_text = "UNREGISTERED ITEM"
                color = (0, 0, 255) # Red for unauthorized

            # Draw Bounding Box
            pts = np.array(obj.polygon, np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, color, 3)
            
            # Draw Label Background
            rect = obj.rect
            cv2.rectangle(frame, (rect.left, rect.top - 30), (rect.left + 250, rect.top), color, -1)
            cv2.putText(frame, display_text, (rect.left + 5, rect.top - 8), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)

        cv2.imshow('Project View', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    
    # --- AUTO OPEN EXCEL ---
    print("Generating Report...")
    if os.path.exists(REPORT_PATH):
        os.startfile(REPORT_PATH)
    print("Done.")

if __name__ == "__main__":
    run_project()