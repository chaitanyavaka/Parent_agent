from groq import Groq
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# --- Configuration ---
try:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env file or environment.")
    # Initialize the Groq client
    client = Groq(api_key=api_key)
except (KeyError, ValueError) as e:
    print(f" Error: {e}")
    print("Please make sure you have a .env file with 'GROQ_API_KEY=YOUR_KEY' in it.")
    exit()

def get_parent_company(company_name: str) -> str:
    """
    Finds the parent company of a given company using the Groq API.

    Args:
        company_name: The name of the company (e.g., "Instagram", "YouTube").

    Returns:
        A string containing the name of the parent company or an error message.
    """
    # The prompt still asks the model to return the company's own name if it has no parent.
    prompt = f"What is the parent company of {company_name}? Respond with only the name of the parent company. If it is the parent company itself or has no parent, respond with '{company_name}'."

    try:
        print(f" Looking up parent company for {company_name} ...")
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant", 
        )
        
        parent_company_from_api = chat_completion.choices[0].message.content.strip()
        
        # --- NEW LOGIC ADDED HERE ---
        # Check if the API returned the original company name.
        # We use .lower() to make the comparison case-insensitive.
        if parent_company_from_api.lower() == company_name.lower():
            return "No parent company"
        else:
            return parent_company_from_api
        
    except Exception as e:
        return f"An error occurred: {e}"

# --- Main Execution Loop ---
if __name__ == "__main__":
    print(" Parent Company Finder Agent (by Chaitanya)  is running.")
    print("Enter a company name, or type 'quit' or 'exit' to stop.")
    
    while True:
        user_input = input("\nEnter a company name: ")
        
        if user_input.lower() in ["quit", "exit"]:
            print("Goodbye!")
            break
            
        parent_company = get_parent_company(user_input)
        print(f" The parent company of {user_input} is: {parent_company}")