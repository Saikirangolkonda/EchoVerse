import os
import re
from flask import Flask, render_template, request, send_file, url_for
import pyttsx3
from groq import Groq
from pydub import AudioSegment

app = Flask(__name__)

# Directory for storing audio files
UPLOAD_FOLDER = os.path.join('static', 'audio')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# API key for Groq
api_key = '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'
client = Groq(api_key=api_key)

# Initialize pyttsx3 TTS engine
engine = pyttsx3.init()

# Configure voices for pyttsx3
voices = engine.getProperty('voices')


def set_voice(voice_type):
    """
    Set voice for pyttsx3 based on speaker type.
    """
    if voice_type == "podcaster":
        engine.setProperty('voice', voices[0].id)  # Male voice
        engine.setProperty('rate', 150)  # Adjust speed
    elif voice_type == "guest":
        engine.setProperty('voice', voices[1].id if len(voices) > 1 else voices[0].id)  # Female voice
        engine.setProperty('rate', 140)  # Adjust speed


def generate_podcast_conversation(topic, podcaster_name, guest_name):
    """
    Generate a podcast conversation script using Groq.
    """
    llm = client.chat.completions.create(
        messages=[
            {"role": "system",
             "content": f"Generate an engaging and interactive podcast conversation between Podcaster {podcaster_name} and Guest {guest_name} on '{topic}'. Use distinct tones and a friendly conversational style with 20-30 exchanges."},
            {"role": "user",
             "content": f"Let's start a podcast about {topic}. Podcaster is {podcaster_name}, and the guest is {guest_name}."}
        ],
        model="llama-3.1-8b-instant",
    )
    return llm.choices[0].message.content


def text_to_speech(text, output_file, voice_type):
    """
    Convert text to speech and save as an audio file.
    """
    set_voice(voice_type)
    engine.save_to_file(text, output_file)
    engine.runAndWait()


def combine_audio_alternating(script, podcaster_name, guest_name, output_file):
    """
    Combine audio segments alternately based on the script dialogue.
    """
    turns = script.split("\n")
    combined_audio = AudioSegment.silent(duration=0)

    for turn in turns:
        if turn.startswith(podcaster_name):
            podcaster_text = turn[len(podcaster_name) + 1:].strip()
            if podcaster_text:
                temp_file = os.path.join(UPLOAD_FOLDER, "temp_podcaster.mp3")
                text_to_speech(podcaster_text, temp_file, "podcaster")
                combined_audio += AudioSegment.from_file(temp_file)
        elif turn.startswith(guest_name):
            guest_text = turn[len(guest_name) + 1:].strip()
            if guest_text:
                temp_file = os.path.join(UPLOAD_FOLDER, "temp_guest.mp3")
                text_to_speech(guest_text, temp_file, "guest")
                combined_audio += AudioSegment.from_file(temp_file)

    # Export combined audio
    combined_audio.export(output_file, format="mp3")
    if not os.path.exists(output_file):
        raise Exception(f"Audio file {output_file} was not created!")


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/generate', methods=['GET', 'POST'])
def generate():
    if request.method == 'POST':
        topic = request.form['topic']
        podcaster_name = request.form['podcaster_name']
        guest_name = request.form['guest_name']

        if not topic:
            return render_template('generate.html', error="Please provide a topic.")

        # Generate podcast script
        podcast_script = generate_podcast_conversation(topic, podcaster_name, guest_name)

        # Combine audio based on dialogue
        final_audio_path = os.path.join(UPLOAD_FOLDER, "final_podcast.mp3")
        try:
            combine_audio_alternating(podcast_script, podcaster_name, guest_name, final_audio_path)
        except Exception as e:
            return render_template('generate.html', error=f"Error creating audio: {str(e)}")

        # Generate relative URL for the audio file
        audio_url = url_for('static', filename="audio/final_podcast.mp3")

        return render_template('result.html',
                               podcast_script=podcast_script,
                               audio_file=audio_url)

    return render_template('generate.html')


@app.route('/download/<filename>')
def download_file(filename):
    """
    Endpoint to download the generated audio file.
    """
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found", 404


if __name__ == "__main__":
    app.run(debug=True)
