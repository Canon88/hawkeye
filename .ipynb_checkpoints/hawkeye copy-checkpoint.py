'''
Author: Canon
Date: 2021-01-24 13:21:39
LastEditTime: 2021-02-01 21:45:33
LastEditors: Please set LastEditors
Description: In User Settings Edit
FilePath: /Code/Jupyter/Beacon/hawkeye.py
'''

import os
import sys
import json
import datetime
from multiprocessing import Process, JoinableQueue, Lock, Manager

import argparse
import pandas as pd
from tqdm import tqdm
from loguru import logger

from config.config import Config
from tools.kibana import Kibana
from tools.elastic import Elastic
from tools.notification import Slack

# TODO 新增威胁情报对接
# TODO 新增TheHive对接


def add_arguments():
    parser = argparse.ArgumentParser(
        description='Beacon detection tool for network traffic. by Canon.')
    parser.add_argument('-c', '--config', type=str,
                        help='Specify configuration file. config.yaml')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable certain debug selectors')
    parser.add_argument('-l', '--log', type=str,
                        help='Specify the logging path')
    return parser.parse_args()


args = add_arguments()
config = Config()

if args.config:
    yaml = args.config
else:
    dirname = os.path.dirname(os.path.realpath(__file__))
    yaml = os.path.join(dirname, 'config/config.yaml')
base_conf = config.load(yaml)

# Beacon
beacon = base_conf['beacon']

# Storage
storage = base_conf['storage']

# Notification
notification = base_conf['notification']

# Alias
alias = base_conf['alias']

# Elastic
elasticsearch = base_conf['elasticsearch']
must = elasticsearch['query']['must']
must_not = elasticsearch['query']['must_not']
index = elasticsearch['index']
includes = elasticsearch['source']['includes']
excludes = elasticsearch['source']['excludes']

# Kibana
kbn = base_conf['kibana']

# Format date
format_date = base_conf['datetime']['format']


