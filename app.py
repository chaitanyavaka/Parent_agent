from flask import Flask, render_template, request, jsonify, send_file
from groq import Groq
import os
from dotenv import load_dotenv
import pandas as pd
from werkzeug.utils import secure_filename
import time
import io
import shutil

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls'}

def clear_temp_folders():
    """Deletes and recreates the upload and output folders for a clean start."""
    print("--- Clearing temporary file folders ---")
    for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    print("--- Temporary folders cleared and recreated ---")

# Call the cleanup function on every startup
clear_temp_folders()

# Initialize Groq client
try:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env file")
    client = Groq(api_key=api_key)
except Exception as e:
    print(f"Error initializing Groq client: {e}")
    client = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_parent_company_info(company_name: str) -> dict:
    if not client:
        return { "error": "API client not initialized. Check your GROQ_API_KEY." }
    
    try:
        # --- IMPROVED PROMPT ---
        parent_prompt = f"""Identify the legal parent company of the business named "{company_name}".
        Respond with ONLY the official name of the parent company.
        If the company has no parent (it is the ultimate parent), respond with '{company_name}'."""
        
        parent_response = client.chat.completions.create(
            messages=[{"role": "user", "content": parent_prompt}],
            model="llama-3.1-8b-instant",
        )
        parent_company = parent_response.choices[0].message.content.strip()
        
        if parent_company.lower() == company_name.lower():
            parent_company = "No parent company"
        
        if parent_company == "No parent company":
            desc_prompt = f"Provide a brief 2-3 sentence description of {company_name}, including what industry it operates in and what it's known for."
        else:
            desc_prompt = f"Provide a brief 2-3 sentence description of how {parent_company} relates to {company_name}, including when the acquisition happened if applicable."
        
        desc_response = client.chat.completions.create(
            messages=[{"role": "user", "content": desc_prompt}],
            model="llama-3.1-8b-instant",
        )
        description = desc_response.choices[0].message.content.strip()
        
        return {
            "parent_company": parent_company,
            "description": description,
            "error": None
        }
    except Exception as e:
        return {
            "error": f"An API error occurred: {str(e)}",
            "parent_company": f"Error for {company_name}",
            "description": f"Error for {company_name}"
        }

def get_parent_company_only(company_name: str) -> str:
    if not client:
        return "Error: API client not initialized"

    # --- IMPROVED PROMPT ---
    parent_prompt = f"""Identify the legal parent company of the business named "{company_name}".
    Respond with ONLY the official name of the parent company.
    If the company has no parent (it is the ultimate parent), respond with 'No parent company'."""
    
    try:
        parent_response = client.chat.completions.create(
            messages=[{"role": "user", "content": parent_prompt}],
            model="llama-3.1-8b-instant",
        )
        parent_company = parent_response.choices[0].message.content.strip()
        
        if parent_company.lower() == company_name.lower():
            return "No parent company"
        else:
            return parent_company
            
    except Exception as e:
        return "API Error"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/lookup', methods=['POST'])
def lookup():
    data = request.get_json()
    company_name = data.get('company_name', '').strip()
    if not company_name:
        return jsonify({"error": "Please enter a company name"}), 400
    result = get_parent_company_info(company_name)
    if result.get('error'):
        return jsonify(result), 500
    return jsonify(result)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Please upload .xlsx or .xls"}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        df = pd.read_excel(filepath)
        if df.empty:
            return jsonify({"error": "The Excel file is empty"}), 400
            
        first_column_name = df.columns[0]
        companies = df[first_column_name].dropna().astype(str).tolist()
        
        if not companies:
            return jsonify({"error": f"No company names found in the first column ('{first_column_name}')"}), 400
            
        return jsonify({
            "success": True,
            "filename": filename,
            "total_companies": len(companies),
            "companies": companies[:5]
        })
    except Exception as e:
        return jsonify({"error": f"Error reading or saving file: {str(e)}"}), 500

@app.route('/process', methods=['POST'])
def process_file():
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({"error": "Filename not provided"}), 400
        
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found on server"}), 404
        
    try:
        df = pd.read_excel(filepath)
        first_column = df.columns[0]
        
        parent_companies = []
        for company in df[first_column].astype(str):
            if company.strip() and company.lower() != 'nan':
                parent = get_parent_company_only(company.strip())
                parent_companies.append(parent)
                time.sleep(0.5) 
            else:
                parent_companies.append("")

        df['Parent Company'] = parent_companies
        
        output_filename = f"processed_{filename}"
        output_filepath = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        df.to_excel(output_filepath, index=False, engine='openpyxl')
        
        return jsonify({
            "success": True,
            "output_filename": output_filename,
            "message": "File processed successfully"
        })
    except Exception as e:
        return jsonify({"error": f"An error occurred during processing: {str(e)}"}), 500

@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found for download"}), 404
    try:
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Could not download file: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)