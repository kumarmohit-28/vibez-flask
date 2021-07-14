import re
from flask import render_template,request,redirect,url_for,flash,Flask,session
from flask_toastr import Toastr
from flask_mysqldb import MySQL
from flask_mail import Mail,Message
import random
import os
from passlib.hash import sha256_crypt
from werkzeug.utils import secure_filename
from PIL import Image
#flask
app=Flask('__name__')
#toaster

toastr = Toastr(app)
app.secret_key="qwertyuiopasdfghjklzxcvbnm"

#mysql databse
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'vibez'
mysql=MySQL(app)


#mail

app.config.update(
    DEBUG=True,
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME='cs207hostelproject@gmail.com',
    MAIL_PASSWORD='cs207dbms'
)

mail=Mail(app)


@app.before_first_request
def init_app():
    session['logged_in']=False
    session['otpverify']=False
    session['signup'] = False



def send_otp(reciver,otp):
    msg=Message('OTP',
                sender='cs207hostelproject@gmail.com',
                recipients=[reciver])
    msg.body="Here is your one time password :"+str(otp)
    mail.send(msg)
    flash('otp sent succesfully please validate')
    return

@app.route('/',methods=['GET','POST'])
def home():
    if 'logged_in' in session and not session['logged_in']:
        flash('Please login first')
        return redirect(url_for('login'))
    cur=mysql.connection.cursor()
    x=cur.execute('SELECT * FROM users')
    l=[]
    if x>0:
        z=cur.fetchall()
        for p in z:
            l.append(p[0])
    # print(l)
    l.remove(session['username'])

    cur=mysql.connection.cursor()
    x=cur.execute('select * from followers where usern=%s',(session['username'],))
    foll=cur.fetchall()
    cur.close()
    d={}
    for p in foll:
        cur=mysql.connection.cursor()
        x=cur.execute('select name from users where username=%s',(p[2],))
        foll1=cur.fetchone()
        d[p[2]]=foll1[0]
        cur.close()
    
    
    if request.method=='POST':
        user=request.form.get('inputsearch')
        return redirect(url_for('profile',username=user))
    return render_template('home.html',items=l,foll=d)

@app.route('/login',methods=["GET","POST"])
def login():
    if session['logged_in']:
        return redirect(url_for('home'))
    if request.method=='POST':
        if request.form.get('login')=='True':
            
            username=request.form.get('username')
            password=request.form.get('password')
            cur1=mysql.connection.cursor()
            x=cur1.execute("SELECT * FROM users WHERE username=%s",(username,))
            if (x!=0):
                data=cur1.fetchone()
                if(sha256_crypt.verify(password,data[2])):
                    session['username'] = data[0]
                    session['email']=data[1]
                    session['name']=data[3]
                    session['logged_in']=True
                    flash('Login successfully')
                    return redirect(url_for('home'))
                else:
                    flash('wrong password')
                    return render_template('login.html')
            else:
                flash('user not registered')
                return render_template('login.html')
        else:
            if str(request.form.get('checkbox'))=='None':
                flash('please accept terms and conditions')
                return redirect(url_for('login'))
            name=request.form.get('name')
            username=request.form.get('username')
            password=request.form.get('password')
            email=request.form.get('email')


            cur=mysql.connection.cursor()
            x=cur.execute("SELECT * FROM users WHERE username=(%s)",(username,))
            x1=cur.execute("SELECT * FROM users WHERE email=(%s)",(email,))
            if x>0 or x1>0:
                flash('Username or Email already exist !!')
                return redirect(url_for('login'))
            cur.close()
            x1=random.randrange(111111,999999)
            send_otp(email,x1)
            session['name']=name
            session['username'] = username
            session['email'] = email
            session['password'] = password
            session['otp']=x1
            session['otpverify'] = False
            session['signup'] = True
            return redirect(url_for('otpverify'))

    return render_template('login.html')

@app.route('/logout',methods=['GET','POST'])
def logout():
    session['logged_in']=False
    session['otpverify']=False
    session['signup'] = False
    flash('logout successfull')
    return redirect(url_for('login'))


