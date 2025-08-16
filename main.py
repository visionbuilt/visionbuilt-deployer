import os
import requests
import json
from flask import Flask, request, jsonify

# --- Environment Variables (Set these in Render's dashboard) ---
# Your Netlify Personal Access Token you just created.
NETLIFY_API_TOKEN = os.environ.get("NETLIFY_API_TOKEN", "")
# Your Netlify Team ID (looks like 'your-team-name'). We will find this in a later step.
NETLIFY_TEAM_ID = os.environ.get("NETLIFY_TEAM_ID", "")
# A simple password to protect your API from public use.
SHARED_SECRET_KEY = os.environ.get("SHARED_SECRET_KEY", "")

# Initialize the Flask web application
app = Flask(__name__)

# This endpoint is just for testing if the API is running
@app.get("/")
def index():
    return "<h1>Visionbuilt Deployer is running.</h1>"

# This is the main endpoint that n8n will call
@app.post("/api/create-website")
def create_website():
    # 1. --- Security Check ---
    # Check if the secret key from n8n matches the one set in Render
    auth_header = request.headers.get("X-Deploy-Key")
    if not SHARED_SECRET_KEY or auth_header != SHARED_SECRET_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    # 2. --- Get Data from n8n ---
    # Get the JSON data sent by the n8n workflow
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON data"}), 400

    customer_id = data.get("customerId")
    html_content = data.get("html")

    if not customer_id or not html_content:
        return jsonify({"status": "error", "message": "Missing 'customerId' or 'html'"}), 400

    # 3. --- Prepare the File for Netlify ---
    # Netlify's API needs the file content and the filename
    files_payload = {
        "index.html": html_content
    }

    # 4. --- Create a New Site on Netlify ---
    # This sends the request to the Netlify API to create a new site
    try:
        api_url = f"https://api.netlify.com/api/v1/{NETLIFY_TEAM_ID}/sites"
        headers = {
            "Authorization": f"Bearer {NETLIFY_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # In the body, we tell Netlify to deploy the files we prepared
        body = {
            "files": files_payload
        }

        response = requests.post(api_url, headers=headers, data=json.dumps(body), timeout=30)
        
        # Raise an error if the request was not successful
        response.raise_for_status() 
        
        response_data = response.json()
        new_website_url = response_data.get("ssl_url") # or 'url'

        if not new_website_url:
            return jsonify({"status": "error", "message": "Deployment succeeded but no URL was returned."}), 500

        # 5. --- Return Success to n8n ---
        # Send back the new live URL to the n8n workflow
        return jsonify({
            "status": "success",
            "message": "Website deployed successfully.",
            "websiteUrl": new_website_url
        }), 201

    except requests.exceptions.RequestException as e:
        # If anything goes wrong with the Netlify API call, return an error
        error_message = f"Failed to deploy to Netlify: {e}"
        if e.response is not None:
            error_message += f" | Details: {e.response.text}"
        
        return jsonify({"status": "error", "message": error_message}), 500

# This part allows Render to run the Flask app
if __name__ == "__main__":
    # Render provides the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)