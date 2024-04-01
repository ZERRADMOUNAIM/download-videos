from flask import Flask, render_template, request, send_file, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
import requests
import io
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from flask import flash
import os
from flask import send_from_directory

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'allinonedownmedia2021'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = 'allinonedownmedia2021'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)


class RegisterForm(FlaskForm):
    username = StringField('الإسم', validators=[InputRequired(), Length(min=4, max=20)] ,render_kw={"placeholder": "الإسم"})
    password = PasswordField('كلمة المرور', validators=[InputRequired(), Length(min=8, max=80)], render_kw={"placeholder": "كلمة المرور"})
    submit = SubmitField('تسجيل')

    def validate_username(self, username):
        existing_user = User.query.filter_by(username=username.data).first()
        if existing_user:
            raise ValidationError('هذا الإسم موجود بالفعل. يرجى اختيار إسم آخر.')

class LoginForm(FlaskForm):
    username = StringField('الإسم', validators=[InputRequired(), Length(min=4, max=20)] ,render_kw={"placeholder": "الإسم"})
    password = PasswordField('كلمة المرور', validators=[InputRequired(), Length(min=8, max=80)], render_kw={"placeholder": "كلمة المرور"})

class UploadedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=True)
    platform = db.Column(db.String(50), nullable=False)  # Nouvelle colonne pour stocker la plateforme




@app.route('/')
def index():
    files_with_urls = UploadedFile.query.filter_by(platform='Home').all()
    return render_template('Home.html', files_with_urls=files_with_urls)



