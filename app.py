from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# מפתח אבטחה לסשנים (מומלץ לשנות במערכת ייצור)
app.config['SECRET_KEY'] = 'super-secret-key-for-memo-app'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- מודלים של בסיס הנתונים ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    memos = db.relationship('Memo', backref='author', lazy=True)

class Memo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- נתיבי האפליקציה (Routes) ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('שם משתמש או סיסמה אינם נכונים', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('שם משתמש זה כבר קיים במערכת', 'error')
        else:
            hashed_pw = generate_password_hash(password, method='scrypt')
            new_user = User(username=username, password=hashed_pw)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('dashboard'))

    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # שליפת המזכרים של המשתמש המחובר בלבד
    memos = Memo.query.filter_by(user_id=current_user.id).order_by(Memo.created_at.desc()).all()
    return render_template('dashboard.html', memos=memos)

@app.route('/memo/add', methods=['POST'])
@login_required
def add_memo():
    content = request.form.get('content')
    if content and content.strip():
        new_memo = Memo(content=content.strip(), user_id=current_user.id)
        db.session.add(new_memo)
        db.session.commit()
        flash('המזכר נשמר בהצלחה!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/memo/delete/<int:memo_id>', methods=['POST'])
@login_required
def delete_memo(memo_id):
    memo = Memo.query.get_or_404(memo_id)
    # אבטחה: לוודא שרק הבעלים של המזכר יכול למחוק אותו
    if memo.user_id == current_user.id:
        db.session.delete(memo)
        db.session.commit()
        flash('המזכר נמחק בהצלחה', 'info')
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # יצירת טבלאות בסיס הנתונים באופן אוטומטי
    app.run(debug=True)