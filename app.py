from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)

app.config['SECRET_KEY'] = 'blogspace-development-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# =========================
# DATABASE MODELS
# =========================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    blogs = db.relationship('Blog', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='commenter', lazy=True)


class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    comments = db.relationship(
        'Comment',
        backref='blog',
        lazy=True,
        cascade='all, delete-orphan'
    )


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    blog_id = db.Column(db.Integer, db.ForeignKey('blog.id'), nullable=False)


# =========================
# HOME PAGE
# =========================

@app.route('/')
def index():
    blogs = Blog.query.order_by(Blog.date_created.desc()).all()
    return render_template('index.html', blogs=blogs)


# =========================
# USER REGISTRATION
# =========================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']

        if not username or not email or not password:
            flash('All fields are required.')
            return redirect(url_for('register'))

        if len(password) < 8:
            flash('Password must contain at least 8 characters.')
            return redirect(url_for('register'))

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            flash('Username or email already exists.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')


# =========================
# USER LOGIN
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email'].strip().lower()
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username

            flash('Login successful!')
            return redirect(url_for('index'))

        flash('Invalid email or password.')

    return render_template('login.html')


# =========================
# USER LOGOUT
# =========================

@app.route('/logout', methods=['GET'])
def logout():

    session.clear()
    flash('You have been logged out.')

    return redirect(url_for('index'))


# =========================
# CREATE BLOG
# =========================

@app.route('/create-blog', methods=['GET', 'POST'])
def create_blog():

    if 'user_id' not in session:
        flash('Please login to create a blog.')
        return redirect(url_for('login'))

    if request.method == 'POST':

        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()

        if not title or not content:
            flash('Title and content are required.')
            return redirect(url_for('create_blog'))

        new_blog = Blog(
            title=title,
            content=content,
            user_id=session['user_id']
        )

        db.session.add(new_blog)
        db.session.commit()

        flash('Your blog has been published successfully!')
        return redirect(url_for('index'))

    return render_template('create_blog.html')


# =========================
# VIEW BLOG DETAILS
# =========================

@app.route('/blog/<int:blog_id>')
def blog_details(blog_id):

    blog = Blog.query.get_or_404(blog_id)

    return render_template('blog_details.html', blog=blog)


# =========================
# EDIT BLOG
# =========================

@app.route('/edit-blog/<int:blog_id>', methods=['GET', 'POST'])
def edit_blog(blog_id):

    if 'user_id' not in session:
        flash('Please login to edit a blog.')
        return redirect(url_for('login'))

    blog = Blog.query.get_or_404(blog_id)

    # Only the blog owner can edit it
    if blog.user_id != session['user_id']:
        flash('You are not allowed to edit this blog.')
        return redirect(url_for('blog_details', blog_id=blog.id))

    if request.method == 'POST':

        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()

        if not title or not content:
            flash('Title and content are required.')
            return redirect(url_for('edit_blog', blog_id=blog.id))

        blog.title = title
        blog.content = content

        db.session.commit()

        flash('Blog updated successfully!')
        return redirect(url_for('blog_details', blog_id=blog.id))

    return render_template('edit_blog.html', blog=blog)


# =========================
# DELETE BLOG
# =========================

@app.route('/delete-blog/<int:blog_id>', methods=['POST'])
def delete_blog(blog_id):

    if 'user_id' not in session:
        flash('Please login to delete a blog.')
        return redirect(url_for('login'))

    blog = Blog.query.get_or_404(blog_id)

    # Only the blog owner can delete it
    if blog.user_id != session['user_id']:
        flash('You are not allowed to delete this blog.')
        return redirect(url_for('blog_details', blog_id=blog.id))

    db.session.delete(blog)
    db.session.commit()

    flash('Blog deleted successfully!')
    return redirect(url_for('index'))


# =========================
# ADD COMMENT
# =========================

@app.route('/blog/<int:blog_id>/comment', methods=['POST'])
def add_comment(blog_id):

    if 'user_id' not in session:
        flash('Please login to comment.')
        return redirect(url_for('login'))

    blog = Blog.query.get_or_404(blog_id)

    content = request.form.get('content', '').strip()

    if not content:
        flash('Comment cannot be empty.')
        return redirect(url_for('blog_details', blog_id=blog.id))

    new_comment = Comment(
        content=content,
        user_id=session['user_id'],
        blog_id=blog.id
    )

    db.session.add(new_comment)
    db.session.commit()

    flash('Comment added successfully!')

    return redirect(url_for('blog_details', blog_id=blog.id))

