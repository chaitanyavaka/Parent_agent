from flask import Flask, render_template, request, jsonify
from groq import Groq
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize Groq client
try:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env file")
    client = Groq(api_key=api_key)
except Exception as e:
    print(f"Error initializing Groq client: {e}")
    client = None

def get_parent_company_info(company_name: str) -> dict:
    """
    Finds the parent company and description using Groq API.
    
    Returns:
        dict: Contains 'parent_company' and 'description'
    """
    if not client:
        return {
            "error": "API client not initialized. Check your GROQ_API_KEY.",
            "parent_company": None,
            "description": None
        }
    
    # First prompt: Get parent company
    parent_prompt = f"""What is the parent company of {company_name}? 
    Respond with ONLY the parent company name, nothing else. 
    If {company_name} has no parent company or is itself the parent, respond with 'No parent company'."""
    
    try:
        # Get parent company
        parent_response = client.chat.completions.create(
            messages=[{"role": "user", "content": parent_prompt}],
            model="llama-3.1-8b-instant",
        )
        parent_company = parent_response.choices[0].message.content.strip()
        
        # Check if it returned the same company name
        if parent_company.lower() == company_name.lower():
            parent_company = "No parent company"
        
        # Second prompt: Get description
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
            "error": f"An error occurred: {str(e)}",
            "parent_company": None,
            "description": None
        }

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

if __name__ == '__main__':
    app.run(debug=True, port=5000)