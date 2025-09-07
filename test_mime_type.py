import requests

def test_js_mime_type(url):
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        content_type = response.headers.get('Content-Type')
        print(f"URL: {url}")
        print(f"Content-Type: {content_type}")
        if 'application/javascript' in content_type:
            print("MIME type is correct: application/javascript")
            return True
        else:
            print(f"MIME type is INCORRECT. Expected 'application/javascript', got '{content_type}'")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return False

if __name__ == "__main__":
    # Replace with an actual URL to a JS file served by your Streamlit app via Nginx
    # You might need to run your docker-compose setup first to get the correct URL
    # For example, if your app is running on localhost:80, and Streamlit serves JS from /_stcore/
    # you might try a URL like: http://localhost:80/_stcore/static/js/main.js (adjust as needed)
    test_url = "https://youssef2106-ai-resume-parser.hf.space/static/js/index.CD8HuT3N.js"
    print(f"Attempting to test MIME type for: {test_url}")
    test_js_mime_type(test_url)