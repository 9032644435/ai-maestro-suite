import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, send_file
from gtts import gTTS
import uuid

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
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = f"""
        You are an expert Telugu songwriter. Your task is to create a song and return it as a JSON object.

        **Instructions:**
        1.  **Theme:** The song must incorporate these words: ` {', '.join(words)} `.
        2.  **Mood:** The mood of the song must be ` {mood} `.
        3.  **Language:** The lyrics must be in Telugu.
        4.  **Format:** You MUST return ONLY a single, clean, minified JSON object. Do not include any text, markdown, or any characters outside of the JSON object.

        **JSON Structure:**
        {{
          "title": "A creative and fitting title for the song in Telugu",
          "artist": "{singer}",
          "lyrics": "The full song lyrics in Telugu, with verses and chorus. Use '\\n' for line breaks."
        }}
        """

        response = model.generate_content(prompt)

        # The response should be a clean JSON string.
        import json
        try:
            # The model should return a clean JSON string, so we parse it directly.
            lyrics_json = json.loads(response.text)
            return jsonify(lyrics_json)
        except (json.JSONDecodeError, TypeError):
            # If the model response is not valid JSON, we log it and return an error.
            print(f"Error: Gemini API did not return valid JSON. Response:\n{response.text}")
            return jsonify({"error": "The AI model returned an invalid format. Please try again."}), 500

    except KeyError:
         return jsonify({"error": "GEMINI_API_KEY is not configured on the server."}), 500
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "Failed to generate lyrics from the AI model."}), 500


@app.route("/api/generate-audio", methods=["POST"])
def generate_audio():
    if not request.is_json:
        return jsonify({"error": "Invalid request: not JSON"}), 400

    data = request.get_json()
    lyrics = data.get("lyrics")

    if not lyrics:
        return jsonify({"error": "Missing lyrics"}), 400

    try:
        # Create a unique filename for the audio file
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join("static", "audio", filename)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Generate the audio file
        print(f"Generating audio for: {lyrics}")
        print(f"Saving to: {filepath}")
        tts = gTTS(text=lyrics, lang='te', slow=False)
        tts.save(filepath)
        print("Audio file saved.")

        return jsonify({"audio_url": f"/static/audio/{filename}", "download_url": f"/download-song/{filename}"})

    except Exception as e:
        print(f"An error occurred during audio generation: {e}")
        return jsonify({"error": "Failed to generate audio."}), 500

@app.route("/download-song/<filename>")
def download_song(filename):
    try:
        filepath = os.path.join("static", "audio", filename)
        return send_file(filepath, as_attachment=True)
    except FileNotFoundError:
        return "File not found.", 404

if __name__ == "__main__":
    # Use Gunicorn for production, but Flask's server for local dev.
    # The port is read from the PORT env var, which is common in cloud platforms.
    port = int(os.environ.get("PORT", 8081))
    app.run(host='0.0.0.0', port=port)