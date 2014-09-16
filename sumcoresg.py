#! /usr/bin/env python

import os
import threading
import datetime
import json
import pickle

import flask
from functools import wraps

import httplib2
from apiclient.discovery import build
from oauth2client.file import Storage
# using Storage for a web app is high undesirable, but used for convenience at the moment
from oauth2client.client import OAuth2WebServerFlow

import util
import thedata
from obj import Event
from app_config import app, db
from db_tables import Account, Figure
from data_collector import collect_data, get_RAW_XML

##################################URL MAPPING##################################
def login_required(f):                                    # used as a decorator
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = util.valid_cookie_val(flask.request.cookies.get('account'))
        if not auth:
            return flask.redirect(flask.url_for("login"))
        return f(*args, **kwargs)
    return decorated

def get_flow():
    flow = OAuth2WebServerFlow(
        client_id=thedata.CLIENT_ID,
        client_secret=thedata.CLIENT_SECRET,
        scope='https://www.googleapis.com/auth/calendar',
        user_agent='sumcoresg/1.0')
    return flow

@app.route('/', methods=["GET"])
def main():
    return flask.redirect('/login')

@app.route('/login/', methods=["GET", "POST"])
def login():
    if flask.request.method == "GET":
        account_cookie = flask.request.cookies.get('account')
        if util.valid_cookie_val(account_cookie):
            return flask.redirect("/report")
        else:
            return flask.render_template("login.html")
    elif flask.request.method == "POST":
        email = flask.request.form.get('email')
        password = flask.request.form.get('password')

        # I think, based on some experiment, checked checkbox will return a
        # unicode empty string, else it's None
        rmbme = flask.request.form.get('rmbme')

        params = dict(email = email, password=password)

        if not util.valid_email(email):
            params['error_email'] = "That's not a valid email."
            return flask.render_template("login.html", **params)
        else:
            emails = fetch_registered_emails()
            if email not in emails:
                params['error_email'] = "This email hasn't been registered yet."
                return flask.render_template("login.html", **params)
            else:
                account = db.session.query(Account).filter(Account.email==email).all()
                account = account[0]
                if not util.correct_password(email, password, account.password):
                    params['error_password'] = "Wrong password."
                    return flask.render_template("login.html", **params)
                else:
                    # Note: account.password is the hashed value
                    if rmbme is None:
                        #### it works here, but too messy about cookie setting
                        #### by different urls
                        cookie_val = util.make_secure_cookie_val(str(account.id))
                        response = flask.make_response(flask.redirect("/report"))
                        response.headers['Set-Cookie'] = 'account={0};Path=/;'.format(cookie_val)
                        return response
                    else:
                        response = set_account_cookie_and_redirect(
                            account.id, "/report")
                        return response

