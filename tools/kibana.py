'''
Author: Canon
Date: 2021-01-24 13:30:41
LastEditTime: 2021-02-20 14:05:52
LastEditors: Please set LastEditors
Description: In User Settings Edit
FilePath: /Code/Jupyter/Beacon/tools/kibana.py
'''

import json
import requests

import prison


class Kibana():
    def __init__(self, kibana):
        self.kibana = kibana

    def shorten_url(self, url):
        goto = self.kibana['url'] + '/goto/'
        api = self.kibana['url'] + "/api/shorten_url"
        headers = self.kibana['headers']
        payload = {'url': url}
        response = requests.post(api, headers=headers,
                                 json=payload, verify=False).json()
        short_url = goto + response["urlId"]
        return short_url

    def disover_global_state(self, from_time, to_time):
        return prison.dumps({
            'filters': [],
            'refreshInterval': {
                'pause': True,
                'value': 0
            },
            'time': {
                'from': from_time,
                'to': to_time
            }
        })

    def discover_app_state(self, query, index, columns, alias, filters):
        if not filters:
            app_filters = []
            for k, v in query.items():
                app_filters.append({
                    '$state': {
                        'store': 'appState'
                    },
                    'meta': {
                        'alias': alias,
                        'disabled': False,
                        'index': index,
                        'key': k,
                        'negate': False,
                        'params': {
                            'query': v
                        },
                        'type': 'phrase'
                    },
                    'query': {
                        'match_phrase': {
                            k: v
                        }
                    }
                })
        else:
            app_filters = [
                {
                    "$state": {
                        "store": "appState"
                    },
                    "meta": {
                        "alias": alias,
                        "disabled": False,
                        "index": index
                    },
                    "query": {
                        "bool": query
                    }
                }
            ]

        return prison.dumps({
            'columns': columns,
            'filters': app_filters,
            'index': index,
            'interval': 'auto'
        })

    def generate_discover_url(self, **kwargs):
        from_time = kwargs['from_time']
        to_time = kwargs['to_time']
        global_state = self.disover_global_state(from_time, to_time)

        query = kwargs['query']
        index = kwargs['index_pattern_id']
        columns = kwargs['columns']
        alias = kwargs.get('alias')
        filters = kwargs.get('filters')
        app_state = self.discover_app_state(
            query, index, columns, alias, filters)

        url = self.kibana['discover_url'].format(
            global_state=global_state, app_state=app_state)
        return url
