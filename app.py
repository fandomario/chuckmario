import requests
import sqlite3

from flask import Flask, render_template, request
from peewee import BooleanField, CharField, IntegerField, IntegrityError, ForeignKeyField, Model, PostgresqlDatabase, SqliteDatabase

# import private


# db = PostgresqlDatabase(
#   private.DATABASE,
#   user=private.USER,
#   password=private.PASSWORD,
#   host=private.HOST,
#   port=private.PORT,
# )
#

db = SqliteDatabase('chuck.db')


class BaseModel(Model):
    class Meta:
        database = db


class Jokes(BaseModel):
    category = CharField()
    joke = CharField(unique=True)

    class Meta:
        table_name = 'jokes'

class Users(BaseModel):
    username = CharField(unique=True)
    password = CharField()
    email = CharField(unique=True)
    is_loggedin = BooleanField(default=False)

    class Meta:
        table_name = 'users'


class JokesUsers(BaseModel):
    user_id = ForeignKeyField(Users)
    joke_id = ForeignKeyField(Jokes)

    class Meta:
        table_name = 'jokes_users'


TABLES = [
    Jokes, JokesUsers, Users
]

with db.connection_context():
    db.create_tables(TABLES, safe=True)
    db.commit()


app = Flask(__name__)


first_options_list = "animal, career, celebrity, dev, explicit, fashion, food, history, money, movie, music, political, religion, science, sport, travel"


@app.before_request
def _db_connect():
    db.connect()


@app.teardown_request
def _db_close(_):
    if not db.is_closed():
        db.close()


@app.route('/', methods=['GET'])
def login():
    try:
        if request.method == "GET":
            email = request.args.get("Email")
            if not email:
                return render_template('index.html')
            password = request.args.get("Password")
            result = Users.select(Users.id).where((Users.email == email) & (Users.password == password)).get()
            result.is_loggedin = True
            result.save()
            return render_template('index.html', result=result, message = "")
    except:
        return render_template('index.html', message = "No such user. Please sign up")


@app.route('/jokes')
def jokes():
    category = request.args.get('category')
    if not category:
        return render_template('jokes.html', categories=first_options_list)
    options_list = requests.get('https://api.chucknorris.io/jokes/categories')
    options_list = options_list.json()
    options_list = ', '.join(options_list)
    if category not in options_list:
        return render_template('jokes.html', categories=options_list, wrong="Choose another")
    the_joke = requests.get(f'https://api.chucknorris.io/jokes/random?category={category}').json()
    joke = the_joke['value']
    try:
        Jokes.create(category=category, joke=joke)
        joke_id = Jokes.select(Jokes.id).order_by(Jokes.id.desc()).limit(1).get()
        logged_id = Users.select(Users.id).where(Users.is_loggedin == True).get()
        JokesUsers.create(user_id=logged_id, joke_id=joke_id)
    except IntegrityError:
        pass
    return render_template(
        'jokes.html',
        categories=options_list,
        category=category,
        joke=joke,
    )


@app.route('/userjokes')
def userjokes():
    jokes = (Jokes.select().join(JokesUsers, on=(JokesUsers.joke_id == Jokes.id)).join(Users, on=(Users.id == JokesUsers.user_id)).where(Users.is_loggedin == 'True').order_by(Jokes.category))
    return render_template('userjokes.html', joke=jokes)


@app.route('/deletejokes')
def deletejokes():
    to_delete = Jokes.select(Jokes.id).order_by(Jokes.id).limit(1).get()
    to_delete.delete_instance()
    to_delete.save()
    message = "DELETED HA HA HA!"
    return render_template('deletejokes.html', message=message)


@app.route('/adduserpage', methods=['POST', 'GET'])
def adduserpage():
    if request.method == "POST":
        username = request.form["Username"]
        password = request.form["Password"]
        email = request.form["Email"]
        try:
            Users.create(username=username, password=password, email=email)
        except IntegrityError:
            return render_template('adduserpage.html', username = username, message="username exist, Please try another")
        result = True
        return render_template('adduserpage.html', result=result, username = username, message="added successfully")
    else:
        return render_template('adduserpage.html', username = "", message="")


@app.route('/logout')
def logout():
    logged_id = Users.select(Users.id).where(Users.is_loggedin == True).get()
    logged_id.is_loggedin = False
    logged_id.save()
    return render_template('logout.html')


if __name__ == '__main__':
    app.run(debug=True)