import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, send_file
from gtts import gTTS
from pydub import AudioSegment
import uuid

app = Flask(__name__)

# Configure the Gemini API key
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
except KeyError:
    print("Error: GEMINI_API_KEY environment variable not set.")

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
        model = genai.GenerativeModel('gemini-2.5-flash')

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

        if not response.candidates:
            if response.prompt_feedback.block_reason:
                print(f"Lyrics generation blocked for safety reasons: {response.prompt_feedback.block_reason}")
                return jsonify({"error": "Content blocked by safety policy. Try different words."}), 400
            else:
                return jsonify({"error": "AI could not generate a valid song structure. Try simplifying the words."}), 500

        import json
        try:
            # Clean the response to remove markdown fences before parsing
            clean_text = response.text.strip().replace('```json', '').replace('```', '').strip()
            lyrics_json = json.loads(clean_text)
            return jsonify(lyrics_json)
        except (json.JSONDecodeError, TypeError):
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
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join("static", "audio", filename)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Generate the speech with an Indian English accent
        tts = gTTS(text=lyrics, lang='en', tld='co.in', slow=False)
        speech_filepath = os.path.join("static", "audio", f"speech_{filename}")
        tts.save(speech_filepath)

        # Load the generated speech and the background music
        speech = AudioSegment.from_mp3(speech_filepath)
        background_music = AudioSegment.from_mp3("static/music/music_loop.mp3")

        # Mix the two audio files
        # We'll make the background music quieter so the speech is audible
        final_audio = speech.overlay(background_music - 10)

        # Export the final audio
        final_audio.export(filepath, format="mp3")

        # Clean up the temporary speech file
        os.remove(speech_filepath)

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
    port = int(os.environ.get("PORT", 8081))
    app.run(host='0.0.0.0', port=port)