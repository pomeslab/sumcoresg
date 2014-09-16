#!/usr/bin/env python

import sys
import datetime
import iso8601
from socket import gaierror

import paramiko

import util
import statparsers

class Cluster(object):
    def __init__(self, clustername, login_url, account, 
                 url, cores_per_node, statcmd, quota):
	"""
	cores_per_node
	statcmd: the command used to generate usage statics, probably in xml
	"""
        self.clustername = clustername
        self.login_url = login_url
        self.account = account
        self.url = url
        self.cores_per_node = int(cores_per_node)
        self.statcmd = statcmd
        self.quota = int(quota)

    def sshexec(self, cmd=None):
        """when ftime is True, the time when the output is received will also
        be returned"""

        if not cmd:
            cmd = self.statcmd
            r = util.sshexec(self.login_url, self.account, cmd)
            return r

    def fetch_raw_xml(self):
        print "start fetch raw_xml from {0} with {1}".format(self.login_url, self.statcmd)
        try:
            raw_xml = self.sshexec()
            print "raw_xml fetched from {0}".format(self.login_url)
        # AuthenticationException is a subclass of SSHException, so it
        # needs to be evaluated first
        # new exceptions are still being found, each time added to the
        # following to make the exception type explicit
        except paramiko.AuthenticationException:
            raw_xml = None
            print ("fetching raw_xml failed from {0}, authentication error, "
                   "make sure you have updated keys".format(self.login_url))
        except paramiko.SSHException:
            raw_xml = None
            print "fetching raw_xml failed from {0}, it may be down".format(self.login_url)
        except gaierror:
            raw_xml = None
            print "gaierror when fetching xml from {0}".format(self.login_url)
        except:
            raw_xml = None
            print "Unexpected error:", sys.exc_info()[0]
        return raw_xml

    def process_raw_xml(self, usermap, raw_xml):
	"""usermap: username-to-realname mapping"""
        if raw_xml:
            # rcu, qcu: running & queuing core usages
            # active_cores, total_cores are returned, but won't be used at the
            # moment 2012-06-23 since it's not accurate at all for some reason
            # 2012-06-23
            rcu, qcu, active_cores, total_cores = statparsers.CLUSTER2STATPARSER[
                self.clustername](raw_xml, usermap, self.cores_per_node)
        else:
            # this is different from everyone having zero core usage, which
            # would produce a dict with all values equal 0
            rcu, qcu = {}, {}
        return rcu, qcu

    def gen_report(self, rcu, qcu, usermap, created=None):
        # first, title of the report
        title = "{0}|{1}|{2}".format(self.clustername, self.quota, self.cores_per_node)

        # second, created datetime
        created = created if created else datetime.datetime.now()

        report_content = []

        # datetime, an addtional "\n" is just for making the reportprettier
        report_content.append("{0}\n".format(util.format_datetime(created)))
        if not rcu and not qcu:
            report_content.append("data not available at the moment")
        else:
            rcu, qcu = util.prune(rcu), util.prune(qcu)

            total_usage = {}
            for realname in set(usermap.values()):
                total_usage[realname] = sum(dd.get(realname, 0) for dd in [rcu, qcu])
            total_usage = util.prune(total_usage)    

            # from this step on, basically it's about print data from 3 dicts
            # in a pretty way: rcu, qcu, total_usage

            # 1. print headers
            report_content.append("{0:13s} {1:8s} {2:8s} {3:8s}".format(
                    'USERNAME', 'Running', 'NotRunning', 'TOTAL'))

            # 2. sort the order of key by total_usage
            sorted_keys = reversed(sorted(total_usage, key=total_usage.get))
            
            if not len(total_usage) == 0:       # not the usage of everyone is zero
                report_content.append('=' * 44)

                # 3. print the table
                for k in sorted_keys:
                    # full name is too long, so last name is used since
                    # firstname is confusing
                    name = k.split()[0]
                    report_content.append("{0:13s} {1:<8d} {2:<8d} {3:<8d}".format(
                            name, rcu.get(k, 0), qcu.get(k, 0), total_usage.get(k, 0)))

            # 4. print the footer sum
            report_content.append('=' * 44)
            report_content.append("{0:13s} {1:<8d} {2:<8d} {3:<8d}".format(
                    'SUM', sum(rcu.values()), sum(qcu.values()), 
                    sum(total_usage.values())))
            report_content.append('=' * 44)

        # 5. join the final work
        report_content = '\n'.join(report_content)
        # 6. since it's displayed on line, need such replacements
        report_content = report_content.replace("\n", "<br>").replace(" ", "&nbsp;")

        return Report(self, report_content, created)

class Report(object):
    def __init__(self, cluster_obj, content, created):
        self.cluster = cluster_obj
        self.content = content
        self.created = created

    def __repr__(self):
        return "{0}|{1}\n{2} ".format(self.title, 
                                      util.format_datetime(self.created),
                                      self.content)

    def __setattr__(self, name, value):
        self.__dict__[name] = value


def start_end(tt):
    # the code is bad!! ugly
    keys = ['dateTime', 'date']
    if tt:
        for key in keys:
            if key in tt:
                if key == keys[0]:
                    return util.format_datetime(iso8601.parse_date(tt[key]))
                elif key ==keys[1]:
                    return util.format_datetime(datetime.datetime.strptime('2012-07-07', '%Y-%m-%d'))
    else:
        return None
class Event(object):
    def __init__(self, creator, start, end, location, summary):
        self.creator = creator['email'] if creator else None
        self.start = start_end(start)
        self.end = start_end(end)
        self.location = location if location else None
        self.summary = summary if summary else None

    def render(self):
        return util.render_str("event.html", event=self)
