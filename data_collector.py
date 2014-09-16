#! /usr/bin/env python

import os
import time
import datetime
import StringIO

import numpy as np
from sqlalchemy import and_

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MaxNLocator

import util
from thedata import MEMC, DURATIONS, THE_VERY_BEGINNING
from db_tables import Usage, Figure

# These are too big to be stored in memcached, used as global variables
# instead, which is BAD, though
RAW_XML = {}

def get_RAW_XML():
    # used by sumcoresg.py. There should be a better way to do this, especially
    # if the threading approach is not adequate any more
    global RAW_XML
    return RAW_XML

def insert2db(rcu, qcu, ic_obj, created, db):
    # making a new row, "testlab", it will be recorded to the db anyway
    # regardless of the usage of other accounts, i.e. even when all of
    # them are 0, it's very important since we need a datapoint at this
    # snapshot!

    # rcu, qcu could be {}, {}, meaning cluster is down, else they can
    # be rcu, qcu could only have a bunch of {key:0}s
    #### Here is a flaw in the design because when the cluster is
    #### down, the 0 core usages ({},{}) cannot be distinguished from the real
    #### 0 core usages ({u1:0, u2:0}, {u1:0, u2:0})
    for dd in [rcu, qcu]:
        dd.update(dict(testlab=sum(dd.values())))

    # remove items where its value is 0,
    rcu = util.prune(rcu, preserved_keys=['testlab'])
    qcu = util.prune(qcu, preserved_keys=['testlab'])

    # uccm: users consuming cores at the moment (realnames)
    # using uccm instead of usermap.values() is trying to eliminate usage items
    # where the both of user's runningcores notrunning cores are zero
    uccm = set(rcu.keys() + qcu.keys())

    # must use rcu.get(realname, 0), qcu.get(realname, 0) instead of
    # rcu[realname], or qcu[realname] since the realname could be in either rcu
    # or qcu, or both.
    for realname in sorted(uccm):
        usage = Usage(
            ic_obj.clustername,
            realname,
            rcu.get(realname, 0),
            qcu.get(realname, 0),
            created)
        db.session.add(usage)
    db.session.commit()

def inte_coresec(xs, ys):
    # inte: integrate core seconds
    # xs: usually time along the x axis
    # ys: core seconds along the y axis
    # The math is just like calculating the area of tiny trapezoids, and then
    # sum it up.
    xs = [util.dat2time(i) for i in xs]
    ref_x = xs[0]
    ref_y = ys[0]
    area = 0
    for x, y in zip(xs[1:], ys[1:]):
        area = area + (.5 * (y + ref_y) * (x - ref_x))
        ref_x, ref_y = x, y
    return area                                             # core seconds

def get_delta_ts_and_resolutions():
    """returned datetime.timedelta objects"""
    # delta_t options
    delta_1d  = datetime.timedelta(days=1)          # 1 day
    delta_1w  = datetime.timedelta(days=7)          # 1 week
    delta_1m  = datetime.timedelta(days=30)         # 1 month
    # number of days from THE_VERY_BEGINNING
    delta_1y  = datetime.timedelta(
        days=(datetime.datetime.now() - THE_VERY_BEGINNING).days)

    # resolution options
    delta_10M = datetime.timedelta(minutes=10)      # 10 minutes
    # delta_30M = datetime.timedelta(minutes=30)      # 30 minutes
    delta_1H  = datetime.timedelta(hours=1)         # 1 hours
    # delta_3H  = datetime.timedelta(hours=3)         # 3 hours
    delta_5H  = datetime.timedelta(hours=5)         # 5 hours
    delta_1d  = delta_1d

    return ([delta_1d,  delta_1w, delta_1m, delta_1y],
            [delta_10M, delta_1H, delta_5H, delta_1d])

def zoomout_query(query_results, resolution):
    """
    this is trying to decrease the time resolution of desc ordered query
    results with datetime objects to the specified resolution, which should
    be a datetime.timedelta object;

    for each item, the index number of the datetime object must be 1;

    the non-datetime column will be normalized by the value of norm to a percentage
    """
    zoomouted = []
    last_index = len(query_results) - 1

    # starting from the second item in query_results, since the first and last
    # one will be used to indicate the actually timestamp, shouldn't be
    # averaged
    beg_item = query_results[1]
    ref_t = beg_item[1]
    # ts: used to collect time for average;
    # cs for cores initial reference time
    cs, ts = [beg_item[0]], [util.dat2time(ref_t)]
    for k, item in enumerate(query_results):
        item_c, item_t = item
        item_c = item_c
        if k == 0 or k == last_index: # not do anything with the first and last item
            item = list(item)         # tuple => list
            zoomouted.append([item_c, item_t])
        else:
            if item_t - ref_t <= resolution:
                ts.append(util.dat2time(item_t))
                cs.append(item_c)
            else:
                zoomouted.append([
                        np.average(cs),
                        datetime.datetime.fromtimestamp(np.average(ts))
                        ])
                ref_t = item_t
                cs, ts = [item_c], [util.dat2time(item_t)] # reinitialize ts, cs
    return zoomouted

