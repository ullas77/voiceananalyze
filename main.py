import os
import re
from flask import Flask, render_template
from collections import Counter
import logging
import psycopg2

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///your_local_db.sqlite')

def get_db_connection():
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def simple_tokenize(text):
    # This is a very basic tokenizer. It splits on whitespace and removes punctuation.
    return re.findall(r'\w+', text.lower())

def generate_ngrams(tokens, n):
    return [' '.join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

@app.route('/phrases')
def phrases():
    try:
        user_id = 1  # In a real app, you'd get this from user authentication
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT translated_text FROM transcriptions WHERE user_id = %s", (user_id,))
            user_texts = cur.fetchall()
        
        if not user_texts:
            return render_template('phrases.html', top_phrases=[], error="No texts found for this user")
        
        user_text = ' '.join([text[0] for text in user_texts])
        
        tokens = simple_tokenize(user_text)
        
        phrases = []
        for n in range(2, 5):
            phrases.extend(generate_ngrams(tokens, n))
        
        phrase_freq = Counter(phrases)
        top_phrases = phrase_freq.most_common(3)
        
        return render_template('phrases.html', top_phrases=top_phrases)
    
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}", exc_info=True)
        return render_template('error.html', error=str(e)), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
