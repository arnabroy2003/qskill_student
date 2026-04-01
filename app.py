from flask import Flask, request, render_template, redirect, url_for, flash, session
from supabase import create_client
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv
import requests
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

# 🔥 Cloudinary Config
cloudinary.config(
     cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
     api_key=os.getenv("CLOUDINARY_API_KEY"),
     api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# 🔥 Supabase Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr


def get_location(ip):
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}").json()
        return res.get('city', 'Unknown'), res.get('country', 'Unknown')
    except:
        return "Unknown", "Unknown"
    
def track_visitor():
    if session.get('tracked'):
        return
    
    session['tracked'] = True

    ip = get_user_ip()
    city, country = get_location(ip)

    now = datetime.now()

    try:
        existing = supabase.table("visitors") \
            .select("*") \
            .eq("ip", ip) \
            .limit(1) \
            .execute()

        if not existing.data:
            supabase.table("visitors").insert({
                "ip": ip,
                "city": city,
                "country": country,
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S")
            }).execute()

    except Exception as e:
        print("Visitor tracking error:", e)


# 🔐 LOGIN ROUTE
@app.route('/', methods=['GET', 'POST'])
def login():

    track_visitor()

    if 'email' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')

        if not email:
            flash("Email is required")
            return redirect(url_for('login'))

        try:
            response = supabase.table("student") \
                .select("*") \
                .eq("email", email) \
                .execute()

            data = response.data

            if not data:
                flash("User not found")
                return redirect(url_for('login'))

            # 🔥 Save session
            session['email'] = email
            session['just_logged_in'] = True

            return redirect(url_for('dashboard'))

        except Exception as e:
            print(e)
            flash("Server error, try again")
            return redirect(url_for('login'))

    return render_template('login.html')


# 🔥 DASHBOARD ROUTE
@app.route('/dashboard')
def dashboard():
    email = session.get('email')

    if not email:
        return redirect(url_for('login'))

    try:
        response = supabase.table("student") \
            .select("*") \
            .eq("email", email) \
            .execute()

        data = response.data

        if not data:
            flash("User not found")
            return redirect(url_for('login'))

        img = data[0].get('img', None)
        name = data[0]['name']

        domains = [d['domain'] for d in data][:5]
        ids = [d['id'] for d in data][:5]
        offer = [d['offer'] for d in data][:5]

        student_data = list(zip(domains, ids))
        active_offers_dict = dict(zip(domains, offer))

        res = supabase.table("announcement").select("*").limit(1).execute()

        if res.data:
            announcement = res.data[0]['text']
            version = res.data[0]['version']
        else:
            announcement = "No announcement yet"
            version = 1

        # 🔥 NOTIFICATION LOGIC
        last_seen = session.get('announcement_seen', 0)

        if version > last_seen:
            show_notification = True
            session['announcement_seen'] = version
        else:
            show_notification = False

        return render_template(
            'dashboard.html',
            name=name,
            img=img,
            email=email,
            student_data=student_data,
            active_domains=domains,
            active_offers=active_offers_dict,
            show_notification=show_notification,
            announcement=announcement
        )

    except Exception as e:
        print(e)
        flash("Server error")
        return redirect(url_for('login'))


# 🚪 LOGOUT
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


# 📸 UPLOAD PHOTO
@app.route('/upload-photo', methods=['POST'])
def upload_photo():
    file = request.files.get('photo')
    email = session.get('email')

    if not file or not email:
        flash("Missing file or email")
        return redirect(url_for('dashboard'))

    try:
        folder_name = f"students/{email}"

        result = cloudinary.uploader.upload(
            file,
            folder=folder_name,
            public_id="profile",
            overwrite=True
        )

        image_url = result['secure_url']

        # 🔥 Update Supabase
        supabase.table("student") \
            .update({"img": image_url}) \
            .eq("email", email) \
            .execute()

        flash("Photo updated successfully")

    except Exception as e:
        print(e)
        flash("Upload failed")

    return redirect(url_for('dashboard'))

@app.route('/remove-photo', methods=['POST'])
def remove_photo():
    email = request.form.get('email')

    try:
        response = supabase.table("student") \
            .update({"img": None}) \
            .eq("email", email.strip().lower()) \
            .execute()

        print(response)
        flash("Photo removed successfully!")
        return redirect(url_for('dashboard'))

    except Exception as e:
        print(e)
        flash("Error removing photo")
        return redirect(url_for('dashboard'))
    
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == os.getenv("ADMIN") and password == os.getenv("PASSWORD"):
            session['admin'] = True
            return redirect(url_for('admin_panel'))
        else:
            flash("Invalid credentials")
            return redirect(url_for('admin'))

    return render_template('admin_login.html')

@app.route('/admin-panel', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    # 🔥 HANDLE POST (update announcement)
    if request.method == 'POST':
        announcement = request.form.get('announcement')

        if announcement:
            try:
                # 🔥 Get current announcement
                res = supabase.table("announcement").select("*").limit(1).execute()

                if res.data:
                    current = res.data[0]
                    new_version = current['version'] + 1

                    # 🔥 Update existing row
                    supabase.table("announcement") \
                        .update({
                            "text": announcement,
                            "version": new_version
                        }) \
                        .eq("id", current['id']) \
                        .execute()
                else:
                    # 🔥 Insert first row
                    supabase.table("announcement").insert({
                        "text": announcement,
                        "version": 1
                    }).execute()

                flash("Announcement Updated ✅")

            except Exception as e:
                print(e)
                flash("Error updating announcement")

    # 🔥 LOAD CURRENT ANNOUNCEMENT
    try:
        res = supabase.table("announcement").select("*").limit(1).execute()

        if res.data:
            current_announcement = res.data[0]['text']
        else:
            current_announcement = ""

    except Exception as e:
        print(e)
        current_announcement = ""

    return render_template('admin_panel.html', announcement=current_announcement)


# 🔥 RUN APP
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)