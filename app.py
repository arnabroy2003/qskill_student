from flask import Flask, request, render_template, redirect, url_for, flash
from supabase import create_client

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Supabase config
SUPABASE_URL = "https://rithbuogcwvjmzqoyrcj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJpdGhidW9nY3d2am16cW95cmNqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4MzUxOTUsImV4cCI6MjA4OTQxMTE5NX0.mo-8nz5oT9uFdlJR2GiRUmLWI9crNf5E8JQm3Oz0Kb4"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# 🔐 LOGIN ROUTE
@app.route('/', methods=['GET', 'POST'])
def login():
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


        except Exception as e:
            flash("Server error, try again")
            return redirect(url_for('login'))

        if not data:
            flash("User not found")
            return redirect(url_for('login'))

        # Name (first row)
        name = data[0]['name']

        # Domains & IDs (max 5)
        domains = [d['domain'] for d in data][:5]
        ids = [d['id'] for d in data][:5]
        offer = [d['offer'] for d in data][:5]

        # Pair them for Jinja loop
        student_data = list(zip(domains, ids))
        active_offers_dict = dict(zip(domains, offer))

        return render_template(
            'dashboard.html',
            name=name,
            student_data=student_data,
            active_domains=domains,
            active_offers=active_offers_dict
        )

    return render_template('login.html')


# 🚪 OPTIONAL LOGOUT (future use)
@app.route('/logout')
def logout():
    return redirect(url_for('login'))


# 🔥 RUN APP
if __name__ == '__main__':
    app.run(debug=True)