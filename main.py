from flask import Flask, render_template, request, jsonify
import speech_recognition as sr
from deep_translator import GoogleTranslator
import sqlite3
from datetime import datetime
from collections import Counter
import re
import nltk
from nltk.util import ngrams

app = Flask(__name__)
import nltk
nltk.download('punkt')
# Database setup
conn = sqlite3.connect('transcriptions.db', check_same_thread=False)
c = conn.cursor()

# Create table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS transcriptions
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              original_text TEXT,
              translated_text TEXT,
              timestamp DATETIME)''')
conn.commit()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/transcribe_and_translate', methods=['POST'])
def transcribe_and_translate():
    user_id = 1  # In a real app, you'd get this from user authentication
    text = request.form['text']
    source_lang = request.form['source_lang']
    
    recognizer = sr.Recognizer()
    
    # If text is empty, try to recognize speech
    if not text:
        with sr.Microphone() as source:
            print("Say something!")
            audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio, language=source_lang)
            print(f"Google Speech Recognition thinks you said: {text}")
        except sr.UnknownValueError:
            return jsonify({'error': "Google Speech Recognition could not understand audio"})
        except sr.RequestError as e:
            return jsonify({'error': f"Could not request results from Google Speech Recognition service; {e}"})
    
    translator = GoogleTranslator(source=source_lang, target='en')
    
    try:
        translated_text = translator.translate(text)
        
        c.execute("INSERT INTO transcriptions (user_id, original_text, translated_text, timestamp) VALUES (?, ?, ?, ?)",
                  (user_id, text, translated_text, datetime.now()))
        conn.commit()
        
        return jsonify({'original': text, 'translated': translated_text})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/history')
def history():
    user_id = 1  # In a real app, you'd get this from user authentication
    c.execute("SELECT * FROM transcriptions WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    history = c.fetchall()
    return render_template('history.html', history=history)

@app.route('/frequencies')
def frequencies():
    user_id = 1  # In a real app, you'd get this from user authentication
    c.execute("SELECT translated_text FROM transcriptions WHERE user_id = ?", (user_id,))
    user_texts = c.fetchall()
    user_text = ' '.join([text[0] for text in user_texts])
    user_freq = Counter(re.findall(r'\w+', user_text.lower()))
    
    c.execute("SELECT translated_text FROM transcriptions")
    all_texts = c.fetchall()
    all_text = ' '.join([text[0] for text in all_texts])
    all_freq = Counter(re.findall(r'\w+', all_text.lower()))
    
    words = set(list(user_freq.keys())[:10] + list(all_freq.keys())[:10])
    freq_data = [[word, user_freq.get(word, 0), all_freq.get(word, 0)] for word in words]
    freq_data.sort(key=lambda x: x[1], reverse=True)
    
    return render_template('frequencies.html', freq_data=freq_data)

@app.route('/phrases')
def phrases():
    user_id = 1  # In a real app, you'd get this from user authentication
    c.execute("SELECT translated_text FROM transcriptions WHERE user_id = ?", (user_id,))
    user_texts = c.fetchall()
    user_text = ' '.join([text[0] for text in user_texts])
    
    tokens = nltk.word_tokenize(user_text.lower())
    
    phrases = []
    for n in range(2, 5):
        phrases.extend([' '.join(gram) for gram in ngrams(tokens, n)])
    
    phrase_freq = Counter(phrases)
    top_phrases = phrase_freq.most_common(3)
    
    return render_template('phrases.html', top_phrases=top_phrases)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
