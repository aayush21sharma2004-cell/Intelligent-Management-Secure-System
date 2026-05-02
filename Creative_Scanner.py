import cv2
import numpy as np
import mss
from pyzbar.pyzbar import decode
import csv
import os
import time
import subprocess
import pygetwindow as gw
from datetime import datetime
import winsound
import ctypes

# ==========================================
#   NABHYAN PRO: HD COMMAND CENTER
# ==========================================

SCRCPY_PATH = r"C:\Users\pyush\Downloads\scrcpy-win64-v3.3.4\scrcpy-win64-v3.3.4\scrcpy.exe"
BASE_DIR = r"C:\Users\pyush\OneDrive\Desktop\Database_30"
DB_PATH = os.path.join(BASE_DIR, "Master_Database.csv")
REPORT_PATH = os.path.join(BASE_DIR, "Final_Inventory_Report.csv")

# 1. HD RESOLUTION SETTINGS (1920x1080)
SCREEN_W = 1920
SCREEN_H = 1080

# 2. LEFT SIDE (Raw Drone Feed)
LEFT_W = 960  # Exactly half screen
VIDEO_H = 720 # HD height
LIST_H = SCREEN_H - VIDEO_H # Remaining bottom space (360px)

# 3. RIGHT SIDE (AI Intelligence Feed)
RIGHT_W = 960

# 4. CAPTURE ZONE (Input)
# We crop the top 30px to remove the Scrcpy white title bar for a clean look
CAPTURE_ZONE = {"top": 30, "left": 0, "width": LEFT_W, "height": VIDEO_H}

# GLOBAL DATA
scan_list = [] 
session_scans = set()

def minimize_console():
    """ Hides the black CMD window instantly """
    try:
        whnd = ctypes.windll.kernel32.GetConsoleWindow()
        if whnd != 0:
            ctypes.windll.user32.ShowWindow(whnd, 6) # 6 = SW_MINIMIZE
    except:
        pass

