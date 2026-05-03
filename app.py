import os
import pandas as pd
from google import genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sentence_transformers import SentenceTransformer, util
from PIL import Image
import io

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

# --- Configuration ---
app.config['SECRET_KEY'] = 'suryam_btech_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- AI & Data Setup ---
# FIXED: Using quotes around the API key to prevent NameError
client = genai.Client(api_key="AIzaSyDoUUWys3ZKLcTbLY7nIBIozg-a0rYT0wE")
text_model = SentenceTransformer('all-MiniLM-L6-v2')

# Load the 1 Lakh Row Dataset
csv_path = os.path.join(basedir, 'fashion_data.csv')
df = pd.read_csv(csv_path) if os.path.exists(csv_path) else pd.DataFrame()

# Pre-calculate embeddings for high-speed vector search
material_list = df['Material'].tolist() if not df.empty else []
embeddings = text_model.encode(material_list, convert_to_tensor=True) if material_list else None

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Authentication Routes ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        new_user = User(username=request.form['username'], password=hashed_pw)
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except Exception:
            flash("Username already exists!")
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('home'))
        flash("Invalid Credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Core Intelligence Logic ---
@app.route('/')
@login_required
def home():
    return render_template('index.html', name=current_user.username)

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    user_text = request.form.get('message', '').strip()
    image_file = request.files.get('image')
    
    # Tier 1: Local Dataset Search
    if embeddings is not None and user_text:
        query_emb = text_model.encode(user_text, convert_to_tensor=True)
        scores = util.cos_sim(query_emb, embeddings)[0]
        idx = scores.argmax().item()

        if scores[idx].item() > 0.5: 
            row = df.iloc[idx]
            
            # FIXED: Safe retrieval to prevent KeyError crashes
            water = row.get('Water_Usage_Liters', 'N/A')
            co2 = row.get('CO2_kg', 'N/A')
            notes = row.get('Eco_Notes', 'Data verified.')

            return jsonify({
                "status": "success",
                "material": row['Material'],
                "score": int(row['Sustainability_Score']),
                "water": f"{water}L",
                "co2": f"{co2}kg",
                "notes": f"✅ VERIFIED DATABASE MATCH\n\n{notes}"
            })

    # Tier 2: AI Fallback (For Brands like Zara or Images)
    try:
        img = None
        if image_file:
            img = Image.open(image_file)
            prompt = "Analyze this garment's material and provide a sustainability summary."
            response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, img])
        else:
            prompt = f"Provide a brief sustainability overview for '{user_text}'."
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        
        return jsonify({
            "status": "success",
            "material": user_text.title() if user_text else "Analyzed Item",
            "score": 45,
            "water": "Variable",
            "co2": "High",
            "notes": f"🌐 AI LIVE REPORT:\n\n{response.text}"
        })
    except Exception as e:
        print(f"!!! API ERROR: {e}") 
        return jsonify({"status": "error", "reply": "AI service temporarily unavailable."})

# --- System Initialization ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)