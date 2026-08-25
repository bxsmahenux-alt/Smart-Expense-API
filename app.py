from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import os
import json
from pythainlp import word_tokenize
import __main__ 

# --- 1. แก้ปัญหา AI หาฟังก์ชันตัดคำไม่เจอตอนอยู่บนเซิร์ฟเวอร์ ---
def thai_tokenizer(text):
    return word_tokenize(text, engine='newmm')
__main__.thai_tokenizer = thai_tokenizer 

# --- 2. โหลดสมองกล AI ---
try:
    model = joblib.load('expense_model.pkl')
    print("✅ โหลดโมเดล expense_model.pkl สำเร็จ")
except Exception as e:
    print(f"❌ โหลดโมเดลไม่สำเร็จ: {e}")

# --- 3. ฟังก์ชันล้วงตู้เซฟและเชื่อมต่อตาราง ---
def connect_to_sheets():
    try:
        secret_creds = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
        if not secret_creds:
            return None
        
        creds_dict = json.loads(secret_creds)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # ⚠️ ชื่อไฟล์ตาราง (ต้องตรงกับชื่อไฟล์ Google Sheets ในขั้นตอนที่ 2)
        sheet = client.open("บัญชีรายจ่าย").sheet1
        return sheet
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการเชื่อมต่อ Sheets: {e}")
        return None

# --- 4. สร้างระบบ API เปิดรับข้อมูล ---
app = Flask(__name__)
CORS(app) 

@app.route('/add_expense', methods=['POST'])
def add_expense():
    data = request.json
    expense_text = data.get('text', '')
    
    # สกัดตัวเลข
    numbers = re.findall(r'\d+', expense_text)
    amount = int(numbers[0]) if numbers else 0
    
    # ให้ AI ทายหมวดหมู่ (พร้อมระบบแจ้งเตือน Error)
    try:
        predicted_category = model.predict([expense_text])[0]
    except Exception as e:
        predicted_category = f"เกิด Error: {str(e)}"
        
    # บันทึกลงตาราง
    sheet = connect_to_sheets()
    if sheet:
        try:
            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d")
            sheet.append_row([date_str, expense_text, amount, predicted_category])
            save_status = "บันทึกสำเร็จ (Render)"
        except Exception as e:
            save_status = f"บันทึก Sheets ไม่สำเร็จ: {str(e)}"
    else:
        save_status = "เชื่อมต่อตู้เซฟ Secrets ไม่สำเร็จ"
        
    # ส่งผลลัพธ์กลับไปที่หน้าเว็บ
    result = {
        "status": "success",
        "original_text": expense_text,
        "amount": amount,
        "category": predicted_category,
        "sheet_status": save_status
    }
    return jsonify(result)

# จุดสตาร์ทเครื่อง
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)