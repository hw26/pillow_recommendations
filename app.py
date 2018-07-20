from flask import Flask, render_template, flash, redirect, url_for, session, request, logging, jsonify
from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, SelectField,BooleanField,validators
from passlib.hash import sha256_crypt
from functools import wraps
import pandas as pd



app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '19901999'
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)

#Articles = Articles()

# Index
@app.route('/')
def index():
    return render_template('home.html')


# About
@app.route('/about')
def about():
    return render_template('about.html')


# Articles
@app.route('/articles')
def articles():
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
    # Close connection
    cur.close()


#Single Article
@app.route('/article/<string:id>/')
def article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    article = cur.fetchone()

    return render_template('article.html', article=article)


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
    style_type = SelectField('Your Muse Type', choices=[('Vincent Van Duysen',"Vincent Van Duysen"),('Sarah Sherman Samuel','Sarah Sherman Samuel'),('Design Love Fest','Design Love Fest'),('Eyeswoon','Eyeswoon'),('Cocolapine','Cocolapine') ,('Joanna Gaines', 'Joanna Gaines'),('Bjarke Ingels','Bjarke Ingels'),('Mountain Vibes','Mountain Vibes')])




# Register Form Class
class PillowsForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    likeit = BooleanField('I like it!')

# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():

    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
        style_type = form.style_type.data

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute("INSERT INTO users1(name, email, username, password,style_type) VALUES(%s, %s, %s, %s, %s)", (name, email, username, password,style_type))

        cur.execute("INSERT INTO user_preferences (pillow_id) SELECT idx from pillows_dataset")

        cur.execute("UPDATE user_preferences SET username = %s WHERE username is null",[name])



        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    # print(request.form)
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users1 WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    

    return render_template('dashboard.html')

# Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])


# Display favorite pillow collections
@app.route('/display_favorites', methods=['GET', 'POST'])
@is_logged_in
def display_favorites():
    cur = mysql.connection.cursor()

    res = cur.execute("SELECT pillow_id from user_preferences where username = %s and isliked", [session['username']])


    preferences = cur.fetchall()

    if res > 0:
        preferences = [i['pillow_id'] for i in preferences]
        format_strings = ','.join(['%s'] * len(preferences))

        nnew_cur = mysql.connection.cursor()
        result = nnew_cur.execute("select idx,title,img,price from pillows_dataset where idx in (%s)" 
        %format_strings,tuple(preferences)) 
        pictures = nnew_cur.fetchall()

        return render_template('display_favorites.html', pictures=pictures)
    else:
        msg = 'No Pillows Found'
        return render_template('display_favorites.html', msg=msg)
    # Close connection
    cur.close()







# present recommendations
@app.route('/recommendations', methods=['GET', 'POST'])
@is_logged_in

