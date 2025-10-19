import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Configure the Gemini API key
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
except KeyError:
    print("Error: GEMINI_API_KEY environment variable not set.")
    # You might want to exit or handle this more gracefully
    # For now, we'll let it raise an error if the API is used.

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/generate-lyrics", methods=["POST"])
def generate_lyrics():
    if not request.is_json:
        return jsonify({"error": "Invalid request: not JSON"}), 400

    data = request.get_json()
    words = data.get("words")
    mood = data.get("mood")
    singer = data.get("singer")

    if not all([words, mood, singer]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        model = genai.GenerativeModel('gemini-pro')

        prompt = f"""
        You are an expert Telugu songwriter. Your task is to create a song based on the user's input.
        The song should be in Telugu, with a mix of verses and a chorus.
        The theme of the song must incorporate the following words: {', '.join(words)}.
        The mood of the song should be '{mood}'.
        The singer's voice is for a '{singer}'.

        Generate the lyrics and provide the output in a clean, structured JSON format like this example:
        {{
          "lyrics": {{
            "pallavi": [
              "Line 1 of the chorus in Telugu",
              "Line 2 of the chorus in Telugu"
            ],
            "charanam1": [
              "Line 1 of the first verse in Telugu",
              "Line 2 of the first verse in Telugu"
            ],
            "charanam2": [
              "Line 1 of the second verse in Telugu",
              "Line 2 of the second verse in Telugu"
            ]
          }}
        }}

        Do not include any text or formatting outside of the JSON structure.
        """

        response = model.generate_content(prompt)

        # The response text might be wrapped in markdown ```json ... ```, so we clean it.
        clean_response_text = response.text.strip().replace('```json', '').replace('```', '').strip()

        # The cleaned text should be valid JSON.
        import json
        lyrics_json = json.loads(clean_response_text)

        return jsonify(lyrics_json)

    except KeyError:
         return jsonify({"error": "GEMINI_API_KEY is not configured on the server."}), 500
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "Failed to generate lyrics from the AI model."}), 500


if __name__ == "__main__":
    # Use Gunicorn for production, but Flask's server for local dev.
    # The port is read from the PORT env var, which is common in cloud platforms.
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)