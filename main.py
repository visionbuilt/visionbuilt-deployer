import os
import requests
import json
from flask import Flask, request, jsonify

# --- Environment Variables ---
NETLIFY_API_TOKEN = os.environ.get("NETLIFY_API_TOKEN", "")
NETLIFY_TEAM_ID = os.environ.get("NETLIFY_TEAM_ID", "")
SHARED_SECRET_KEY = os.environ.get("SHARED_SECRET_KEY", "")

# Initialize the Flask web application
app = Flask(__name__)

@app.get("/")
def index():
    return "<h1>Visionbuilt Deployer is running.</h1>"

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

    html_content = data.get("html")
    if not html_content:
        return jsonify({"status": "error", "message": "Missing 'html'"}), 400

    # 3. --- Call Netlify API ---
    try:
        api_url = f"https://api.netlify.com/api/v1/{NETLIFY_TEAM_ID}/sites"
        headers = {
            "Authorization": f"Bearer {NETLIFY_API_TOKEN}",
            "Content-Type": "application/json"
        }
        body = { "files": { "index.html": html_content } }

        response = requests.post(api_url, headers=headers, data=json.dumps(body), timeout=30)

        # --- NEW: STRICT ERROR CHECKING ---
        # If the HTTP status code is 400 or higher, it's an error.
        if response.status_code >= 400:
            error_message = f"Netlify returned an error (HTTP {response.status_code})"
            # Try to get more details from the response body
            try:
                error_details = response.json().get("message", response.text)
                error_message += f": {error_details}"
            except json.JSONDecodeError:
                error_message += f": {response.text}"
            
            print("ERROR:", error_message) # Log the specific error
            return jsonify({"status": "error", "message": error_message}), 500

        # If we reach here, the status code was successful (2xx)
        response_data = response.json()
        new_website_url = response_data.get("ssl_url") or response_data.get("url")

        if not new_website_url:
            print("Could not find URL. Full Netlify response:", response_data)
            return jsonify({"status": "error", "message": "Deployment succeeded but no URL was returned by Netlify."}), 500

        # 4. --- Return True Success to n8n ---
        return jsonify({
            "status": "success",
            "message": "Website deployed successfully.",
            "websiteUrl": new_website_url
        }), 201

    except Exception as e:
        # Catch any other unexpected errors
        print("UNEXPECTED ERROR:", str(e))
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)```

**Step 4: Upload to GitHub, Wait for Render, and Retest**
*   Save the new `main.py` and upload it to your GitHub repository.
*   Wait for Render to finish deploying the latest version.
*   Run the **Execute step** in n8n one last time.

This time, if there is an authentication problem, the new code is guaranteed to catch it and will return the *real* error message from Netlify.