def display_recommendations():

    
    initial_preferences_cur = mysql.connection.cursor()

    initial_preferences_res = initial_preferences_cur.execute("SELECT pillow_id from user_preferences where username = %s and isliked", [session['username']])
    initial_preferences = initial_preferences_cur.fetchall()
    initial_preferences = set([i['pillow_id'] for i in initial_preferences])

    ## pillows that the user has made a choice
    initial_choices_cur = mysql.connection.cursor()
    initial_choices_res = initial_choices_cur.execute("SELECT pillow_id from user_preferences where username = %s and choice_made", [session['username']])
    initial_choices = initial_choices_cur.fetchall()
    initial_choices = set([i['pillow_id'] for i in initial_choices])

    ## old recurring users based on user preferences(selected pillows)
    if initial_preferences_res > 0:

        # likes = request.form.getlist('like')
        # nopes = request.form.getlist('nope')
        # choices_made =  likes + nopes

        # # format_strings_likes = format_strings(likes)
        # # format_strings_nopes = format_strings(nopes)
        # # format_strings_choices_made = format_strings(choices_made)

        # format_strings_likes = ','.join(['%s'] * len(likes))
        # format_strings_nopes = ','.join(['%s'] * len(nopes))
        # format_strings_choices_made = ','.join(['%s'] * len(choices_made))


        # ### update user database
        # update_user_cur = mysql.connection.cursor()
        # # update_user_cur.execute("UPDATE user_preferences SET isliked = 1 WHERE username = %s and pillow_id in (%s)"%format_strings_likes,[session['username'],tuple(likes)])
        # # update_user_cur.execute("UPDATE user_preferences SET choice_made = 1 WHERE username = %s and pillow_id in (%s)"%format_strings_choices_made,[session['username'],tuple(choices_made)])
        # for ii in likes:
        #     update_user_cur.execute("UPDATE user_preferences SET isliked = 1 WHERE username = %s and pillow_id = %s",[session['username'],ii])
        # for jj in choices_made:    
        #     update_user_cur.execute("UPDATE user_preferences SET choice_made = 1 WHERE username = %s and pillow_id = %s",[session['username'],jj])

        # mysql.connection.commit()
        # update_user_cur.close()






        top_sims_cur = mysql.connection.cursor()

        format_strings = ','.join(['%s'] * len(initial_preferences))

        top_sims_res = top_sims_cur.execute("with pillow_sim_scores_with_preferences as \
            (SELECT pillow_id_i,pillow_id_j,similarity_score,choice_made FROM similarity_matrix inner join user_preferences on \
            user_preferences.pillow_id = similarity_matrix.pillow_id_i\
            where pillow_id_i in (%s) order by similarity_score desc) \
            select pillow_id_j,similarity_score,choice_made from pillow_sim_scores_with_preferences"%format_strings,tuple(initial_preferences))


        allpillow = top_sims_cur.fetchall()
        # print(allpillow)
        top_sims = []

        for kk in allpillow:
            if kk['pillow_id_j'] not in top_sims and kk['pillow_id_j'] not in initial_choices:
                top_sims.append(kk['pillow_id_j'])
        # print(top_sims)
        top_sims = top_sims[:10]

       
        top_sims_cur.close()

        new_cur = mysql.connection.cursor()

        format_strings_sims = ','.join(['%s'] * len(top_sims))



        result = new_cur.execute("select idx,title,img,price from pillows_dataset where idx in (%s)" 
        %format_strings_sims,tuple(top_sims)) 

        pictures = new_cur.fetchall()
        # print("from old user with preferences already")
        
        
        return render_template('display_recommendations.html', pictures=pictures)
    
    ## new users recommendations based on style quiz result(muse type)
    else:


        style_type_cur = mysql.connection.cursor()
        style_type = style_type_cur.execute("SELECT style_type FROM users1 where username = %s",[session['username']])
        style_type = style_type_cur.fetchall()[0]['style_type']

        style_type_cur.close()


        print("from new login user without preferences")



        new_cur = mysql.connection.cursor()

        # Get articles
        result = new_cur.execute("with db1 as (SELECT pillow_id FROM style_pillows_dataset \
             where style_type = %s ORDER BY confidence_score desc LIMIT 10)\
                select idx,title,img,price from db1 inner join \
                pillows_dataset on idx = db1.pillow_id",[style_type])


        pictures = new_cur.fetchall()
        new_cur.close()
        return render_template('display_recommendations.html', pictures=pictures)

        # if not choices_made: 
        #     return render_template('display_recommendations.html', pictures=pictures)


        # format_strings_likes = format_strings(likes)
        # format_strings_nopes = format_strings(nopes)
        # format_strings_choices_made = format_strings(choices_made)

        # format_strings_likes = ','.join(['%s'] * len(likes))
        # format_strings_nopes = ','.join(['%s'] * len(nopes))
        # format_strings_choices_made = ','.join(['%s'] * len(choices_made))

        # format_strings_likes = str('('+str(','.join(likes))+')')
        # format_strings_nopes = ','.join(nopes)
        # format_strings_choices_made = str('('+str(','.join(choices_made))+')')




        ### update user dataset
        # update_user_cur2 = mysql.connection.cursor()
        # # update_user_cur.execute("UPDATE user_preferences SET isliked = 1 WHERE username = %s and pillow_id in (%s)"%format_strings_likes,tuple(session['username'],likes))
        # # update_user_cur.execute("UPDATE user_preferences SET choice_made = 1 WHERE username = %s and pillow_id in (%s)"%format_strings_choices_made,tuple(session['username'],likes))
        # for ii in likes:
        #     update_user_cur2.execute("UPDATE user_preferences SET isliked = 1 WHERE username = %s and pillow_id = %s",[session['username'],ii])
        # for jj in choices_made:    
        #     update_user_cur2.execute("UPDATE user_preferences SET choice_made = 1 WHERE username = %s and pillow_id = %s",[session['username'],jj])

        # # update_user_cur.execute("UPDATE user_preferences SET isliked = 1 WHERE username = %s and pillow_id as varchar(10)) in " + "%s",[session['username'],format_strings_likes])
        # # update_user_cur.execute("UPDATE user_preferences SET choice_made = 1 WHERE username = %s and pillow_id in "+ "%s",[session['username'],format_strings_choices_made])
        

        # ### update pillow vsstyle dataset
        # for ii in likes:
        #     update_user_cur2.execute("UPDATE style_pillows_dataset SET confidence_score = confidence_score + 1 WHERE style_type = %s and pillow_id = %s",[style_type,ii])
        # for jj in nopes:    
        #     update_user_cur2.execute("UPDATE style_pillows_dataset SET confidence_score = confidence_score - 1 where style_type = %s and pillow_id = %s",[style_type,jj])

        # # Commit to DB
        # mysql.connection.commit()
        # update_user_cur2.close()

        