@app.route('/otpverify',methods=['GET','POST'])
def otpverify():
    if('logged_in' in session and session['logged_in']==True):
        return redirect(url_for('home'))
    if ('signup' in session and session['signup'] == False):
        flash('PLEASE SIGNUP FIRST')
        return redirect(url_for('login'))
    if request.method=='POST':
        otp=request.form.get('otp')
        if int(otp)!=session['otp']:
            flash('Otp incorrect')
            return redirect(url_for('otpverify'))
        session['otpverify']=True
        session['signup'] = True
        cur=mysql.connection.cursor()
        password = sha256_crypt.encrypt(session['password'])
        cur.execute("INSERT INTO users(username,email,password,name) VALUES(%s,%s,%s,%s)", (session['username'],session['email'],password,session['name']))
        mysql.connection.commit()
        cur.close()
        session['logged_in'] = True
        flash('Signup successfull')
        return redirect(url_for('home'))
    return render_template('otpverify.html')

@app.route('/forget-password',methods=['GET','POST'])
def forgotpassword():
    if session['logged_in']:
        flash('You are already logged in')
        return redirect(url_for('home'))
    if request.method=='POST':
        email=request.form.get('email')
        cur1=mysql.connection.cursor()
        x=cur1.execute("SELECT * FROM users WHERE email=%s",(email,))
        cur1.close()
        if x==0:
            flash("Email not registered")
            return redirect(url_for('forgotpassword'))
        x1=random.randrange(111111,999999)
        send_otp(email,x1)
        session['otp']=x1
        session['otpverify']=False
        return redirect(url_for('verifyotppass',email=email))
    return render_template('forgotpassword.html')

@app.route('/verify-otp/<email>',methods=['GET','POST'])
def verifyotppass(email):
    if 'otpverify' not in session or not session['otpverify']:
        flash('Enter email for otp')
        return redirect(url_for('forgotpassword'))
    if request.method=='POST':
        otp=request.form.get('otp')
        if int(otp)!=session['otp']:
            flash('Otp incorrect')
            return redirect(url_for('verifyotppass',email=email))
        session['otpverify']=True
        return redirect(url_for('newpassword',email=email))
    return render_template('verifyotppass.html')

@app.route('/new-password/<email>',methods=["GET",'POST'])
def newpassword(email):
    if session['otpverify']==False:
        flash('Verify otp first')
        return redirect(url_for('verifyotppass',email=email))
    if request.method=='POST':
        password=request.form.get('password')
        cnfpassword=request.form.get('cnfpassword')
        if password !=cnfpassword:
            flash('both password did not match')
            return redirect(url_for('newpassword',email=email))
        password = sha256_crypt.encrypt(password)
        cur=mysql.connection.cursor()
        cur.execute('UPDATE users SET password=%s WHERE email=%s',(password,email))
        mysql.connection.commit()
        cur.close()
        flash('password changed succesfully please login')
        return redirect(url_for('login'))
    return render_template('newpassword.html')

@app.route('/profile/<username>',methods=['GET','POST'])
def profile(username):
    # if 'logged_in' in session and not session['logged_in']:
    #     return redirect(url_for('home'))
    cur=mysql.connection.cursor()
    x=cur.execute('select * from users where username=%s',(username,))
    if x==0:
        flash('No user exist with the username')
        return redirect(url_for('home'))
    item=cur.fetchone()
    cur.close()

    cur=mysql.connection.cursor()
    x=cur.execute('select * from followers where usern=%s',(username,))
    foll=cur.fetchall()
    cur.close()
    d={}
    for p in foll:
        cur=mysql.connection.cursor()
        x=cur.execute('select name from users where username=%s',(p[2],))
        foll1=cur.fetchone()
        d[p[2]]=foll1[0]
        cur.close()

    #followings
    cur=mysql.connection.cursor()
    x=cur.execute('select * from followings where usern=%s',(username,))
    foll=cur.fetchall()
    cur.close()
    d1={}
    for p in foll:
        cur=mysql.connection.cursor()
        x=cur.execute('select name from users where username=%s',(p[2],))
        foll1=cur.fetchone()
        d1[p[2]]=foll1[0]
        cur.close()
    print(d)
    print(d1)
    return render_template('profile.html',items=item,foll=d,follwing=d1)