@app.route('/homelogin')
def home():
    return render_template("home_log.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/Naif@2024cnc', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from flask import render_template

@app.route('/dashboard', methods=['POST'])
@login_required
def upload_image():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    url = request.form.get('url')
    platform = request.form.get('platform')  # Récupérer la plateforme depuis le formulaire
    if file.filename == '' and not url:
        flash('No image selected for uploading')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_file = UploadedFile(filename=filename, url=url, platform=platform)  # Enregistrer la plateforme dans la base de données
        db.session.add(new_file)
        db.session.commit()
        flash('Image successfully uploaded')
        return redirect(url_for('dashboard', filename=filename))
    else:
        flash('Allowed image types are - png, jpg, jpeg, gif')
    return redirect(url_for('dashboard'))



@app.route('/delete_image', methods=['POST'])
@login_required
def delete_image():
    platform = request.form.get('platform')
    if platform:
        # Supprimer les images en fonction de la plateforme
        files_to_delete = UploadedFile.query.filter_by(platform=platform).all()
        for file in files_to_delete:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            db.session.delete(file)
        db.session.commit()
        flash('Images successfully deleted for platform {}'.format(platform))
    else:
        flash('No platform specified for deletion')
    return redirect(url_for('dashboard'))






@app.route('/display/<filename>')
def display_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



# @app.route('/download', methods=['POST'])
# def download():
#     url = request.form['url']

#     # Utilisez votre API pour obtenir les informations nécessaires
#     api_url = "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink"
#     headers = {
#         "content-type": "application/json",
#         "X-RapidAPI-Key": "86ecc87551msh861f870fd8435b3p1cba24jsn86662259e7fd",
#         "X-RapidAPI-Host": "social-download-all-in-one.p.rapidapi.com"
#     }
#     response = requests.post(api_url, json={"url": url}, headers=headers)
#     data = response.json()

#     return render_template('download.html', data=data)
@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    
    if 'soundcloud' in url.lower() or 'Soundcloud' in url or 'snapchat' in url or 'Snapchat' in url or 'LinkedIn' in url or 'linkedin' in url.lower() or 'pin' in url.lower() or 'pinterest' in url.lower():
        api_url = "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink"

        payload = { "url": url}
        headers = {
                "content-type": "application/json",
                "X-RapidAPI-Key": "2e2453cff2msh8affd8801abc98bp1ac0e2jsned733e0f829f",
                "X-RapidAPI-Host": "social-download-all-in-one.p.rapidapi.com"
            }

        response = requests.post(api_url, json=payload, headers=headers)
        mou = response.json()
        platform = 'soundcloud'
        
        return render_template('download.html', mou=mou, platform=platform)

    elif 'youtube' in url.lower() or 'Youtube' in url or 'youtu' in url.lower():
        api_url = "https://youtube-media-downloader2.p.rapidapi.com/ajaxSearch"
        headers = {
            "X-RapidAPI-Key": "2e2453cff2msh8affd8801abc98bp1ac0e2jsned733e0f829f",
            "X-RapidAPI-Host": "youtube-media-downloader2.p.rapidapi.com"
        }
        params = {"url": url}
        response = requests.get(api_url, headers=headers, params=params)
        data = response.json()
        platform = 'youtube'
        return render_template('download.html', data=data, platform=platform)

    elif 'threads' in url.lower() or 'threads' in url.lower() or 'threads' in url.lower():
        api_url = "https://threads-downloader-scraper-api.p.rapidapi.com/threads"
        headers = {
            "X-RapidAPI-Key": "2e2453cff2msh8affd8801abc98bp1ac0e2jsned733e0f829f",
            "X-RapidAPI-Host": "tthreads-downloader-scraper-api.p.rapidapi.com"
        }
        params = {"url": url}
        response = requests.get(api_url, headers=headers, params=params)
        data = response.json()
        platform = 'threads'
        return render_template('download.html', data=data, platform=platform)


    elif 'facebook' in url.lower() or 'Facebook' in url.lower() or 'fb' in url.lower() or 'instagram' in url.lower() or 'Instagram' in url or 'tiktok' in url.lower() or 'Tiktok' in url or 'youtube' in url.lower() or 'Youtube' in url or 'youtu' in url.lower():
        api_url = "https://social-media-video-downloader.p.rapidapi.com/smvd/get/all"
        headers = {
            "X-RapidAPI-Key": "c931710f09msh47869a3597dd7c1p1cce87jsn95c34f3d43ff",
            "X-RapidAPI-Host": "social-media-video-downloader.p.rapidapi.com"
        }
        params = {"url": url}
        response = requests.get(api_url, headers=headers, params=params)
        data = response.json()
        # print(data)
        
        platform = 'Facebook'
        return render_template('download.html', data=data, platform=platform)
    
    elif 'twitter' in url.lower() or 'x' in url.lower() or 'X' in url.lower():
        api_url = "https://twitter277.p.rapidapi.com/qTweet"
        headers = {
            "X-RapidAPI-Key": "c931710f09msh47869a3597dd7c1p1cce87jsn95c34f3d43ff",
            "X-RapidAPI-Host": "twitter277.p.rapidapi.com"
        }
        params = {"url": url}
        response = requests.get(api_url, headers=headers, params=params)
        data = response.json()
        platform = 'twitter'
        return render_template('download.html', data=data, platform=platform)

    else:
        return "URL non prise en charge"


@app.route('/download-video', methods=['POST'])
def download_video():
    video_url = request.form['video_url']
    title = request.form['title']
    response = requests.get(video_url, stream=True)
    return send_file(io.BytesIO(response.content), as_attachment=True, download_name= title + "_video.mp4")

@app.route('/download-audio', methods=['POST'])
def download_audio():
    audio_url = request.form['audio_url']
    title = request.form['title']

    response = requests.get(audio_url, stream=True)
    return send_file(io.BytesIO(response.content), as_attachment=True, download_name=   title +"_audio.mp3")

@app.route('/Instagram')
def Instagram():
    files_home = UploadedFile.query.filter_by(platform='Home').all()
    files_with_urls = UploadedFile.query.filter_by(platform='Instagram').all()
    return render_template('Instagram.html', files_with_urls=files_with_urls, files_home=files_home)

@app.route('/Facebook')
def Facebook():
    files_home = UploadedFile.query.filter_by(platform='Home').all()
    files_with_urls = UploadedFile.query.filter_by(platform='Facebook').all()
    return render_template('Facebook.html', files_with_urls=files_with_urls, files_home=files_home)



@app.route('/Snapchat')
def Snapchat():
    files_home = UploadedFile.query.filter_by(platform='Home').all()
    files_with_urls = UploadedFile.query.filter_by(platform='Snapchat').all()
    return render_template('Snapchat.html', files_with_urls=files_with_urls, files_home=files_home)

@app.route('/Spotify')
def Spotify():
    files_home = UploadedFile.query.filter_by(platform='Home').all()
    files_with_urls = UploadedFile.query.filter_by(platform='Spotify').all()
    return render_template('Spotify.html', files_with_urls=files_with_urls, files_home=files_home)

@app.route('/Tiktok')
def Tiktok():
    files_home = UploadedFile.query.filter_by(platform='Home').all()
    files_with_urls = UploadedFile.query.filter_by(platform='TikTok').all()
    return render_template('Tiktok.html', files_with_urls=files_with_urls, files_home=files_home)

@app.route('/Twitter')
def Twitter():
    files_home = UploadedFile.query.filter_by(platform='Home').all()
    files_with_urls = UploadedFile.query.filter_by(platform='Twitter').all()
    return render_template('Twitter.html', files_with_urls=files_with_urls, files_home=files_home)

@app.route('/Reddit')
def Reddit():
    files_home = UploadedFile.query.filter_by(platform='Home').all()
    files_with_urls = UploadedFile.query.filter_by(platform='Reddit').all()
    return render_template('Reddit.html', files_with_urls=files_with_urls, files_home=files_home)

@app.route('/SoundCloud')
def SoundCloud():
    files_home = UploadedFile.query.filter_by(platform='Home').all()
    files_with_urls = UploadedFile.query.filter_by(platform='SoundCloud').all()
    return render_template('SoundCloud.html', files_with_urls=files_with_urls, files_home=files_home)

@app.route('/youtube')
def Youtube():
    files_home = UploadedFile.query.filter_by(platform='Home').all()
    files_with_urls = UploadedFile.query.filter_by(platform='YouTube').all()
    return render_template('Youtube.html', files_with_urls=files_with_urls, files_home=files_home)

@app.route('/Pinterest')
def Pinterest():
    files_home = UploadedFile.query.filter_by(platform='Home').all()
    files_with_urls = UploadedFile.query.filter_by(platform='Pinterest').all()
    return render_template('Pinterest.html', files_with_urls=files_with_urls, files_home=files_home)

@app.route('/LinkedIn')
def LinkedIn():
    files_home = UploadedFile.query.filter_by(platform='Home').all()
    files_with_urls = UploadedFile.query.filter_by(platform='LinkedIn').all()
    return render_template('LinkedIn.html', files_with_urls=files_with_urls, files_home=files_home)
@app.route('/Threads')
def Threads():
    files_home = UploadedFile.query.filter_by(platform='Home').all()
    files_with_urls = UploadedFile.query.filter_by(platform='Threads').all()
    return render_template('Threads.html', files_with_urls=files_with_urls, files_home=files_home)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
