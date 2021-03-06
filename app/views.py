from app import app, db, lm, mail
from flask import render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from .forms import LoginForm, EditForm
from .models import User
import hashlib
from datetime import datetime
from flask.ext.mail import Mail, Message
from config import ADMINS

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.route('/send_email')
def send_email(text):
#    return mail.username + " | " + mail.password + " | "
#    return mail.server
    if not text:
      text = 'test_subject'
    msg = Message(text , sender=ADMINS[0], recipients=ADMINS)
    msg.body = 'text body'
    msg.html = '<b>HTML</b> body'
    mail.send(msg)
    return "Email sended!"

@app.before_request
def before_request():
    g.user = current_user
    if g.user.is_authenticated:
        g.user.last_seen = datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()

@app.route('/') 
@app.route('/index') 
@login_required
def index():
    user = g.user
    posts = [{'author': {'nickname':'John'},
              'body': 'beautiful day in portland!'},
             {'author': {'nickname':'Susan'},
              'body': 'the avengers movie was so cool!'}]
    return render_template('index.html', user=user, posts=posts)

@app.route('/user/<nickname>')
@login_required
def user(nickname):
    user = User.query.filter_by(nickname=nickname).first()
    if user == None:
        flash('User %s not found.' % nickname)
        return redirect(url_for('index'))
    posts = [
        {'author': user, 'body':'Test post #1'},
        {'author': user, 'body':'Test post #2'},
    ]
    return render_template('user.html', user=user, posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        session['remember_me'] = form.remember_me.data
        session['email'] = form.email.data
        if 'email' in session:
            email = session['email']
            if email is not None and email != '':
                return afterLogin(email)
        else:
           return 'no email'
                
    return render_template('login.html', title='Sign In', form=form, providers=app.config['OPENID_PROVIDERS'])

def checkUser(email):
    user = User.query.filter_by(email=email).first()
    if user is None:
        nickname = email.split('@')[0]
        session['nickname'] = nickname
        nickname = User.make_unique_nickname(nickname)
        user = User(nickname=nickname, email=email)
        db.session.add(user)
        db.session.commit()
	# make the user follow him/herself
	db.session.add(user.follow(user))
	db.session.commit()
    return user

def afterLogin(email):
    remember_me = False
    if 'remember_me' in session:
        remember_me = session['remember_me']
        session.pop('remember_me', None)
    user = checkUser(email)
    if user is not None:
        login_user(user, remember = remember_me)
    return redirect(request.args.get('next') or url_for('index'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# @oid.after_login
def after_login(resp):
    # resp.email = 'malong5219@gmail.com'
    if resp.email is None or resp.email == "":
        flash('Invalid login. Please try again.')
        return redirect(url_for('login'))
    user = User.query.filter_by(email=resp.email).first()
    if user is None:
        nickname = resp.nickname
        if nickname is None or nickname == "":
            nickname = resp.email.split('@')[0]
        user = User(nickname=nickname, email=resp.email)
        db.session.add(user)
        db.session.commit()
        # make the user follow him/herself
        db.session.add(user.follow(user))
        db.session.commit()
    remember_me = False
    if 'remember_me' in session:
        remember_me = session['remember_me']
        session.pop('remember_me', None)
    login_user(user, remember = remember_me)
    return redirect(request.args.get('next') or url_for('index'))

@app.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    form = EditForm(g.user.nickname)
    if form.validate_on_submit():
        g.user.nickname = form.nickname.data
        g.user.about_me = form.about_me.data
        db.session.add(g.user)
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit'))
    else:
        form.nickname.data = g.user.nickname
        form.about_me.data = g.user.about_me
    return render_template('edit.html', form=form)

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/follow/<nickname>')
def follow(nickname):
    user = User.query.filter_by(nickname = nickname).first()
    if user == None:
      flash('User ' + nickname + ' not found.')
      return redirect(url_for('index'))
    if user == g.user:
      flash("You can't follow yourself")
      return redirect(url_for('user', nickname=nickname))
    u = g.user.follow(user)
    if u is None:
        flash('Cannot follow' + nickname + '.')
        return redirect(url_for('user', nickname=nickname))
    db.session.add(u)
    db.session.commit()
    flash('You are now following ' + nickname + '!')
    return redirect(url_for('user', nickname=nickname))

@app.route('/unfollow/<nickname>')
@login_required
def unfollow(nickname):
    user = User.query.filter_by(nickname=nickname).first()
    if user is None:
        flash('User %s not found' % nickname)
        return redirect(url_for('index'))
    if user == g.user:
        flash('You cannot follow your slef')
        return redirect(url_for('user', nickname=nickname))
    u = g.user.unfollow(user)
    if u is None:
        flash('Cannot unfollow ' + nickname + '.')
        return redirect(url_for('user', nickname=nickname))
    db.session.add(u)
    db.session.commit()
    flash('You have stopped following ' + nickname + '.')
    return redirect(url_for('user', nickname=nickname))

