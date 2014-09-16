#! /usr/bin/env python

import xml.etree.ElementTree as xml

def init_vars(userhash):
    # initialize variables
    active_cores, total_cores = 0, 0
    rcu, qcu = {}, {}    # collect cores usage by running jobs & queueing cores
    for d in [rcu, qcu]:
        for n in set(userhash.values()):
            d[n] = 0
    return rcu, qcu, active_cores, total_cores

def parse_showq_xml_data(xml_data, rcu, qcu, active_cores, total_cores, userhash):
    queues = xml_data.findall('queue')
    for queue in queues:
        for job in queue.findall('job'):
            # collect global statitics
            # RegNodes seems to be set by None always after checking with set
            cores = int(job.get('ReqProcs'))
            job_state = job.get('State')
            if job_state == 'Running':
                active_cores += cores
            total_cores += cores

            # collect statistics for my group
            job_owner = job.get('User')
            if job_owner in userhash:                       # user in my group
                realname = userhash[job_owner]
                if job_state == 'Running':
                    rcu[realname] += cores
                else:
                    qcu[realname] += cores
    return rcu, qcu, active_cores, total_cores

def scinet_statparser(raw_xml_data, userhash, cores_per_node):
    # rcu, qcu: running & queuing core usages
    rcu, qcu, active_cores, total_cores = init_vars(userhash)

    # This following one line is very necessary e.g. form mp2 the returned
    # len(list) is 1 since a statparser is cluster specific, it should be able
    # to handle different kinds of raw_xml_data
    raw_xml_data = "".join(raw_xml_data)
    xml_data = xml.fromstring(raw_xml_data)

    # parse data in the following ORDER:
    # loop through all jobs (or equivalent nodes), all collect active_cores,
    # total_cores; but only collect rcu, qcu when the job owner is within the
    # interested group

    rcu, qcu, active_cores, total_cores = parse_showq_xml_data(
        xml_data, rcu, qcu, active_cores, total_cores, userhash)

    # the following function seems redundant now, might be deleted later
    # 2012-06-23
    # display_active_usage(active_cores, total_cores)
    return rcu, qcu, active_cores, total_cores

def mp2_statparser(raw_xml_data, userhash, cores_per_node):
    rcu, qcu, active_cores, total_cores = init_vars(userhash)

    # change on the following two lines seems to be because the format of
    # output changed from mp2 as of 2013-05-01

    # raw_xml_data = raw_xml_data[0]
    raw_xml_data = ''.join(raw_xml_data)

    xml_data = xml.fromstring(raw_xml_data)
    # xml_data = xml.fromstring(result.translate(None, "&")) ?
    # the above line is from cing, not sure when to use

    for job in xml_data.findall('Job'):
        # nodes info for mp2 is heterogeneous, it can be like this using
        # command "set([job.find("Resource_List").find("nodes").text for job in
        # xml_data.findall("Job")])"
        # set(['24', '10', '13', '12', '20', '3:ppn=1', '16:ppn=1', '1:ppn=1',
        # '28', '50', '1', '3', '2', '5', '4', '7', '6', '8', '7:ppn=1', '683',
        # 'cp0301'])
        try:
            nnodes = job.find('Resource_List').find("nodes").text.split(':')[0]
        except:
            nnodes = "none"              # dirty way of handling this exception
            print "handled mp2_statparser exception in the dirty way"
        if nnodes.isdigit():
            cores = cores_per_node * int(nnodes)
        else:
            cores = 0                # e.g. cp0301, not sure what this would be
        job_state = job.find('job_state').text
        # possible jobs status set(['Q', 'H', 'R'])
        if job_state == 'R':
            active_cores += cores
        total_cores += cores

        # e.g. 'test@ip13.m', 'testuser1@ip14.m'
        job_owner = job.find('Job_Owner').text.split('@')[0]
        if job_owner in userhash:
            realname = userhash[job_owner]
            if job_state == 'R':
                rcu[realname] += cores
            else:
                qcu[realname] += cores

    return rcu, qcu, active_cores, total_cores

