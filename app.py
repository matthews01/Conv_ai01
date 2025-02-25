from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
from werkzeug.utils import secure_filename

app = Flask(__name__)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'curious-idea-452009-p9-711e548edb07.json'

# Configuration
UPLOAD_FOLDER = 'static/recordings'
GENERATED_AUDIO_FOLDER = 'static/audio'
ALLOWED_EXTENSIONS = {'wav'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['GENERATED_AUDIO_FOLDER'] = GENERATED_AUDIO_FOLDER

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_AUDIO_FOLDER, exist_ok=True)

# Check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Upload audio and convert to text
@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Convert speech to text using Google Speech-to-Text API
        client = speech.SpeechClient()
        with open(file_path, 'rb') as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code='en-US'
        )

        response = client.recognize(config=config, audio=audio)
        transcript = ''
        for result in response.results:
            transcript += result.alternatives[0].transcript

        # Save transcript to a file
        transcript_filename = filename.replace('.wav', '.txt')
        transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], transcript_filename)
        with open(transcript_path, 'w') as transcript_file:
            transcript_file.write(transcript)

        return render_template('index.html', transcript=transcript, audio_file=None)
    return redirect(request.url)

# Convert text to audio
@app.route('/text-to-audio', methods=['POST'])
def text_to_audio():
    text = request.form['text']
    if not text:
        return redirect(request.url)

    # Generate audio using Google Text-to-Speech API
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code='en-US',
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    # Save audio to a file
    audio_filename = 'output.mp3'
    audio_path = os.path.join(app.config['GENERATED_AUDIO_FOLDER'], audio_filename)
    with open(audio_path, 'wb') as audio_file:
        audio_file.write(response.audio_content)

    return render_template('index.html', transcript=None, audio_file=audio_filename)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)