class HawkEye():
    def __init__(self):
        self.es = self.elastic()
        self.fields = self.normalized(alias)

        self.min_occur = int(beacon['min_occur'])
        self.min_percent = int(beacon['min_percent'])
        self.window = int(beacon['window'])
        self.num_processes = int(beacon['threads'])
        self.min_interval = int(beacon['min_interval'])
        self.period = int(beacon['period'])

        self.q_job = JoinableQueue()
        self.l_df = Lock()
        self.l_list = Lock()

    def elastic(self):
        hosts = elasticsearch['hosts']
        config = elasticsearch['config']
        return Elastic(hosts, **config)

    def normalized(self, alias):
        """标准化字段方法

        :param alias: alias field
        :return: dict object
        """
        fields = {'beacon': [], 'output': [], 'aliases': {}}
        for field, info in alias.items():
            fields['aliases'][info['alias']] = field
            for i in info.get('type', []):
                fields[i].append(field)
        return fields

    def get_timestamp(self, hours=0):
        """获取X小时前的时间戳

        :param hour: 指定时间(小时)
        :return: timestamp (int)
        """
        t = datetime.datetime.now()
        timestamp = (t - datetime.timedelta(hours=hours)).timestamp()
        return round(timestamp * 1000)

    def get_isotime(self, hours=0):
        local = datetime.datetime.utcnow()
        t = local - datetime.timedelta(hours=hours)
        return t.isoformat()[:-3]+'Z'

    def create_url(self, row, payload, kibana):
        """
        match = {'must': [], 'must_not': []}
        for k, v in row.items():
            if k in self.fields['beacon']:
                match['must'].append({
                    'terms': {k: [v]}
                })
        payload['match'] = match
        payload['alias'] = 'interval: ' + str(row['interval'])
        url = kibana.generate_discover_url(**payload)
        url = kibana.shorten_url(url)
        return url
        """

        payload['query'] = row
        url = kibana.generate_discover_url(**payload)
        url = kibana.shorten_url(url)
        return url

    def percent_grouping(self, d, total):
        interval = 0
        # Finding the key with the largest value (interval with most events)
        mx_key = int(max(iter(list(d.keys())), key=(lambda key: d[key])))
        mx_percent = 0.0

        for i in range(mx_key - self.window, mx_key + 1):
            current = 0
            # Finding center of current window
            curr_interval = i + int(self.window / 2)
            for j in range(i, i + self.window):
                if j in d:
                    current += d[j]
            percent = float(current) / total * 100
            if percent > mx_percent:
                mx_percent = percent
                interval = curr_interval
        return interval, mx_percent

    def find_beacon(self, q_job, beacon_list):
        while not q_job.empty():
            beacon_id = q_job.get()
            self.l_df.acquire()
            work = self.df[self.df.beacon_id ==
                           beacon_id].reset_index(drop=True)
            work = work.copy()
            self.l_df.release()

            timestamp = self.fields['aliases']['timestamp']
            if not format_date:
                work[timestamp] = pd.to_datetime(work[timestamp])
            else:
                work[timestamp] = pd.to_datetime(
                    work[timestamp], format=format_date)
            work[timestamp] = (work[timestamp].astype(
                int) / 1000000000).astype(int)
            work = work.sort_values([timestamp])
            work['delta'] = (work[timestamp] -
                             work[timestamp].shift()).fillna(0)

            work = work[1:]
            d = dict(work.delta.value_counts())
            for key in list(d.keys()):
                if key < self.min_interval:
                    del d[key]

            # Finding the total number of events
            total = sum(d.values())
            if d and total > self.min_occur:
                window, percent = self.percent_grouping(d, total)
                if percent > self.min_percent and total > self.min_occur:
                    # add fields['output'] by Canon 2020.04.28
                    beacon = work[self.fields['output']].iloc[0].tolist()
                    beacon.extend([int(percent), window, total])

                    self.l_list.acquire()
                    beacon_list.append(beacon)
                    self.l_list.release()
            q_job.task_done()

    def find_beacons(self):
        for beacon_id in self.high_freq:
            self.q_job.put(beacon_id)

        mgr = Manager()
        beacon_list = mgr.list()
        processes = [Process(target=self.find_beacon, args=(
            self.q_job, beacon_list,)) for thread in range(self.num_processes)]

        # Run processes
        for p in processes:
            p.start()

        # Exit the completed processes
        for p in processes:
            p.join()

        beacon_list = list(beacon_list)

        aliases = self.fields['aliases']
        # alias_list = list(aliases.keys())
        alias_list = list(aliases.values())
        # alias_list.remove('timestamp')
        alias_list.remove(aliases['timestamp'])

        beacon_fields = alias_list + ['percent', 'interval', 'occurrences']
        beacon_df = pd.DataFrame(beacon_list, columns=beacon_fields).dropna()
        beacon_df.interval = beacon_df.interval.astype(int)
        beacon_df = beacon_df.sort_values(
            ['percent', 'occurrences'], ascending=False).reset_index(drop=True)
        return beacon_df

    def analyze(self):
        # add gte timestamp
        gte = self.get_isotime(self.period)
        lte = self.get_isotime()
        timestamp = self.fields['aliases']['timestamp']
        query = {
            "_source": {
                "includes": includes,
                "excludes": excludes
            },
            "query": {
                "bool": {
                    "must": must,
                    "must_not": must_not,
                    "filter": {
                        "range": {
                            timestamp: {
                                "gte": gte,
                                "lte": lte
                            }
                        }
                    }
                }
            }
        }
        # Debug
        if args.debug:
            logger.debug(query)

        # get data from ElasticSearch
        self.df = self.es.Search(index, query).to_df()

        # add beacon_id
        tqdm.pandas(desc='add beacon_id')
        self.df['beacon_id'] = self.df[self.fields['beacon']
                                       ].progress_apply(lambda row: hash(tuple(row)), axis=1)
        self.df['beacon_freq'] = self.df.groupby(
            'beacon_id')['beacon_id'].transform('count').fillna(0).astype(int)
        self.high_freq = list(self.df[self.df.beacon_freq > self.min_occur].groupby(
            'beacon_id').groups.keys())

        # find beacons
        beacons = self.find_beacons()

        if beacons.empty:
            logger.info('No events detected.')
            return

        # Kibana
        if kbn['enable']:
            kibana = Kibana(kbn)
            payload = {
                'from_time': gte,
                'to_time': lte,
                'index_pattern_id': kbn['index_pattern_id'],
                'columns': self.fields['output']
            }

            beacons['url'] = beacons[self.fields['beacon']].apply(
                lambda row: self.create_url(row, payload, kibana), axis=1)

        beacons['create_time'] = self.get_isotime()
        beacons['from_time'] = gte
        beacons['to_time'] = lte
        beacons['period'] = self.period
        beacons['event_type'] = "beaconing"

        # Rename
        aliases = {v: k for k, v in self.fields['aliases'].items()}
        beacons.rename(aliases, axis=1, inplace=True)

        # Debug
        if args.debug:
            logger.debug(beacons)

        # Storage
        # Local
        if args.log:
            beacons.to_json(args.log, orient='records')
        elif storage['local']['enable']:
            path = storage['local']['path']
            beacons.to_json(path, orient='records')
        # ElasticSearch
        if storage['elastic'].get('path', False):
            pass

        # Notification
        if notification['slack']['enable']:
            webhook = notification['slack']['webhook']
            slack = Slack(webhook)

            text = 'New Alert'
            msg = beacons.to_dict(orient='records')
            for i in msg:
                t = []
                for k, v in i.items():
                    t.append(slack.section(k, v))
                slack.notify(text, t)

        if not beacons.empty:
            msg = 'Detected {} events.'.format(beacons.shape[0])
        logger.info(msg)


if __name__ == '__main__':
    beacon = HawkEye()
    beacon.analyze()
