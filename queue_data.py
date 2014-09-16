# import sys
import datetime

from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker

from app_config import db
from db_tables import Usage
from util import user_mapping

"""
This code was originally written to import data previous to 2012-03, which is
collected mannually from Chris Ing.
"""

def update_vars(cn, un, cores, status, ref_created, rcu, qcu):
    k = (cn, un, ref_created)
    if status == 'R':
        if k in rcu:
            rcu[k] += cores
        else:
            rcu[k]  = cores
    elif status =='W':
        if k in qcu:
            qcu[k] += cores
        else:
            qcu[k]  = cores
    else:
        raise ValueError("some error")
    return rcu, qcu

def main():
    userhash = user_mapping()
    engine = create_engine(
        "sqlite:////redacted_path_for_test/sumcoresg/queue_data.db", echo=True)
    jobs = engine.execute("select * from jobs where cluster ='Orca'").fetchall()
    # jobs = engine.execute("select * from jobs").fetchmany(6)
    jobs.sort(key=lambda x: x[1])

    fmt = '%Y-%m-%d %H:%M:%S.%f'
    # if two commits are longer than delta_t apart, suppose they're parsed from the
    # same xml data
    delta_t = datetime.timedelta(microseconds=100000)           # 0.1 seconds

    # if it's ref_created, then it's not necessarily the exact real time stamp
    ref_created = None
    rcu, qcu = {}, {}
    for k, j in enumerate(jobs):
        # cn: clustername; un: username
        cn = j[0].lower()
        created = datetime.datetime.strptime(j[1], fmt)
        un = userhash[j[2]] # converted to realname, realname equals username here
        cores = int(j[3]) * int(j[4])
        status = j[5]

        if not ref_created:
            # first time in the loop
            ref_created = created
        elif (created - ref_created) > delta_t:
            ref_created = created
        rcu, qcu = update_vars(cn, un, cores, status, ref_created, rcu, qcu)

    for cu in [rcu, qcu]:
        new_cu = {}
        for key in cu:
            # note: a key here is of a tuple type
            clustername, username, ref_created = key[0], key[1], key[2]
            pomeslab_key = (clustername, 'testlab', ref_created)
            if pomeslab_key in new_cu:
                new_cu[pomeslab_key] += cu[key]
            else:
                new_cu[pomeslab_key]  = cu[key]
        cu.update(new_cu)
    return rcu, qcu

def make_rows(rcu, qcu):
    usages = []                           # init usages
    # note: a key here is of a tuple type
    uccm = set(rcu.keys() + qcu.keys())
    for key in uccm:
        clustername, username, created = key[0], key[1], key[2]
        usage = Usage(
            clustername, username,
            rcu.get(key, 0),
            qcu.get(key, 0),
            created)
        usages.append(usage)
    usages.sort(key=lambda x: x.created)
    from pprint import pprint as pp
    pp(usages)
    return usages

def import_to_postgres(usages):
    for usage in usages:
        db.session.add(usage)
    db.session.commit()

if __name__ == "__main__":
    rcu, qcu = main()
    usages = make_rows(rcu, qcu)
    import_to_postgres(usages)

