#!/usr/bin/env python

import os
import re
import time
import random
import string
import hashlib
import hmac
import xml.dom.minidom as xdm

import pytz
import numpy as np
import paramiko
import jinja2

import thedata
import obj

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)
def render_str(template, **params):
    # maybe this function is the same as flask.render_template, prefer to use
    # the laster at the moment
    t = jinja_env.get_template(template)
    return t.render(params)

def user_mapping():
    """get username:real_name mapping"""
    dom = xdm.parse(os.path.join(os.path.dirname(__file__), 'static/xml', 'users.xml'))
    users = dom.getElementsByTagName('username')
    return {u.childNodes[0].data: u.nextSibling.childNodes[0].data for u in users}

def gen_cluster_obj_from_clustername(clustername):
    dom = xdm.parse(os.path.join(
            os.path.dirname(__file__), 'static/xml', 'clusters.xml'))
    clusters = dom.getElementsByTagName("cluster")  # get all cluster items
    for c in clusters:
        if c.getElementsByTagName("clustername")[0].childNodes[0].data == clustername:
            args = [c.getElementsByTagName(tag)[0].childNodes[0].data
                    for tag in thedata.CLUSTER_TAGS]
            cluster_obj = obj.Cluster(*args)
            return cluster_obj

# def gen_cluster_obj_from_hostname(hostname):
#     dom = xdm.parse(os.path.join(
#             os.path.dirname(__file__), 'static/xml', 'clusters.xml'))
#     hns_nodes = dom.getElementsByTagName("hostnames") # hn: hostname
#     for node in hns_nodes:
# 	hns = [i.childNodes[0].data for i in node.getElementsByTagName("hn")]
# 	if hostname in hns:
# 	    c =  node.parentNode
# 	    args = [ c.getElementsByTagName(tag)[0].childNodes[0].data
# 		     for tag in ['clustername', 'cores-per-node', 'statcmd']
# 		     ]
# 	    cluster_obj = obj.Cluster(*args)
# 	    return cluster_obj

def sshexec(host, username, cmd, rsa_key_file=None):
    """
    cmd: should be a string, not list
    #### not perfect!
    This function needs to be rewritten to be more convenient for debugging!!
    """
    # check the existence of ~/.ssh/id_rsa (or id_dsa?)

    if rsa_key_file:
        rsa_key_file = os.path.expanduser(rsa_key_file)
        if not os.path.exists(rsa_key_file):
            raise IOError('{0} rsa_key_file cannot found'.format(rsa_key_file))
        else:
            rsakf = rsa_key_file                            # rsakf: rsa key file
    else:
        rsakf = ".sumcoresgk"

    rsa_key = paramiko.RSAKey.from_private_key_file(rsakf)

    # This step will timeout after about 75 seconds if cannot proceed
    channel = paramiko.Transport((host, 22))
    channel.connect(username=username, pkey=rsa_key)
    session = channel.open_session()

    # if exec_command fails, None will be returned
    session.exec_command(cmd)

    # not sure what -1 does? learned from ssh.py
    output = session.makefile('rb', -1).readlines()
    channel.close()
    if output:
        return output

def prune(dd, preserved_keys=None):
    """remove the items where their keys are not in preserved_keys and their
    values are 0"""
    if preserved_keys:
        pk = preserved_keys
    else:
        pk = []
    return {k:dd[k] for k in dd if (dd[k] != 0) or (k in pk)}

def split_list(thelist, step):
    llen = len(thelist)
    if llen <= step:
        return [thelist]
    else:
        final_list = []
        ng = len(thelist) / step
        for i in range(ng):
            if ng - i > 1:
                final_list.append(thelist[i * step:(i+1) * step])
            else:
                final_list.append(thelist[i * step:])
        return final_list

def format_datetime(t, iso=False):
    """t is a datetime.datetime object; iso mean isoformat, non-iso is
    prettier"""
    fmt = '%Y-%m-%d %H:%M:%S %Z%z'
    if t.tzinfo:
        if iso:
            return t.isoformat()
        else:
            return t.strftime(fmt.replace('%Z', ''))
    else:
        toronto = pytz.timezone('America/Toronto')
        if iso:
            return toronto.localize(t).isoformat()
        else:

            return toronto.localize(t).strftime(fmt)

def dat2time(x):                                       # dat: datetime
    return time.mktime(x.timetuple())

def dthandler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        raise TypeError(
            'Object of type %s with value of %s is not JSON serializable' % (
                type(obj), repr(obj)))

##########################FOR VALID EMAIL & PASSWORD###########################
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

SECRET_CODE = "REDACTEDREDACTEDREDACTEDREDACTEDREDACTEDREDACTED"
def valid_secretcode(secretcode):
    # sc: secret code hash
    return hashlib.sha256(secretcode).hexdigest() == SECRET_CODE

#########################FOR GENERATING PASSWORD HASH##########################
def make_salt(n):
    return ''.join(random.choice(string.letters) for x in xrange(n))

def make_pw_hash(username, password, salt=None):
    # make password hash to store in the database
    if not salt:
        salt = make_salt(5)
    hash = hashlib.sha256(username + password + salt).hexdigest()
    return '%s|%s' % (hash, salt)

def correct_password(name, pw, h):
    salt = h.split('|')[1]
    return h == make_pw_hash(name, pw, salt)

#############################FOR GENERATING COOKIE#############################
SECRET="notsecret"
def hash_str(s):
    return hmac.new(SECRET, s).hexdigest()

def make_secure_cookie_val(s):
    # make cookie values
    return "{0}|{1}".format(s, hash_str(s))

def valid_cookie_val(h):
    if h:
        id = h.split('|')[0]
        return h == make_secure_cookie_val(id)
