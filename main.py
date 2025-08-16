# This is the new function. Delete the old one and paste this in its place.
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
        response.raise_for_status() 
        
        response_data = response.json()
        
        # --- IMPROVEMENT: Check for multiple possible URL keys ---
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
```3.  Save the `main.py` file.