def format_strings(str):
    formatted_str = ','.join(['%s'] * len(str))
    return formatted_str

# Delete Favorited Pillows
@app.route('/delete_pillow/<string:id>', methods=['POST'])
@is_logged_in
def delete_pillow(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("UPDATE user_preferences SET isliked = 0 and choice_made = 1 WHERE username = %s and pillow_id = %s" ,[session['username'],id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Pillow Deleted', 'success')

    return redirect(url_for('display_favorites'))

@app.route('/submit_choices/', methods=['GET', 'POST'])
@is_logged_in
def submit_choices():
    # Create cursor
    style_type_cur = mysql.connection.cursor()
    style_type = style_type_cur.execute("SELECT style_type FROM users1 where username = %s",[session['username']])
    style_type = style_type_cur.fetchall()[0]['style_type']
    style_type_cur.close()


    likes = request.form.getlist('like')
    nopes = request.form.getlist('nope')
    choices_made =  likes + nopes




    ## update user dataset
    update_user_cur2 = mysql.connection.cursor()
    # update_user_cur.execute("UPDATE user_preferences SET isliked = 1 WHERE username = %s and pillow_id in (%s)"%format_strings_likes,tuple(session['username'],likes))
    # update_user_cur.execute("UPDATE user_preferences SET choice_made = 1 WHERE username = %s and pillow_id in (%s)"%format_strings_choices_made,tuple(session['username'],likes))
    for ii in likes:
        update_user_cur2.execute("UPDATE user_preferences SET isliked = 1 WHERE username = %s and pillow_id = %s",[session['username'],ii])
    for jj in choices_made:    
        update_user_cur2.execute("UPDATE user_preferences SET choice_made = 1 WHERE username = %s and pillow_id = %s",[session['username'],jj])

    # update_user_cur.execute("UPDATE user_preferences SET isliked = 1 WHERE username = %s and pillow_id as varchar(10)) in " + "%s",[session['username'],format_strings_likes])
    # update_user_cur.execute("UPDATE user_preferences SET choice_made = 1 WHERE username = %s and pillow_id in "+ "%s",[session['username'],format_strings_choices_made])
    

    ### update pillow vs style dataset
    for ii in likes:
        update_user_cur2.execute("UPDATE style_pillows_dataset SET confidence_score = confidence_score + 1 WHERE style_type = %s and pillow_id = %s",[style_type,ii])
    for jj in nopes:    
        update_user_cur2.execute("UPDATE style_pillows_dataset SET confidence_score = confidence_score - 1 where style_type = %s and pillow_id = %s",[style_type,jj])

    # Commit to DB
    mysql.connection.commit()
    update_user_cur2.close()
    return render_template("submit_choices.html")







if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)



