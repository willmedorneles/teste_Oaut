from flask import Flask
from flask import session, request
from flask import render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_oauthlib.provider import Oauth1Provider

app = Flask(__name__, template_folder='templates')
app.debug = True
app.secret_key = 'secret'
app.config.update({
    'SQLALCHEMY_DATABASE_URI':'sqlite:///db.sqlite',
    'OAUTH1_PROVIDER_ENFORCE_SSL': False,
    'OAUTH1_PROVIDER_KEY_LENGTH' : (10, 100),
})
db = SQLAlchemy(app)
oauth = Oauth1Provider(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True)

class Client(db.Model):
    client_key = db.Column(db.String(40), primary_key=True)
    clienr_secret = db.Column(db.String(55), index=True, nullable=False)

    #creator of the client
    user_id = db.Column(db.ForeignKey('user.id'))
    user = db.relationship('User')
    _realms = db.Column(db.Text)
    _redirect_uris = db.Column(db.Text)

    @property
    def redirect_uris(self):
        if self._redirect_uris:
            return self._redirect_uris.split()
        return []

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]

    @property
    def default_realms(self):
        if self._realms:
            return self._realms.split()
        return []

class RequestToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE')
    )
    user = db.relationship('User')

    client_key = db.Column(
        db.String(40), db.ForeignKey('client.client_key'),
        nullable=False,
    )

    client = db.relationship('Client')
    
    token = db.Column(db.String(225), index=True, unique=True)
    secret = db.Column(db.String(225), nullable=False)

    verifier = db.Column(db.String(225))

    redirect_uri = db.Column(db.Text)
    _realms = db.Column(db.Text)

    @property
    def realms(self):
        if self._realms:
            return self._realms.split()
        return []

    

def current_user():
    if 'id' in session:
        uid = session['id']
        return User.query.get(uid)
    return None

@app.route('/', methods=('GET', 'POST'))
def home():
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        session['id'] = user.id
        return redirect('/')
    user = current_user()
    return render_template('home.html', user=user)

@app.route('/client')
def client():
    user = current_user()
    if not user:
        return redirect('/')
    item = Client(
        client_key=gen_salt(40),
        client_secret=gen_salt(50),
        user_id = user.id
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(
        client_key=item.client_key,
        client_secret=item.client_secret
    )
@oauth.clientgetter
def load_client(client_key):
    return Client.query.filter_by(client_key=client_key).first()

@oauth.grantgetter
def load_request_token(token):
    return RequestToken.query.filter_by(token=token).first()



if __name__ == '__main__':
    db.create_all()
    app.run()