def prepare_data_for_plotting(ic, created, db):
    """ic: name of the interested cluster"""
    dur_queries = []  # duration querys, sorry, such name is not very intuitive
    for delta_t, resolution_t in zip(*get_delta_ts_and_resolutions()):
        query_result = db.session.query(Usage.runningcores, Usage.created).filter(
            and_(Usage.clustername==ic,
                 Usage.username=='testlab',
                 created - Usage.created < delta_t
                 )).order_by(Usage.created).all()

        # if <= 1, there is no point to decrease resolution, and possibly data
        # is lost within that delta_t
        if len(query_result) > 1:
            # decrease the resolution to the desired one
            query_result = zoomout_query(query_result, resolution_t)

            # do tranposition, ending with two lists, i.e. x, y
            query_result = np.array(query_result).transpose()

            # trying to get the right order for x, y [[t1,t2,t3], [c1,c2,c3]]
            query_result = query_result.tolist()
            query_result.reverse()
            query_result = np.array(query_result)
        else:
            # to be consistent as an (2,N) multidimensional array and at the
            # same time reflect the fact that data is lost.
            query_result = np.array([[created, created], [0., 0.]])
        dur_queries.append(query_result)
    return dur_queries

def do_fig_plotting(fig, ax, key_group, dur, figs_data_dict, usage_frac_dict):
    for key in key_group:                       # note: key is a ic
        x, y = figs_data_dict[key][dur]
        # note: key_obj is a ic_obj
        key_obj = util.gen_cluster_obj_from_clustername(key)
        ax.plot(x, y / float(key_obj.quota) * 100, 'o-', linewidth=2,
                label="{0} | {1} | {2:.1%}".format(
                key_obj.clustername,
                key_obj.quota,
                usage_frac_dict[key_obj.clustername][dur]))

    ax.xaxis.set_major_locator(MaxNLocator(15))
    if dur in ['day', 'week']:
        dtfmt = "%Y-%m-%d %H:%M"
    else:
        dtfmt = "%Y-%m-%d"
    ax.xaxis.set_major_formatter(DateFormatter(dtfmt))
    ax.minorticks_on()
    ax.grid(b=True, which="both")
    leg = ax.legend(loc="best")
    leg.get_frame().set_alpha(0.2)
    fig.autofmt_xdate()

    # It's probably better to plot percentage
    ax.set_ylabel("Running Cores (%)", labelpad=50)
    xlim = list(ax.get_xlim())             # get_ylim() returns a tuple
    ylim = list(ax.get_ylim())             # get_ylim() returns a tuple
    ylim[0] = -5                           # to see 0 more clearly
    # make sure we see this line at y=100%
    ylim[1] = ylim[1] * 1.1 if ylim[1] > 100 else 105

    # drawing reference line, this will mess up the xlim, need to
    # find a way to avoid it 2012-06-28
    beg_datetime = datetime.datetime(*[2000, 1, 1, 0, 0, 0, 0])
    end_datetime = datetime.datetime(*[2050, 1, 1, 0, 0, 0, 0])
    ax.plot([beg_datetime, end_datetime], [100, 100], 'k--')
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    return  fig

def update_the_figure(db, Figure, ident, fig_content, created):
    # though .all(), ideally, there should be only one row.
    q = db.session.query(Figure).filter(Figure.name == ident).all()
    if q:                                       # do update only
        q = q[0]   # actually, there should be only 1 row, bad code due to bad design
        q.content = fig_content
        q.created = created
    else:
        fig4db = Figure(ident, fig_content, created)
        db.session.add(fig4db)
    return db

