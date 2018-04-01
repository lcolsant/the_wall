from flask import Flask, request, redirect, render_template, flash, session
from mysqlconnection import MySQLConnector
import md5
import os, binascii 
import re
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')

app = Flask(__name__)
mysql = MySQLConnector(app,'the_wall')
app.secret_key = 'secretKey'

@app.route('/')
def index():
    if 'id' in session.keys():
        return redirect('/wall')
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def create():

    if '_flashes' in session:
        session.pop('_flashes', None)
    
    errors = 0

    if len(request.form['fname']) < 3:
        flash('First name must be at least 2 characters!')
        errors+=1
    elif not request.form['fname'].isalpha():
        flash("First name should be alpha only")
        errors+=1
    else:
        fname = request.form['fname']
    if len(request.form['lname']) < 3:
        flash('Last name must be at least 2 characters!')
        errors+=1
    elif not request.form['lname'].isalpha():
        flash("First name should be alpha only")
        errors+=1
    else:
        lname = request.form['lname']
    if len(request.form['email']) < 1:
        flash('Email cannot be empty!')
        errors+=1
    elif not EMAIL_REGEX.match(request.form['email']):
        flash('Invalid Email Address!')
        errors+=1
    else:
        email = request.form['email']
    if len(request.form['pass']) < 8:
        flash('Password should be at least 8 characters!')
        errors+=1
    else:
        password = request.form['pass']
        salt = binascii.b2a_hex(os.urandom(15))
        hashed_pw = md5.new(password + salt).hexdigest()        
    if len(request.form['pass_confirm']) < 8:
        flash('Password confirm should be at least 8 characters!')
        errors+=1
    else:
        pass_confirm = request.form['pass_confirm']
    
    if request.form['pass'] != request.form['pass_confirm']:
        flash('Password does not match password confirmation')
        errors+=1

    if errors > 0:
        print "Number of errors:",errors
        return redirect('/')
    else:
        session['fname'] = fname
        session['lname'] = lname
        session['email'] = email
        session['pass'] = hashed_pw
        query = 'INSERT INTO `the_wall`.`users` (`first_name`, `last_name`, `email`, `password`, `salt`, `created_at`, `updated_at`) VALUES (:fname, :lname, :email, :pass, :salt, NOW(), NOW() );'

        # create a dictionary of data from the POST data received.
        data = {
                'fname': session['fname'],
                'lname': session['lname'],
                'email': session['email'],
                'pass': session['pass'],
                'salt': salt,

            }
        # Run query, with dictionary values injected into the query.
        mysql.query_db(query, data)
        flash('Registered successfully. Please login')

    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    
    email = request.form['email']
    password = request.form['pass']
    query = 'SELECT * FROM users WHERE email=:email'
    data = {
            'email': email,

        }
    user = mysql.query_db(query, data)
    if len(user) == 0:
        flash("User not recognized")
        return redirect('/')
    else:
        encrypted_password = md5.new(password + user[0]['salt']).hexdigest()
        if user[0]['password'] == encrypted_password:
            flash("User logged in")
            session['id'] = user[0]['id']  #set current user id in session
            session['fname'] = user[0]['first_name']
            return redirect('/wall')
        else:
            flash("Invalid password.")
            return redirect('/')

@app.route('/wall')
def wall():
    
    query = 'SELECT concat(users.first_name," ", users.last_name) as Name, messages.message, messages.id, messages.user_id, date_format(messages.created_at,"%M %d, %Y") as Post_Date from users join messages on messages.user_id = users.id order by Post_Date desc'
    post_info = mysql.query_db(query)
    
    query = 'SELECT concat(users.first_name," ", users.last_name) as Name, comments.comment, date_format(comments.created_at,"%M %d, %Y") as Comment_Date, comments.message_id from comments join users on comments.user_id = users.id order by Comment_Date desc;'
    comment_info = mysql.query_db(query)
    
    print post_info
    
    return render_template('wall.html',post_data=post_info,comment_data=comment_info)

@app.route('/message',methods=['POST'])
def message_():
    message = request.form['message']
    print 'new message:', message
    query = 'INSERT INTO `the_wall`.`messages` (`user_id`, `message`, `created_at`, `updated_at`) VALUES (:user_id, :message, now(), now() );'   
    data = {
            'user_id': session['id'],
            'message': message,

        }

    mysql.query_db(query, data)
    flash('Message posted successfully.')

    return redirect('/')

@app.route('/comment',methods=['POST'])
def comment_():
    comment = request.form['comment']
    message_id = request.form['message_ID']
    print 'new comment:', comment
    print 'message_id:', message_id
    query = 'INSERT INTO `the_wall`.`comments` (`message_id`, `user_id`, `comment`, `created_at`, `updated_at`) VALUES (:message_id, :user_id, :comment, now(), now());'    
    data = {
            'message_id': message_id,
            'user_id': session['id'],
            'comment': comment,

        }

    mysql.query_db(query, data)
    flash('Comment posted successfully.')

    return redirect('/wall')    

@app.route('/message/delete/<id>')
def delete_message_(id):
    delete_comments = "DELETE FROM `the_wall`.`comments` WHERE message_id = :id"
    data = {
        'id': id,
    }
    mysql.query_db(delete_comments, data)
    delete_message = "DELETE FROM messages WHERE id = :id"
    mysql.query_db(delete_message, data)

    return redirect('/wall')    

@app.route('/logout')
def logout_():
    session.clear()
    return redirect('/')


app.run(debug=True)