def launch_scrcpy_source():
    """ Launches Scrcpy and positions it perfectly on the Left """
    if not gw.getWindowsWithTitle('NABHYAN DRONE FEED'):
        try:
            # We open it slightly larger (1000px) so we can crop the borders
            subprocess.Popen(
                [SCRCPY_PATH, "--window-title", "NABHYAN DRONE FEED", 
                 "--max-size", "1024", "--window-x", "0", "--window-y", "0"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            time.sleep(2)
        except:
            pass

    # Force Move to Top-Left
    try:
        windows = gw.getWindowsWithTitle('NABHYAN DRONE FEED')
        if windows:
            win = windows[0]
            if win.isMinimized: win.restore()
            win.moveTo(0, 0)       
            # Resize slightly larger than 960 to hide scrollbars
            win.resizeTo(LEFT_W + 16, VIDEO_H + 40)
    except:
        pass

def close_system():
    print("Shutting down...")
    cv2.destroyAllWindows()
    # Force kill Scrcpy
    subprocess.run(["taskkill", "/F", "/IM", "scrcpy.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Open Report
    if os.path.exists(REPORT_PATH):
        try:
            os.startfile(REPORT_PATH)
        except:
            pass

def load_database():
    data = {}
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, 'r') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 2:
                        data[row[0]] = {"name": row[1], "price": row[2] if len(row) > 2 else "N/A"}
        except:
            pass
    return data

def save_to_report(code, name, price, status):
    try:
        file_exists = os.path.exists(REPORT_PATH)
        with open(REPORT_PATH, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Barcode", "Product Name", "Price", "Status"])
            now = datetime.now().strftime("%H:%M:%S")
            writer.writerow([now, code, name, price, status])
    except:
        pass

def create_data_panel():
    """ Creates the Bottom-Left Inventory List """
    panel = np.zeros((LIST_H, LEFT_W, 3), dtype=np.uint8)
    
    # Header
    cv2.rectangle(panel, (0, 0), (LEFT_W, 50), (30, 30, 30), -1)
    cv2.putText(panel, "LIVE INVENTORY TRACKER", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    
    # Columns
    cv2.putText(panel, "TIME", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 2)
    cv2.putText(panel, "PRODUCT", (200, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 2)
    cv2.putText(panel, "STATUS", (750, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 2)
    cv2.line(panel, (0, 95), (LEFT_W, 95), (100, 100, 100), 1)
    
    # Data Rows
    y = 140
    for item in reversed(scan_list[-4:]): # Show last 4 items
        color = (0, 255, 0) if item['status'] == "VERIFIED" else (0, 0, 255)
        
        cv2.putText(panel, item['time'], (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        cv2.putText(panel, item['name'][:25], (200, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(panel, item['status'], (750, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        y += 50
        
    return panel

def start_system():
    minimize_console()
    launch_scrcpy_source()
    db = load_database()
    sct = mss.mss()
    
    print(">>> SYSTEM ONLINE <<<")
    
    # 1. AI INTELLIGENCE WINDOW (Top Right - Full Height)
    cv2.namedWindow('AI TARGET FEED', cv2.WINDOW_NORMAL)
    # Remove borders for seamless look
    cv2.setWindowProperty('AI TARGET FEED', cv2.WND_PROP_TOPMOST, 1) 
    cv2.resizeWindow('AI TARGET FEED', RIGHT_W, SCREEN_H)
    cv2.moveWindow('AI TARGET FEED', LEFT_W, 0)
    
    # 2. DATA WINDOW (Bottom Left)
    cv2.namedWindow('DATA LOG', cv2.WINDOW_NORMAL)
    cv2.setWindowProperty('DATA LOG', cv2.WND_PROP_TOPMOST, 1)
    cv2.resizeWindow('DATA LOG', LEFT_W, LIST_H)
    cv2.moveWindow('DATA LOG', 0, VIDEO_H) 

    while True:
        try:
            # 1. Capture the Scrcpy Window
            screenshot = sct.grab(CAPTURE_ZONE)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            # 2. Prepare AI Feed (Scale to fit right side)
            ai_frame = frame.copy()
            ai_frame = cv2.resize(ai_frame, (RIGHT_W, SCREEN_H))
            
            # 3. Header Overlay
            cv2.rectangle(ai_frame, (0,0), (RIGHT_W, 70), (0,0,0), -1)
            cv2.putText(ai_frame, "AI VISION INTELLIGENCE | ACTIVE", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

            # 4. Scanning Logic
            decoded = decode(frame)

            for obj in decoded:
                code = obj.data.decode('utf-8')
                
                # --- INTELLIGENCE LOGIC ---
                if code in db:
                    # DATABASE MATCH
                    item = db[code]
                    color = (0, 255, 0) # Green
                    status = "VERIFIED"
                    name = item['name']
                    
                    if code not in session_scans:
                        winsound.Beep(1200, 150)
                        now_time = datetime.now().strftime("%H:%M:%S")
                        scan_list.append({"name": name, "price": item['price'], "time": now_time, "status": "VERIFIED"})
                        save_to_report(code, name, item['price'], "VERIFIED")
                        session_scans.add(code)
                else:
                    # UNKNOWN THREAT
                    color = (0, 0, 255) # Red
                    status = "INVALID / UNKNOWN"
                    name = "UNREGISTERED OBJECT"
                
                # --- DRAWING THE LIVE TRACKING BOXES ---
                # Calculate scale factor (Input Size -> Output Size)
                scale_x = RIGHT_W / CAPTURE_ZONE["width"]
                scale_y = SCREEN_H / CAPTURE_ZONE["height"]
                
                # Map polygon points
                pts = np.array(obj.polygon, np.int32)
                pts[:, 0] = pts[:, 0] * scale_x
                pts[:, 1] = pts[:, 1] * scale_y
                pts = pts.reshape((-1, 1, 2))
                
                # Draw Box
                cv2.polylines(ai_frame, [pts], True, color, 8)
                
                # Draw Label
                x = int(obj.rect.left * scale_x)
                y = int(obj.rect.top * scale_y)
                
                # Label Background
                cv2.rectangle(ai_frame, (x, y-50), (x+500, y), color, -1)
                cv2.putText(ai_frame, f"{status}: {name}", (x + 10, y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            # 5. Display
            cv2.imshow('AI TARGET FEED', ai_frame)
            
            data_panel = create_data_panel()
            cv2.imshow('DATA LOG', data_panel)

            # 6. Check for Quit
            # We check both 'q' key AND if the window 'X' button was pressed
            if (cv2.waitKey(1) & 0xFF == ord('q')) or (cv2.getWindowProperty('AI TARGET FEED', cv2.WND_PROP_VISIBLE) < 1):
                break
        except Exception as e:
            print(f"Error loop: {e}")
            break

    close_system()

if __name__ == "__main__":
    start_system()