def collect_data(db):
    """should be ideally run in background"""
    # the names in interested_clusters are not arbitrary, it has to match the
    # clusternames in static/xml/clusters.xml, e.g. scinet is not the same as
    # Scinet, SciNet, or Sci Net

    # be sure to use config var INTERESTED_CLUSTERS on heroku
    # here, just use scinet is for local testing,
    interested_clusters = os.getenv(
        "INTERESTED_CLUSTERS",
        "scinet mp2 colosse guillimin lattice nestor parallel orcinus orca").split()

    # interested_clusters = ["orcinus"]

    # sort of variables initialization
    figs_data_dict, usage_frac_dict = {}, {}
    usermap = util.user_mapping()
    delta_ts, resolutions = get_delta_ts_and_resolutions()
    durations = DURATIONS
    while True:
        for ic in interested_clusters:                 # ic: interested cluster
            ic_obj = util.gen_cluster_obj_from_clustername(ic)
            raw_xml = ic_obj.fetch_raw_xml()
            created = datetime.datetime.now()
            if raw_xml:
                global RAW_XML
                RAW_XML[ic] = raw_xml
                # having such error for scinet and nestor,
                # MemcachedError: error 37 from memcached_set: SUCCESS
                # guess those xml data may be too big for memcached,
                # using system memory instead for now 2012-06-12
                # MEMC.set("RAW_XML", raw_xml_cache)

            # rcu, qcu: running & queuing core usages
            rcu, qcu = ic_obj.process_raw_xml(usermap, raw_xml)

            # 1. generate reports and cache it
            reports = MEMC.get("REPORTS")
            if not reports:                               # meaning: first time
                reports = {}
            report = ic_obj.gen_report(rcu, qcu, usermap, created)
            reports[ic_obj.clustername] = report
            MEMC.set("REPORTS", reports)

            # 2. insert to database
            insert2db(rcu, qcu, ic_obj, created, db)

            # 3. cache usage data for later plotting
            # dur_queries = [last_day_data, last_week_data, last_month_data,
            # last_year_data]
            dur_queries = prepare_data_for_plotting(ic, created, db)

            # this is for /.json kind of url
            figs_data_dict[ic] = {i:j for i, j in zip(durations, dur_queries)}
            MEMC.set("FIGS_DATA", figs_data_dict)

            # ldd:last_day_data;    lwd:last_week_data
            # lmd:last_month_data;  lyd:last_year_data
            ldd, lwd, lmd, lyd = dur_queries
            total_sec_to_now = (
                lyd[0][-1] - THE_VERY_BEGINNING).total_seconds()

            # inte_coresec: integrate core seconds
            usage_frac_dict[ic] = {
                'day': inte_coresec(*ldd) / (ic_obj.quota * 24 * 3600),
                'week': inte_coresec(*lwd) / (ic_obj.quota * 7 * 24 * 3600),
                'month': inte_coresec(*lmd) / (ic_obj.quota * 30 * 24 * 3600),
                'year': inte_coresec(*lyd) / (ic_obj.quota * total_sec_to_now),
                }
            MEMC.set("USAGE_FRAC", usage_frac_dict)

        # 4. Now let's do the real plotting, first: usage vs. time, then: histogram
        # 1). usage vs. time
        keys = sorted(figs_data_dict.keys())
        for index, key_group in enumerate(util.split_list(keys, step=4)):
            figs, axes = {}, {}
            for dur in durations:
                figs[dur] = plt.figure(figsize=(24, 13.5))
                axes[dur] = figs[dur].add_subplot(111)
                fig, ax = figs[dur], axes[dur]
                fig = do_fig_plotting(fig, ax, key_group, dur,
                                      figs_data_dict, usage_frac_dict)

                canvas = FigureCanvas(fig)
                png_output = StringIO.StringIO()
                canvas.print_png(png_output)
                plt.close(fig)                            # clear up the memory

                # figure naming pattern should be systematically redesigned
                # when # gets large
                ident = str('_'.join([dur, str(index)]))
                fig_content = png_output.getvalue()
                db = update_the_figure(db, Figure, ident, fig_content, created)
            db.session.commit()

        # 2). histogram plotting
        usage_frac_dict_by_dur = {}
        for dur in durations:
            usage_frac_dict_by_dur[dur] = {}
        for ic in usage_frac_dict:
            for dur in usage_frac_dict[ic]:
                usage_frac_dict_by_dur[dur][ic] = usage_frac_dict[ic][dur]

        for dur in usage_frac_dict_by_dur:
            N = len(usage_frac_dict_by_dur[dur])
            width = 1.                         # the width of the bars
            ind = np.arange(0, N, width)       # the x locations for the groups

            keys = usage_frac_dict_by_dur[dur].keys()
            keys.sort(key=lambda k:usage_frac_dict_by_dur[dur][k], reverse=True)
            # make sure the order is right
            durMeans = [usage_frac_dict_by_dur[dur][k] for k in keys]

            fig = plt.figure(figsize=(16, 10))
            fig.subplots_adjust(bottom=0.2) # otherwise, xticklabels cannot be shown fully
            ax = fig.add_subplot(111)

            for i, d in zip(ind, durMeans):
                # 'g': green; 'r': red
                col = 'g' if d > 1 else 'r'
                ax.bar(i, d, width, color=col)

            ylim = list(ax.get_ylim())
            ylim[1] = ylim[1] * 1.1 if ylim[1] > 1 else 1.05

            ax.plot([0, 100], [1, 1], 'k--')
            ax.set_xlim([0, N*width])
            ax.set_ylim(ylim)

            ax.set_ylabel('Usage', labelpad=40)
            ax.set_title(dur, size=40, family="monospace",
                         bbox={'facecolor':'red', 'alpha':0.5})
            ax.title.set_y(1.02)                            # offset title position
            ax.set_xticks(ind+width / 2.)
            ax.set_xticklabels(keys, size=25, rotation=45)
            ax.grid(b=True, which="both")

            canvas = FigureCanvas(fig)
            png_output = StringIO.StringIO()
            canvas.print_png(png_output)
            plt.close(fig)

            ident = "histo_{0}".format(dur)
            fig_content = png_output.getvalue()

            db = update_the_figure(db, Figure, ident, fig_content, created)
        db.session.commit()

        # when at last, maybe 10min is too frequent, think about 30 min
        dt = os.environ.get('DELTAT')
        if not dt:
            time.sleep(600)                                 # sleep 10 min
        else:
            time.sleep(float(dt))
