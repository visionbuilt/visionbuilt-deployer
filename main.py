import os
import requests
import json
from flask import Flask, request, jsonify

# --- Environment Variables (Set these in Render's dashboard) ---
NETLIFY_API_TOKEN = os.environ.get("NETLIFY_API_TOKEN", "")
NETLIFY_TEAM_ID = os.environ.get("NETLIFY_TEAM_ID", "")
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
    auth_header = request.headers.get("X-Deploy-Key")
    if not SHARED_SECRET_KEY or auth_header != SHARED_SECRET_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    # 2. --- Get Data from n8n ---
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON data"}), 400

    customer_id = data.get("customerId")
    html_content = data.get("html")

    if not customer_id or not html_content:
        return jsonify({"status": "error", "message": "Missing 'customerId' or 'html'"}), 400

    # 3. --- Prepare the File for Netlify ---
    files_payload = {
        "index.html": html_content
    }

    # 4. --- Create a New Site on Netlify ---
    try:
        api_url = f"https://api.netlify.com/api/v1/{NETLIFY_TEAM_ID}/sites"
        headers = {
            "Authorization": f"Bearer {NETLIFY_API_TOKEN}",
            "Content-Type": "application/json"
        }
        body = { "files": files_payload }

        response = requests.post(api_url, headers=headers, data=json.dumps(body), timeout=30)
        
        # We will check the response later to decide if it was a real success
        response_data = response.json()

        # Check for an error message inside a successful response
        if response.status_code >= 400 or response_data.get("error"):
             print("Netlify returned an error:", response_data)
             return jsonify({"status": "error", "message": f"Netlify returned an error: {response_data.get('message', 'Unknown error')}"}), 500

        # IMPROVEMENT: Check for multiple possible URL keys
        new_website_url = response_data.get("ssl_url") or response_data.get("url") or response_data.get("deploy_ssl_url")

        if not new_website_url:
            # For debugging, we can log the response to see what keys are available
            print("Could not find URL. Full Netlify response:", response_data)
            return jsonify({"status": "error", "message": "Deployment succeeded but no URL was returned by Netlify."}), 500

        # 5. --- Return Success to n8n ---
        return jsonify({
            "status": "success",
            "message": "Website deployed successfully.",
            "websiteUrl": new_website_url
        }), 201

    except requests.exceptions.RequestException as e:
        error_message = f"Failed to deploy to Netlify: {e}"
        if e.response is not None:
            error_message += f" | Details: {e.response.text}"
        
        return jsonify({"status": "error", "message": error_message}), 500

# This part allows Render to run the Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)