# =========================
# RESTFUL BLOG APIs
# =========================

# API 1: GET ALL BLOGS
@app.route('/api/blogs', methods=['GET'])
def api_get_blogs():

    blogs = Blog.query.order_by(Blog.date_created.desc()).all()

    blog_list = []

    for blog in blogs:
        blog_list.append({
            'id': blog.id,
            'title': blog.title,
            'content': blog.content,
            'author': blog.author.username,
            'date_created': blog.date_created.isoformat()
        })

    return jsonify(blog_list), 200


# API 2: GET SINGLE BLOG
@app.route('/api/blogs/<int:blog_id>', methods=['GET'])
def api_get_blog(blog_id):

    blog = Blog.query.get_or_404(blog_id)

    return jsonify({
        'id': blog.id,
        'title': blog.title,
        'content': blog.content,
        'author': blog.author.username,
        'date_created': blog.date_created.isoformat()
    }), 200


# API 3: CREATE BLOG
@app.route('/api/blogs', methods=['POST'])
def api_create_blog():

    if 'user_id' not in session:
        return jsonify({'error': 'Login required'}), 401

    data = request.get_json(silent=True) or {}

    title = data.get('title', '').strip()
    content = data.get('content', '').strip()

    if not title or not content:
        return jsonify({
            'error': 'Title and content are required'
        }), 400

    new_blog = Blog(
        title=title,
        content=content,
        user_id=session['user_id']
    )

    db.session.add(new_blog)
    db.session.commit()

    return jsonify({
        'message': 'Blog created successfully',
        'id': new_blog.id
    }), 201


# API 4: UPDATE BLOG
@app.route('/api/blogs/<int:blog_id>', methods=['PUT'])
def api_update_blog(blog_id):

    if 'user_id' not in session:
        return jsonify({'error': 'Login required'}), 401

    blog = Blog.query.get_or_404(blog_id)

    if blog.user_id != session['user_id']:
        return jsonify({'error': 'Permission denied'}), 403

    data = request.get_json(silent=True) or {}

    title = data.get('title', '').strip()
    content = data.get('content', '').strip()

    if not title or not content:
        return jsonify({
            'error': 'Title and content are required'
        }), 400

    blog.title = title
    blog.content = content

    db.session.commit()

    return jsonify({
        'message': 'Blog updated successfully'
    }), 200


# API 5: DELETE BLOG
@app.route('/api/blogs/<int:blog_id>', methods=['DELETE'])
def api_delete_blog(blog_id):

    if 'user_id' not in session:
        return jsonify({'error': 'Login required'}), 401

    blog = Blog.query.get_or_404(blog_id)

    if blog.user_id != session['user_id']:
        return jsonify({'error': 'Permission denied'}), 403

    db.session.delete(blog)
    db.session.commit()

    return jsonify({
        'message': 'Blog deleted successfully'
    }), 200


# =========================
# RESTFUL COMMENT APIs
# =========================

# API 6: GET COMMENTS
@app.route('/api/blogs/<int:blog_id>/comments', methods=['GET'])
def api_get_comments(blog_id):

    blog = Blog.query.get_or_404(blog_id)

    comments = []

    for comment in blog.comments:
        comments.append({
            'id': comment.id,
            'content': comment.content,
            'username': comment.commenter.username,
            'date_created': comment.date_created.isoformat()
        })

    return jsonify(comments), 200


# API 7: ADD COMMENT
@app.route('/api/blogs/<int:blog_id>/comments', methods=['POST'])
def api_add_comment(blog_id):

    if 'user_id' not in session:
        return jsonify({'error': 'Login required'}), 401

    blog = Blog.query.get_or_404(blog_id)

    data = request.get_json(silent=True) or {}
    content = data.get('content', '').strip()

    if not content:
        return jsonify({
            'error': 'Comment cannot be empty'
        }), 400

    new_comment = Comment(
        content=content,
        user_id=session['user_id'],
        blog_id=blog.id
    )

    db.session.add(new_comment)
    db.session.commit()

    return jsonify({
        'message': 'Comment added successfully',
        'id': new_comment.id
    }), 201

# =========================
# RUN APPLICATION
# =========================

if __name__ == '__main__':

    with app.app_context():
        db.create_all()

    app.run(debug=True)
