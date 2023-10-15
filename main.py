from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from sqlalchemy.exc import IntegrityError
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

gravatar = Gravatar(app,force_default=False,default='retro',size=100)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    # This will act like a list of VlogPost objects attached to each other User
    # The 'author' refers to the author property in the BlogPost class
    posts = relationship('BlogPost', back_populates='author')
    usr_comments = relationship('Comment', back_populates='commentor')


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # Create a foreign Key, 'users.id' the users refers to the tablename of User
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    # create a reference to the User object, the 'posts' refers to the posts property in the User
    author = relationship('User', back_populates='posts')
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    blog_comments = relationship('Comment', back_populates='blogPost')

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    commentor = relationship('User', back_populates='usr_comments')
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    blogPost = relationship('BlogPost',back_populates='blog_comments')
    text = db.Column(db.Text, nullable=False)

    

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def loader_user(user_id):
    return db.session.get(User,user_id)

def admin_only(function):
    @wraps(function)
    def decorator_funtion(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            abort(403)
        return function(*args, **kwargs)
    return decorator_funtion
        
        

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register',methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        pasword = form.password.data
        try:
            with app.app_context():
                user = User(
                    email=form.email.data,
                    name=form.name.data,
                    password = generate_password_hash(pasword,'pbkdf2:sha256')
                )
                db.session.add(user)
                db.session.commit()
                login_user(user)
            return redirect(url_for('get_all_posts'))
        except IntegrityError:
            flash('You\'ve already signed up with that email, log in instead')
            return redirect(url_for('login'))
    return render_template("register.html",form=form)


@app.route('/login',methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        with app.app_context():
            user = db.session.query(User).filter_by(email=email).first()
            if user:
                if check_password_hash(user.password,password):
                    login_user(user)
                    print(current_user.id)
                    return redirect(url_for('get_all_posts'))
                else:
                    flash('password incorrect please try again', 'error')
                    return redirect(url_for('login'))
            else:
                flash('The email does not exist please try again', 'error')
                return redirect(url_for('login'))
    return render_template("login.html",form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=['GET','POST'])
def show_post(post_id):
    requested_post = db.session.get(BlogPost,post_id)
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        if current_user.is_authenticated:            
            new_comment = Comment(
            text = comment_form.comment_text.data,
            commentor = current_user,
            blogPost = requested_post)
            db.session.add(new_comment)
            db.session.commit() 
            return redirect(url_for('show_post', post_id=post_id))
        else:
            flash('you need to login or register to comment', 'error')
            return redirect(url_for('login'))
    return render_template("post.html", post=requested_post, form=comment_form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post",methods=['GET','POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>",methods=['GET','POST'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
