from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)

# Index Route
@app.route('/')
def index():
    return render_template('home.html')

# About Route
@app.route('/about')
def about():
    return render_template('about.html')

# Articles Route
@app.route('/articles')
def articles():
    try:
        # Create cursor
        cur = mysql.connection.cursor()

        # Get articles
        result = cur.execute("SELECT * FROM articles")

        articles = cur.fetchall()

        if result > 0:
            return render_template('articles.html', articles=articles)
        else:
            msg = 'No Articles Found'
            return render_template('articles.html', msg=msg)

    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for('index'))
    finally:
        cur.close()

# Single Article Route
@app.route('/article/<string:id>/')
def article(id):
    try:
        # Create cursor
        cur = mysql.connection.cursor()

        # Get article
        result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

        article = cur.fetchone()
        return render_template('article.html', article=article)

    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for('articles'))
    finally:
        cur.close()

# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

# User Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        try:
            # Create cursor
            cur = mysql.connection.cursor()

            # Execute query
            cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

            # Commit to DB
            mysql.connection.commit()

            # Close connection
            cur.close()

            flash('You are now registered and can log in', 'success')

            return redirect(url_for('login'))

        except Exception as e:
            flash(f"An error occurred: {e}", 'danger')
            return redirect(url_for('register'))

    return render_template('register.html', form=form)

# User Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']

        try:
            cur = mysql.connection.cursor()

            result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

            if result > 0:
                data = cur.fetchone()
                password = data['password']

                # Verify password
                if sha256_crypt.verify(password_candidate, password):
                    session['logged_in'] = True
                    session['username'] = username
                    flash('You are now logged in', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    error = 'Invalid login, incorrect password.'
                    return render_template('login.html', error=error)
            else:
                error = 'Username not found'
                return render_template('login.html', error=error)

        except Exception as e:
            flash(f"An error occurred: {e}", 'danger')
            return redirect(url_for('login'))
        finally:
            cur.close()

    return render_template('login.html')

# Check if user is logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Logout Route
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Dashboard Route
@app.route('/dashboard')
@is_logged_in
def dashboard():
    try:
        cur = mysql.connection.cursor()

        # Show articles only from the user logged in
        result = cur.execute("SELECT * FROM articles WHERE author = %s", [session['username']])

        articles = cur.fetchall()

        if result > 0:
            return render_template('dashboard.html', articles=articles)
        else:
            msg = 'No Articles Found'
            return render_template('dashboard.html', msg=msg)

    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for('dashboard'))
    finally:
        cur.close()

# Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])

# Add Article Route
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        try:
            # Create Cursor
            cur = mysql.connection.cursor()

            # Execute query
            cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, session['username']))

            # Commit to DB
            mysql.connection.commit()

            # Close connection
            cur.close()

            flash('Article Created', 'success')

            return redirect(url_for('dashboard'))

        except Exception as e:
            flash(f"An error occurred: {e}", 'danger')
            return redirect(url_for('add_article'))

    return render_template('add_article.html', form=form)

# Edit Article Route
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    try:
        # Create cursor
        cur = mysql.connection.cursor()

        # Get article by id
        result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

        article = cur.fetchone()
        cur.close()

        form = ArticleForm(request.form)
        form.title.data = article['title']
        form.body.data = article['body']

        if request.method == 'POST' and form.validate():
            title = request.form['title']
            body = request.form['body']

            try:
                cur = mysql.connection.cursor()
                cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title, body, id))
                mysql.connection.commit()
                cur.close()

                flash('Article Updated', 'success')

                return redirect(url_for('dashboard'))

            except Exception as e:
                flash(f"An error occurred: {e}", 'danger')
                return redirect(url_for('edit_article', id=id))

    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)

# Delete Article Route
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    try:
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute("DELETE FROM articles WHERE id = %s", [id])

        # Commit to DB
        mysql.connection.commit()

        cur.close()

        flash('Article Deleted', 'success')

        return redirect(url_for('dashboard'))

    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)
