import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

# --- Configuration ---
app.config['SECRET_KEY'] = 'suryam_btech_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "" # Fix: Removes the red "Please log in" message

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(10), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256')
        new_user = User(username=request.form.get('username'), password=hashed_pw)
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            return "Username already exists!"
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('home'))
        return "Invalid Credentials."
    return render_template('login.html')

@app.route('/')
@login_required
def home():
    return render_template('dashboard.html', name=current_user.username)

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    # Lazy Loading models here to save RAM on Render

    from sentence_transformers import SentenceTransformer, util
    user_text = request.form.get('message', '').strip()
    csv_path = os.path.join(basedir, 'fashion_data.csv')
    
    if os.path.exists(csv_path) and user_text:
        df = pd.read_csv(csv_path).head(10) # Efficiency fix
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embs = model.encode(df['Material'].tolist(), convert_to_tensor=True)
        query_emb = model.encode(user_text, convert_to_tensor=True)
        idx = util.cos_sim(query_emb, embs)[0].argmax().item()
        row = df.iloc[idx]
        
        return jsonify({
            "status": "success",
            "material": row['Material'],
            "score": int(row['Sustainability_Score']),
            "water": f"{row.get('Water_Usage_Liters', 'N/A')}L",
            "co2": f"{row.get('CO2_kg', 'N/A')}kg",
            "notes": row.get('Eco_Notes', 'Verified Analysis.')
        })
    return jsonify({"status": "error"})

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)