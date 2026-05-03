import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sentence_transformers import SentenceTransformer, util
import google.generativeai as genai  # Standard library for Render
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
# Use Environment Variable for security
API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_KEY_HERE")
genai.configure(api_key=API_KEY)
text_model = SentenceTransformer('all-MiniLM-L6-v2')

# Load Dataset
csv_path = os.path.join(basedir, 'fashion_data.csv')
if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    material_list = df['Material'].tolist()
    embeddings = text_model.encode(material_list, convert_to_tensor=True)
else:
    df = pd.DataFrame()
    embeddings = None

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

@app.route('/')
@login_required
def home():
    # Matches the dashboard.html file you provided
    return render_template('dashboard.html', name=current_user.username)

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    user_text = request.form.get('message', '').strip()
    image_file = request.files.get('image')
    
    # 1. Vector Search
    if embeddings is not None and user_text:
        query_emb = text_model.encode(user_text, convert_to_tensor=True)
        scores = util.cos_sim(query_emb, embeddings)[0]
        idx = scores.argmax().item()

        if scores[idx].item() > 0.6: 
            row = df.iloc[idx]
            return jsonify({
                "status": "success",
                "material": row['Material'],
                "score": int(row['Sustainability_Score']),
                "water": f"{row.get('Water_Usage_Liters', 'N/A')}L",
                "co2": f"{row.get('CO2_kg', 'N/A')}kg",
                "notes": row.get('Eco_Notes', 'Data verified.')
            })

    # 2. Gemini AI Fallback
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        if image_file:
            img = Image.open(image_file)
            response = model.generate_content(["Analyze sustainability of this garment.", img])
        else:
            response = model.generate_content(f"Sustainability summary for: {user_text}")
        
        return jsonify({
            "status": "success",
            "material": user_text.title() if user_text else "Item",
            "score": 50,
            "water": "Variable",
            "co2": "Moderate",
            "notes": response.text
        })
    except Exception as e:
        return jsonify({"status": "error", "reply": "AI error. Check API key."})

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)