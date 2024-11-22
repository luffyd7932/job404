from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os
import openai



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Set your OpenAI API key here
openai.api_key = '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'

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Initialize the database
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    # Check if user exists
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already exists"}), 400

    # Hash the password
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(name=name, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # Authenticate user
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['user_name'] = user.name
        return jsonify({"message": "Login successful"}), 200
    else:
        return jsonify({"message": "Invalid email or password"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/profile', methods=['GET'])
def profile():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    user = User.query.get(session['user_id'])
    return jsonify({
        "name": user.name,
        "email": user.email
    }), 200

# Extend the User model to include a Profile
class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_title = db.Column(db.String(100), nullable=True)
    skills = db.Column(db.Text, nullable=True)
    experience = db.Column(db.Text, nullable=True)
    education = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    salary = db.Column(db.String(50), nullable=True)


    # Job Model
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    skills = db.Column(db.Text, nullable=False)  # Comma-separated list of skills
    location = db.Column(db.String(100), nullable=False)
    salary = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)

@app.route('/recommended_jobs', methods=['GET'])
def recommended_jobs():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    user_id = session['user_id']
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        return jsonify({"message": "Profile not found"}), 404

    # Extract profile attributes
    user_skills = profile.skills.lower().split(',')  # Skills are separated by commas
    user_job_title = profile.job_title.lower() if profile.job_title else ''
    user_location = profile.location.lower() if profile.location else ''
    user_salary = float(profile.salary) if profile.salary else 0

    # Query jobs based on profile attributes
    jobs = Job.query.all()  # Fetch all jobs (in production, consider filtering)
    
    recommended_jobs = []
    for job in jobs:
        job_skills = job.skills.lower().split(',')
        job_title = job.title.lower()
        job_location = job.location.lower()
        job_salary = float(job.salary)

        # Check if job matches the profile
        skill_match = any(skill in user_skills for skill in job_skills)
        job_title_match = user_job_title in job_title
        location_match = user_location in job_location
        salary_match = user_salary <= job_salary  # Ensure the salary is equal or greater

        if skill_match or job_title_match or location_match or salary_match:
            recommended_jobs.append(job)

    return jsonify([
        {
            "title": job.title,
            "skills": job.skills,
            "location": job.location,
            "salary": job.salary,
            "description": job.description
        }
        for job in recommended_jobs
    ]), 200

# Example job insertions (You can add this in a script or directly in your Flask shell)
with app.app_context():
    job1 = Job(title="Software Engineer", skills="Python, Java, SQL", location="New York", salary="100000", description="Develop software applications.")
    job2 = Job(title="Data Scientist", skills="Python, Machine Learning, SQL", location="San Francisco", salary="120000", description="Analyze and model data.")
    
    db.session.add(job1)
    db.session.add(job2)
    db.session.commit()


# Initialize the database (ensure this is called to update the schema)
with app.app_context():
    db.create_all()

# Route to update or create a profile
@app.route('/profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.json
    user_id = session['user_id']

    # Check if the user already has a profile
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        # Create a new profile if it doesn't exist
        profile = Profile(user_id=user_id)

    # Update profile fields
    profile.job_title = data.get('jobTitle')
    profile.skills = data.get('skills')
    profile.experience = data.get('experience')
    profile.education = data.get('education')
    profile.location = data.get('location')
    profile.salary = data.get('salary')

    db.session.add(profile)
    db.session.commit()

    return jsonify({"message": "Profile updated successfully"}), 200

# Route to get the current user's profile
@app.route('/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    user_id = session['user_id']
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        return jsonify({"message": "Profile not found"}), 404

    return jsonify({
        "jobTitle": profile.job_title,
        "skills": profile.skills,
        "experience": profile.experience,
        "education": profile.education,
        "location": profile.location,
        "salary": profile.salary
    }), 200


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        prompt = data['prompt']

        # Check if the prompt asks for real-time info
        if "real-time" in prompt.lower():  # Example condition for triggering real-time data
            # Fetch real-time news using an API (example using a news API)
            news_api_url = 'https://newsapi.org/v2/top-headlines'
            params = {
                'country': 'us',  # Example: get news for the US
                'apiKey': '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'
            }
            news_response = requests.get(news_api_url, params=params)
            news_data = news_response.json()
            
            if news_data.get('status') == 'ok':
                articles = news_data.get('articles', [])
                if articles:
                    latest_article = articles[0]  # Just an example to get the first article
                    reply = latest_article['title'] + " - " + latest_article['description']
                else:
                    reply = "Sorry, no news available right now."
            else:
                reply = "Sorry, there was an error fetching the news."

        else:
            # Process other prompts normally using GPT-4
            messages = [{"role": "user", "content": prompt}]
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=150
            )
            reply = response['choices'][0]['message']['content'].strip()

        return jsonify({'reply': reply})

    except Exception as e:
        print("Error:", e)
        return jsonify({'reply': "Sorry, something went wrong. Please try again later."}), 500


if __name__ == '__main__':
    app.run(debug=True)
