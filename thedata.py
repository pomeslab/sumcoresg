import os
import datetime
import pylibmc

# this is used for gen_cluster_obj_from_clustername in util.py
CLUSTER_TAGS = ["clustername", "login_url", "username", "url",
                "cores_pernode", "statcmd",
                "quota"]

CLUSTER_DATA = [
    # e.g. data structure
    # [clustername, url, username,
    #  cores_pernode, statcmd, quota,
    #  [...],
    #  ]

    ['scinet', 'login.scinet.utoronto.ca', 'TEST',
     'http://wiki.scinethpc.ca',
    # Version: moab client 6.1.2 (revision 1, changeset
    # e9ca7f9e001afe6b2983621aad26e4414c7aa --2012-06-23
     8, '/usr/local/bin/showq --format=xml', 2500,
     ['gpc-f101n084', 'gpc-f102n084', 'gpc-f103n084', 'gpc-f104n084', 'gpc-logindm01']
     ],

    # showq --format=xml on mp2 doesn't show xml for some reason
    ['mp2', 'mp2.ccs.usherbrooke.ca', 'TEST',
     'https://rqchp.ca/?mod=cms&pageId=1380&lang=EN&',
    # version: 2.5.8 --2012-06-23
     24, '/opt/torque/bin/qstat -x', 5500,
     ['ip13', 'cp2540', 'ip14']
     ],

    ['colosse', 'colosse.clumeq.ca', 'TEST',
     'https://www.clumeq.ca/wiki/',
     # showq: Version: moab client 7.0.1 (revision 6, changeset
     # 28b311559e14a68d7873acd5c1de0601bbbf41ba)
     # qstat is from Grid Engine User Commands
     # version: GE 6.2u5 --2012-06-23
     8, '/opt/moab/bin/showq --format=xml; /usr/local/ge6.2u5/bin/lx24-amd64/qstat -xml -g d -u "*"', 1500,
     ['colosse1', 'colosse2']
     ],

    ['guillimin', 'guillimin.clumeq.ca', 'TEST',
     'http://www.hpc.mcgill.ca/index.php/guillimin-status',
     # Version: moab client 6.1.3 (revision 3, changeset
     # 6ffa03403892c92f4d63b34708b7a00c044eb2ea) --2012-06-23
     12, '/opt/moab/bin/showq --format=xml', 999,
     ['lg-1r14-n01', 'lg-1r14-n02', 'lg-1r14-n03', 'lg-1r14-n04', 'lg-1r14-n05']
     ],

    ['lattice', 'lattice.westgrid.ca', 'TEST',
     'https://www.westgrid.ca/support/running_jobs',
     # Version: moab client 5.4.2 (revision 9, changeset
     # 1ab636c98e1eedb41e1abd6cf15d315663374095)  --2012-06-23
     8, '/usr/local/moab/bin/showq --format=xml', 999,
     ['lattice']
     ],

    ['orcinus', 'orcinus.westgrid.ca', 'TEST',
     'https://www.westgrid.ca/support/running_jobs',
     # Version: moab client 5.4.2 (revision 9, changeset
     # 1ab636c98e1eedb41e1abd6cf15d315663374095)  --2012-06-23
     8, '/global/system/moab/bin/showq --format=xml', 1300,
     ['seawolf3']
     ],

    ['nestor', 'nestor.westgrid.ca', 'TEST',
     'https://www.westgrid.ca/support/running_jobs',
     # Version: moab client 5.4.3 (revision 1, changeset
     # f1fd7e143f4902693842e4bf72e6d1ed268b5437)  --2012-06-23
     # 8, '/opt/bin/qstat -x', 384,
     # not sure why cing use qstat instead of showq, I feel more comfortable
     # with showq
     8, '/opt/bin/showq --format=xml', 999,
     ['litai05.westgrid.ca']
     ],

    ['parallel', 'parallel.westgrid.ca', 'TEST',
     'https://www.westgrid.ca/support/running_jobs',
     12, '/usr/local/moab/bin/showq --format=xml', 1100,
     ['parallel']
     ],

    ['orca', 'orca.sharcnet.ca', 'TEST',
     'https://www.sharcnet.ca/my/systems/show/73',
     24, '/opt/sharcnet/moab/7.1.1/bin/showq --format=xml', 960,

     # showq version has been updated and the 6.1.3 showq is gone, that's why
     # orca data is not available
     # 'bash -l -c "/opt/sharcnet/moab/6.1.3/bin/showq --format=xml'
     # Orca is wired.
     # When doing ssh orca.sharcnet.ca /opt/sharcnet/moab/6.1.3/bin/showq
     # IT PRODUCE:
     # WARNING:  cannot open configfile '/opt/moab//etc/moab.cfg' (using internal defaults)
     # ERROR:    connection refused - no service listening at :42559

     # When doing ssh orca.sharcnet.ca /opt/sharcnet/torque/current/bin/qstat -x
     # IT PRODUCE: Unable to allocate memory for XML output, returning null

     # 24, '/opt/sharcnet/moab/6.1.3/bin/showq --format=xml',
     # 24, '/opt/sharcnet/torque/current/bin/qstat -x', 960,
     ['orc-login1', 'orc-login2']
     ],

    ]

USER_DATA = '''
    Test User           = TEST
    Test User 2         = TEST2
    Test User 3         = TEST3
'''
USER_TAGS = ["username", "realname"]
# starting time as shown below for the year
THE_VERY_BEGINNING = datetime.datetime.strptime(
    # "2012-03-16 00:00:00", "%Y-%m-%d %H:%M:%S")
    "2013-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
DURATIONS = ['day', 'week', 'month', 'year']
STORAGE = '.sumcoresg.dat'

GROUP_CAL_ID = 'fake@group.calendar.google.com'

# If *binary* is True, the binary memcached protocol is used.  SASL
# authentication is supported if libmemcached supports it (check
# *pylibmc.support_sasl*). Requires both username and password. Note that
# SASL requires *binary*=True.
MEMC = pylibmc.Client(
    # not sure why there could be replacement of ',' to ';'
    # learned from https://devcenter.heroku.com/articles/memcachier#django --2013-10-21
    servers=[os.environ.get('MEMCACHIER_SERVERS', '127.0.0.1').replace(',', ';')],
    username=os.environ.get('MEMCACHIER_USERNAME', ''),
    password=os.environ.get('MEMCACHIER_PASSWORD', ''),
    binary=True,
    )

CLIENT_ID = '0000000000000000.apps.googleusercontent.com'
CLIENT_SECRET = 'xxxxxxxxxxxxxxxxxxxxxx'                  # new key after reset 2012-08-13
REDIRECT_URI = 'https://testtest.herokuapp.com/oauth2callback'