def colosse_statparser(raw_xml_data, userhash, cores_per_node):
    rcu, qcu, active_cores, total_cores = init_vars(userhash)

    # colosse is some complicated, it has data from both showq & qstat; so have
    # to parse one by one
    # the first 2 elm are from showq
    raw_xml_data_showq = ''.join(raw_xml_data[:2])
    try:
        xml_data_showq = xml.fromstring(raw_xml_data_showq)
        rcu, qcu, active_cores, total_cores = parse_showq_xml_data(
            xml_data_showq, rcu, qcu, active_cores, total_cores, userhash)
    except:
        print "xml.fromstring(raw_xml_data_showq) from colosse failed"

    # I think the format of qstat xml data has changed, the returned list is
    # much longer (~700 to >1000), the old parser cannot parse this part of
    # data properly at all.
    raw_xml_data_qstat = ''.join(raw_xml_data[2:])

    try:
        xml_data_qstat = xml.fromstring(raw_xml_data_qstat)
        for queue_or_job_info in xml_data_qstat.getchildren():
            # The children are like
            # [<Element 'queue_info' at 0x110281750>, <Element 'job_info' at 0x1102a79d0>]
            for job in queue_or_job_info.findall('job_list'):
                cores = int(job.find('slots').text) # no need to times number of nodes
                job_state = job.find('state').text
                if job_state == 'r':
                    active_cores += cores
                total_cores += cores

                job_owner = job.find('JB_owner').text
                if job_owner in userhash:
                    realname = userhash[job_owner]
                    if job_state == 'r':
                        rcu[realname] += cores
                    else:
                        qcu[realname] += cores
    except:
        print "exception in raw_xml_data_qstat failed in colosse, handled in a very dirty way. (note: qstat is gonna be deprecated after 27th of August, 2012, then this part of the parser can be removed, so can the command line)"
    return rcu, qcu, active_cores, total_cores

def guillimin_statparser(raw_xml_data, userhash, cores_per_node):
    rcu, qcu, active_cores, total_cores = scinet_statparser(
        raw_xml_data, userhash, cores_per_node)
    return rcu, qcu, active_cores, total_cores

def lattice_statparser(raw_xml_data, userhash, cores_per_node):
    rcu, qcu, active_cores, total_cores = scinet_statparser(
        raw_xml_data, userhash, cores_per_node)
    return rcu, qcu, active_cores, total_cores

def orcinus_statparser(raw_xml_data, userhash, cores_per_node):
    rcu, qcu, active_cores, total_cores = scinet_statparser(
        raw_xml_data, userhash, cores_per_node)
    return rcu, qcu, active_cores, total_cores

def nestor_statparser(raw_xml_data, userhash, cores_per_node):
    rcu, qcu, active_cores, total_cores = scinet_statparser(
        raw_xml_data, userhash, cores_per_node)
    return rcu, qcu, active_cores, total_cores

def orca_statparser(raw_xml_data, userhash, cores_per_node):
    rcu, qcu, active_cores, total_cores = scinet_statparser(
        raw_xml_data, userhash, cores_per_node)
    return rcu, qcu, active_cores, total_cores

def parallel_statparser(raw_xml_data, userhash, cores_per_node):
    rcu, qcu, active_cores, total_cores = scinet_statparser(
        raw_xml_data, userhash, cores_per_node)
    return rcu, qcu, active_cores, total_cores


CLUSTER2STATPARSER = {
    'scinet'    : scinet_statparser,
    'mp2'       : mp2_statparser,
    'guillimin' : guillimin_statparser,
    'colosse'   : colosse_statparser,
    'nestor'    : nestor_statparser,
    'lattice'   : lattice_statparser,
    'parallel'  : parallel_statparser,
    'orcinus'   : orcinus_statparser,
    'orca'      : orca_statparser,
    }

def display_active_usage(active_cores, total_cores):
    if total_cores != 0:
        print "=" * 44
        print "Active cores {0} / {1} = {2:.2%}".format(
            active_cores, total_cores, active_cores / float(total_cores))
        print
        print "this NUMBER is NOT ACURATE on mp2, scinet, guillimin, colosse, lattice, \nonly orca is ok"
        print "=" * 44
        print