@app.route('/signup/', methods=["GET", "POST"])
def sigup():
    if flask.request.method == "GET":
        return flask.render_template("signup.html")
    elif flask.request.method == "POST":
        have_error = False
        email = flask.request.form.get('email')
        password = flask.request.form.get('password')
        verify = flask.request.form.get('verify')
        secretcode = flask.request.form.get('secretcode')

        params = dict(email = email, password=password,
                      verify = verify, secretcode=secretcode)

        if not util.valid_email(email):
            params['error_email'] = "That's not a valid email."
            have_error = True
        else:
            # Check if this email has been already been registered.
            #### This is ugly! There must be a better way, and maybe cached
            emails = fetch_registered_emails()
            if email in emails:
                params['error_email'] = "This email has already been registered."
                have_error=True

        if not util.valid_password(password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif password != verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not util.valid_secretcode(secretcode):
            params['error_secretcode'] = "secret code is wrong."
            have_error = True

        if have_error:
            return flask.render_template("signup.html", **params)
        else:
            pw_hash = util.make_pw_hash(email, password)
            account = Account(email, pw_hash, datetime.datetime.now())
            db.session.add(account)
            db.session.commit()

            # FYI, url_for("report") will be return "/report", seems I don't
            # need url_for very much
            # u = flask.url_for("report")

            response = set_account_cookie_and_redirect(account.id, "/report")
            return response

@app.route('/logout/', methods=["GET", "POST"])
def logout():
    account_cookie = flask.request.cookies.get('account')
    if account_cookie:
        response = flask.make_response(flask.redirect("/login"))
        response.headers['Set-Cookie'] = 'account=;Path=/;expires=0;'
        return response

@app.route('/report/.json/', methods=["GET"])
@login_required
def report_json():
    if flask.request.method == "GET":
        raw_xml = thedata.MEMC.get("RAW_XML")
        if not raw_xml:
            raw_xml = get_RAW_XML()
        r = json.dumps(raw_xml)
        response = flask.make_response(r)
        response.headers["Content-type"] = "text/plain"
        return response

@app.route('/report/', methods=["GET", "POST"])
@login_required
def report():
    if flask.request.method == "GET":
        reports = thedata.MEMC.get("REPORTS")
        return flask.render_template("report.html", reports=reports)

# note: png_id should better be a string
@app.route('/plot/<png_id>.png/', methods=["GET"])
@login_required
def pomeslab_png(png_id):
    if flask.request.method == "GET":
        # here it is some strange to me, both [0] & [0][0] works for plotting,
        # though [0] returns the object:
        #  <class 'sqlalchemy.util._collections.NamedTuple'>
        png_data = db.session.query(Figure.content).filter(Figure.name == png_id).all()[0]
        if png_data:
            response = flask.make_response(png_data)
            response.headers['Content-Type'] = 'image/png'
        return response

@app.route('/plot/', methods=["GET"])
def plot():
    if flask.request.method == "GET":
        return flask.redirect("/plot/day")

@app.route('/plot/histo/', methods=["GET"])
@login_required
def histo():
    if flask.request.method == "GET":
        png_ids = db.session.query(Figure.name).filter(
            Figure.name.like("histo%")).all()
        png_ids = [str(tp[0]) for tp in png_ids]   # tp: tuple; tuple[0] => str
        return flask.render_template("histo.html", histos=png_ids)

@app.route('/plot/.json/', methods=["GET"])
@login_required
def plot_json():
    if flask.request.method == "GET":
        figs_data = thedata.MEMC.get("FIGS_DATA")
        r = json.dumps(figs_data, default=util.dthandler)
        response = flask.make_response(r)
        response.headers["Content-type"] = "text/plain"
        return response

@app.route('/plot/<dur>/', methods=["GET"])
@login_required
def plot_dur(dur):
    if flask.request.method == "GET":
        png_ids = db.session.query(Figure.name).filter(
            Figure.name.like("{0}%".format(dur))).all()
        png_ids = [str(tp[0]) for tp in png_ids]   # tp: tuple; tuple[0] => str
        durs = list(thedata.DURATIONS)    # list() copies old list to a new one
        durs.remove(dur)
        return flask.render_template("plot.html", durs=durs, pngs=png_ids)

@app.route('/cal/', methods=["GET"])
@login_required
def groupcalendar():
    if flask.request.method == "GET":
        storage = Storage(thedata.STORAGE)
        cred = storage.get()
        # the next line copied from
        # https://code.google.com/p/google-api-python-client/wiki/OAuth2
        if cred is None or cred.invalid == True:
            flow = get_flow()
            callback = thedata.REDIRECT_URI
            authorize_url = flow.step1_get_authorize_url(callback)
            thedata.MEMC.set("OAUTH2_FLOW", pickle.dumps(flow))
            return flask.redirect(authorize_url)
        else:
            http = httplib2.Http()
            http = cred.authorize(http)
            probe = build('calendar', 'v3', http=http)

            # comments are just for records: ['acl', 'calendarList',
            # 'calendars', 'colors', 'events', 'freebusy', 'settings']

            interested_calId = thedata.GROUP_CAL_ID
            current = datetime.datetime.now()
            delta_30d = datetime.timedelta(days=30)
            events = probe.events().list(
                calendarId=interested_calId,
                timeMin=util.format_datetime(current-delta_30d, iso=True),
                timeMax=util.format_datetime(current, iso=True)).execute()
            eVents = []
            for event in events['items']:
                eVent = Event(
                    event.get('creator', '{}'),
                    event.get('start', '{}'),
                    event.get('end', '{}'),
                    event.get('location', 'noloc'),
                    event.get('summary', 'nosummary'),
                    )
                eVents.append(eVent)
            return flask.render_template("cal.html", events=eVents)

# for handing the google api OAuth2.0 response
@app.route('/oauth2callback/', methods=["GET"])
@login_required
def oauth2callback_accept():
    args = flask.request.args
    code = args.get('code', None)
    if code:                      # meaning the user has granted the permission
        flow = pickle.loads(thedata.MEMC.get("OAUTH2_FLOW"))
        credentials = flow.step2_exchange(args)
        storage = Storage(thedata.STORAGE)
        storage.put(credentials)
        return flask.redirect('/cal')
        # credentials have the attributes something like the following: (or check oauth2client:client.py +360
        # [['access_token', u'ya29.AHES6ZTlEnVejuwDk7G3YF1CAYWgAIWix8LkF697H2ichz_DDs73fA'],
        #  ['access_token_expired', False],
        #  ['refresh_token', None],
        #  ['token_expiry', datetime.datetime(2012, 7, 8, 21, 0, 33, 904819)],
        #  ['token_uri', 'https://accounts.google.com/o/oauth2/token'],
        #  ['client_id', '1090543704733-hg2lc1ak1t7c3gf9ubtgvr7ha29ll8dm.apps.googleusercontent.com'],
        #  ['client_secret', 's5akWp-3F_1csjFkwvCqksEj'],
        #  ['user_agent', 'sumcoresg/1.0']]
        #  ['apply', >],
        #  ['authorize', >],
        #  ['from_json', >],
        #  ['id_token', None],
        #  ['invalid', False],
        #  ['new_from_json', >],
        #  ['refresh', >],
        #  ['set_store', >],
        #  ['store', None],
        #  ['to_json', >],
    else:
        try:
            if args['error'] == 'access_denied':
                return "Sorry, you cannot view the cal if you deny, go back to <a href='/'>home</a>"
        except KeyError:
            return "key not in args: wired thing happen, please report to the maintainer"
# return flask.render_template("cal.html")

@app.route('/..test/', methods=["GET"])
@login_required
def test():
    if flask.request.method == "GET":
        # print dir(db.session)
        # db.session.add(usage)
        # cn = db.session.query(Usage).filter(Usage.clustername == 'mp2').all()[0]
        # print cn
        # ac = db.session.query(Account).filter(Account.email == '123@123.com').all()[0]
        # print ac
        return "this url is for testing"

def fetch_registered_emails():
    emails = db.session.query(Account.email).all()
    emails = [e[0] for e in emails]
    return emails

def set_account_cookie_and_redirect(uid, redirect_url):
    cookie_val = util.make_secure_cookie_val(str(uid))
    response = flask.make_response(flask.redirect(redirect_url))
    response.headers['Set-Cookie'] = 'account={0};expires="Sat, 01-Jan-2050 00:00:00 GMT";Path=/;'.format(cookie_val)
    return response

# The following two functions are gonna be deprecated after switching to
# gunicorn & storing figures in db
def start_collecting_data():
    thread = threading.Thread(target=collect_data, args=(db,))
    # remove this line at last & its tt function
    # thread = threading.Thread(target=util.tt)
    thread.daemon = True
    thread.start()

def start_app_run():
    port = int(os.environ.get('PORT', 1234))
    if not os.environ.get('DEV'):
        debug = True
        host = "127.0.0.1"
        ur = False
    else:
        debug = False
        host = "0.0.0.0"
        ur = False  # to avoid duplicate output in start_collecting_data thread
    app.run(host=host, port=port, debug=debug, use_reloader=ur)

if __name__ == '__main__':
###############################################################################
    # this is trying to use multiprocessing, the case is almost the same as
    # threading, doesn't solve the problem, I've spent too much time on this,
    # prefer to leave the code here for now

    # from multiprocessing import Process
    # p = Process(target=util.tt)
    # p.start()
###############################################################################

    start_collecting_data()
    start_app_run()
