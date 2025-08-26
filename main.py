from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_mail import Mail
import os
import math
from datetime import datetime
import pymysql
pymysql.install_as_MySQLdb()

# Load environment variables from .env locally
from dotenv import load_dotenv
load_dotenv()

# -----------------------------
# Environment variables instead of config.json
# -----------------------------
local_server = os.getenv("LOCAL_SERVER", "True") == "True"
gmail_user = os.getenv("GMAIL_USER")
gmail_password = os.getenv("GMAIL_PASSWORD")
no_of_posts = int(os.getenv("NO_OF_POSTS", 2))
admin_user = os.getenv("ADMIN_USER", "rajina")
admin_password = os.getenv("ADMIN_PASSWORD", "admin")
upload_location = os.getenv("UPLOAD_LOCATION", "./static")
local_uri = os.getenv("LOCAL_URI")
prod_uri = os.getenv("PROD_URI")

params = {
    "no_of_posts": no_of_posts,
    "admin_user": admin_user,
    "admin_password": admin_password,
    "upload_location": upload_location,
    "gmail-user": gmail_user,
    "gmail-password": gmail_password,
}

# -----------------------------
# Flask app setup
# -----------------------------
app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = upload_location
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME=gmail_user,
    MAIL_PASSWORD=gmail_password
)
mail = Mail(app)

if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = local_uri
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = prod_uri

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False                
db = SQLAlchemy(app)

# -----------------------------
# Models
# -----------------------------
class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.DateTime, nullable=True)
    email = db.Column(db.String(20), nullable=False)

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(21), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    tagline = db.Column(db.String(120), nullable=False)
    date = db.Column(db.DateTime, nullable=True)
    img_file = db.Column(db.String(12), nullable=True)

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    posts = Posts.query.all()
    last = math.ceil(len(posts)/no_of_posts)
    page = request.args.get('page')
    if not str(page).isnumeric():
        page = 1
    page = int(page)
    posts = posts[(page-1)*no_of_posts:(page-1)*no_of_posts+no_of_posts]

    # Pagination
    prev = "#" if page == 1 else f"/?page={page-1}"
    next_ = "#" if page == last else f"/?page={page+1}"

    return render_template("index.html", params=params, posts=posts, prev=prev, next=next_)

@app.route("/post/<string:post_slug>", methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template("post.html", params=params, post=post)

@app.route("/about")
def about():
    return render_template("about.html", params=params)

@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if 'user' in session and session['user'] == admin_user:
        posts = Posts.query.all()
        return render_template('dashboard.html', params=params, posts=posts)

    if request.method == 'POST':
        username = request.form.get('uname')
        userpass = request.form.get('pass')
        if username == admin_user and userpass == admin_password:
            session['user'] = username
            posts = Posts.query.all()
            return render_template('dashboard.html', params=params, posts=posts)
    
    return render_template("login.html", params=params)

@app.route("/edit/<int:sno>", methods=['GET','POST'])
def edit(sno):
    if 'user' in session and session['user'] == admin_user:
        if request.method == 'POST':
            box_title = request.form.get('title')
            tline = request.form.get('tline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            date = datetime.now()
        
            if sno == 0:
                existing_snos = [p.sno for p in Posts.query.order_by(Posts.sno).all()]
                new_sno = 1
                for i, s in enumerate(existing_snos, 1):
                    if s != i:
                        new_sno = i
                        break
                    new_sno = len(existing_snos) + 1
                post = Posts(sno=new_sno, title=box_title, slug=slug, content=content, tagline=tline, img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()
                return redirect(f'/edit/{post.sno}')
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = box_title
                post.slug = slug
                post.content = content
                post.tagline = tline
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect('/edit/'+ str(sno))

        post = Posts(sno=0, title="", slug="", content="", tagline="", img_file="") if sno == 0 else Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=post)
    
    return redirect('/dashboard')

@app.route("/uploader", methods=['GET','POST'])
def uploader():
    if 'user' in session and session['user'] == admin_user:
        if request.method == 'POST':
            f = request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "Uploaded successfully"

@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/dashboard')

@app.route("/delete/<int:sno>", methods=['GET','POST'])
def delete(sno):
    if 'user' in session and session['user'] == admin_user:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
        posts = Posts.query.order_by(Posts.sno).all()
        for idx, post in enumerate(posts, 1):
            post.sno = idx
        db.session.commit()
    return redirect('/dashboard')

@app.route("/contact", methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contacts(name=name, phone_num=phone, msg=message, date=datetime.now(), email=email)
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New message from Blog: ' + name,
                          sender=email,
                          recipients=[gmail_user],
                          body=message + "\n" + phone)
    return render_template("contact.html", params=params)

if __name__ == "__main__":
    app.run(debug=True)