@app.route('/createpost',methods=['GET','POST'])
def createpost():
    if 'logged_in' in session and not session['logged_in']:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        des=request.form.get('des')
        cur=mysql.connection.cursor()
        file = request.files['file']
        if (file and file.filename != ''):
                    l=file.filename.split('.')
                    file.filename = str(session['username']) +'1'+'.'+str(l[-1])
                    filename = secure_filename(file.filename)
                    file.save(os.path.join('C:\\Users\\kumar\\Desktop\\vibez-flask\\static\\images\\post', filename))
                    s='C:\\Users\\kumar\\Desktop\\vibez-flask\\static\\images\\post\\'+str(filename)
                    img1=Image.open(s)
                    img2=img1.convert('RGB')
                    s = 'C:\\Users\\kumar\\Desktop\\vibez-flask\\static\\images\\post\\' + str(session['username'])+'.jpg'
                    img2.save(s)
                    os.remove(os.path.join('C:\\Users\\kumar\\Desktop\\vibez-flask\\static\\images\\post', filename))









    cur=mysql.connection.cursor()
    x=cur.execute('select * from users where username=%s',(session['username'],))
    if x==0:
        flash('No user exist with the username')
        return redirect(url_for('home'))
    item=cur.fetchone()
    cur.close()

    cur=mysql.connection.cursor()
    x=cur.execute('select * from followers where usern=%s',(session['username'],))
    foll=cur.fetchall()
    cur.close()
    d={}
    for p in foll:
        cur=mysql.connection.cursor()
        x=cur.execute('select name from users where username=%s',(p[2],))
        foll1=cur.fetchone()
        d[p[2]]=foll1[0]
        cur.close()
    
    #followings
    cur=mysql.connection.cursor()
    x=cur.execute('select * from followings where usern=%s',((session['username'],)))
    foll=cur.fetchall()
    cur.close()
    d1={}
    for p in foll:
        cur=mysql.connection.cursor()
        x=cur.execute('select name from users where username=%s',(p[2],))
        foll1=cur.fetchone()
        d1[p[2]]=foll1[0]
        cur.close()
    
    return render_template('createpost.html',items=item,foll=d,follwing=d1)

@app.route('/profile/<username>/followers',methods=['GET','POST'])
def followers(username):

    #user detials
    cur=mysql.connection.cursor()
    x=cur.execute('select * from users where username=%s',(username,))
    if x==0:
        flash('No user exist with the username')
        return redirect(url_for('home'))
    item=cur.fetchone()
    cur.close()

    #followers
    cur=mysql.connection.cursor()
    x=cur.execute('select * from followers where usern=%s',(username,))
    foll=cur.fetchall()
    cur.close()
    d={}
    for p in foll:
        cur=mysql.connection.cursor()
        x=cur.execute('select name from users where username=%s',(p[2],))
        foll1=cur.fetchone()
        d[p[2]]=foll1[0]
        cur.close()
    
    #followings
    cur=mysql.connection.cursor()
    x=cur.execute('select * from followings where usern=%s',(username,))
    foll=cur.fetchall()
    cur.close()
    d1={}
    for p in foll:
        cur=mysql.connection.cursor()
        x=cur.execute('select name from users where username=%s',(p[2],))
        foll1=cur.fetchone()
        d1[p[2]]=foll1[0]
        cur.close()
    return render_template('followers.html',items=item,foll=d,follwing=d1)

@app.route('/follow/<username>',methods=['GET','POST'])
def follow(username):
    if 'logged_in' in session and not session['logged_in']:
        return redirect(url_for('home'))
    cur=mysql.connection.cursor()
    print(username,session['username'])
    cur.execute('Insert into followers(usern,followern) values(%s,%s)',(username,session['username']))
    cur.execute('Insert into followings(usern,followern) values(%s,%s)',(session['username'],username))
    
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('profile',username=session['username']))
@app.route('/unfollow/<username>',methods=['GET','POST'])
def unfollow(username):
    if 'logged_in' in session and not session['logged_in']:
        return redirect(url_for('home'))
    cur=mysql.connection.cursor()
    print(username,session['username'])
    cur.execute('delete from followers where usern=%s and followern=%s',(username,session['username']))
    cur.execute('delete from followings where usern=%s and followern=%s',(username,session['username']))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('profile',username=session['username']))
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")
app.run(debug=True)