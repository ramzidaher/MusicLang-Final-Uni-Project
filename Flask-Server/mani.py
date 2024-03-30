from flask import Flask, request, render_template_string
from langdetect import detect_langs, DetectorFactory
from collections import defaultdict
import spacy

# Load spaCy model for sentence segmentation
nlp = spacy.load("en_core_web_sm")

app = Flask(__name__)
DetectorFactory.seed = 0

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Language Detector</title>
</head>
<body>
    <h1>Language Detector</h1>
    <form action="/" method="post">
        <label for="lyrics">Enter Lyrics:</label><br>
        <textarea id="lyrics" name="lyrics" rows="10" cols="50"></textarea><br>
        <input type="submit" value="Detect Languages">
    </form>
    {% if languages %}
        <h2>Detected Languages:</h2>
        <ul>
            {% for lang, conf in languages %}
            <li>{{ lang }}: {{ conf }}%</li>
            {% endfor %}
        </ul>
    {% endif %}
</body>
</html>
"""

def refined_detect_languages(text, confidence_threshold=0.05):
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]
    segment_confidences = defaultdict(list)

    for sentence in sentences:
        detections = detect_langs(sentence)
        for detection in detections:
            lang, confidence = str(detection).split(':')
            segment_confidences[lang].append(float(confidence))
    
    # Calculate average confidence per language, emphasizing minority languages
    language_confidence = {}
    for lang, confidences in segment_confidences.items():
        # This example simply averages confidence scores; consider more complex weighting
        language_confidence[lang] = sum(confidences) / len(confidences)
    
    # Filter by confidence threshold
    filtered_languages = {lang: conf for lang, conf in language_confidence.items() if conf >= confidence_threshold}
    
    return sorted(filtered_languages.items(), key=lambda x: x[1], reverse=True)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        lyrics = request.form['lyrics']
        languages = refined_detect_languages(lyrics)
        return render_template_string(HTML_TEMPLATE, languages=languages)
    else:
        return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    app.run(debug=True)