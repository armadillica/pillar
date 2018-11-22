import copy

from pillar.api.search.queries import create_node_search, create_multi_node_search
from pillar.tests import AbstractPillarTest

EMPTY_QUERY = {
    "query": {
        "bool": {
            "must": [
                {
                    "bool": {}
                }
            ]
        }
    },
}

AGGREGATIONS = {
    "aggs": {
        "node_type": {
            "terms": {
                "field": "node_type"
            }
        },
        "media": {
            "terms": {
                "field": "media"
            }
        },
        "tags": {
            "terms": {
                "field": "tags"
            }
        },
        "is_free": {
            "terms": {
                "field": "is_free"
            }
        }
    }
}

SORTED_DESC_BY_CREATED = {
    "sort": [{
        "created_at": {"order": "desc"}
    }]
}

PAGE_1 = {
    "from": 0,
    "size": 10
}

IN_PROJECT = {
    "term": {
        "project.id": "MyProjectId"
    }
}

NODE_INDEX = {
    "index": ["test_nodes"]
}


class TestSearchNodesGlobal(AbstractPillarTest):
    def test_empty_query(self):
        with self.app.app_context():
            search = create_node_search(query='', terms={}, page=0)
            expected = {
                **EMPTY_QUERY,
                **AGGREGATIONS,
                **SORTED_DESC_BY_CREATED,
                **PAGE_1
            }

            self.assertEquals(expected, search.to_dict())

    def test_empty_query_page_2(self):
        with self.app.app_context():
            search = create_node_search(query='', terms={}, page=1)
            page_2 = copy.deepcopy(PAGE_1)
            page_2['from'] = 10

            expected = {
                **EMPTY_QUERY,
                **AGGREGATIONS,
                **SORTED_DESC_BY_CREATED,
                **page_2
            }

            self.assertEquals(expected, search.to_dict())

    def test_empty_query_with_terms(self):
        with self.app.app_context():
            terms = {
                'is_free': '0',
                'node_type': 'asset',
            }
            search = create_node_search(query='', terms=terms, page=0)
            query = copy.deepcopy(EMPTY_QUERY)
            query['query']['bool']['filter'] = [
                {
                    "term": {
                        "is_free": False
                    }
                },
                {
                    "term": {
                        "node_type": "asset"
                    }
                }
            ]

            expected = {
                **query,
                **AGGREGATIONS,
                **SORTED_DESC_BY_CREATED,
                **PAGE_1
            }

            self.assertEquals(expected, search.to_dict())

    def test_query(self):
        with self.app.app_context():
            search = create_node_search(query='is there life on mars?', terms={}, page=0)
            query = copy.deepcopy(EMPTY_QUERY)
            query['query']['bool']['must'] = [
                {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "name": "is there life on mars?"
                                }
                            },
                            {
                                "match": {
                                    "project.name": "is there life on mars?"
                                }
                            },
                            {
                                "match": {
                                    "user.name": "is there life on mars?"
                                }
                            },
                            {
                                "match": {
                                    "description": "is there life on mars?"
                                }
                            },
                            {
                                "term": {
                                    "media": "is there life on mars?"
                                }
                            },
                            {
                                "term": {
                                    "tags": "is there life on mars?"
                                }
                            }
                        ]
                    }
                }
            ]

            expected = {
                **query,
                **AGGREGATIONS,
                **PAGE_1
            }

            self.assertEquals(expected, search.to_dict())


class TestSearchNodesInProject(AbstractPillarTest):
    def test_empty_query(self):
        with self.app.app_context():
            search = create_node_search(query='', terms={}, page=0, project_id='MyProjectId')
            project_query = copy.deepcopy(EMPTY_QUERY)
            project_query['query']['bool']['filter'] = [IN_PROJECT]

            expected = {
                **project_query,
                **AGGREGATIONS,
                **SORTED_DESC_BY_CREATED,
                **PAGE_1
            }

            self.assertEquals(expected, search.to_dict())

    def test_empty_query_page_2(self):
        with self.app.app_context():
            search = create_node_search(query='', terms={}, page=1, project_id='MyProjectId')
            project_query = copy.deepcopy(EMPTY_QUERY)
            project_query['query']['bool']['filter'] = [IN_PROJECT]
            page_2 = copy.deepcopy(PAGE_1)
            page_2['from'] = 10

            expected = {
                **project_query,
                **AGGREGATIONS,
                **SORTED_DESC_BY_CREATED,
                **page_2
            }

            self.assertEquals(expected, search.to_dict())

    def test_empty_query_with_terms(self):
        with self.app.app_context():
            terms = {
                'is_free': '1',
                'media': 'video',
            }
            search = create_node_search(query='', terms=terms, page=1, project_id='MyProjectId')
            project_query = copy.deepcopy(EMPTY_QUERY)
            project_query['query']['bool']['filter'] = [
                IN_PROJECT,
                {
                    "term": {
                        "is_free": True
                    }
                },
                {
                    "term": {
                        "media": "video"
                    }
                }
            ]
            page_2 = copy.deepcopy(PAGE_1)
            page_2['from'] = 10

            expected = {
                **project_query,
                **AGGREGATIONS,
                **SORTED_DESC_BY_CREATED,
                **page_2
            }

            self.assertEquals(expected, search.to_dict())

    def test_query(self):
        with self.app.app_context():
            search = create_node_search(query='is there life on mars?', terms={}, page=0, project_id='MyProjectId')
            query = copy.deepcopy(EMPTY_QUERY)
            query['query']['bool']['filter'] = [IN_PROJECT]
            query['query']['bool']['must'] = [
                {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "name": "is there life on mars?"
                                }
                            },
                            {
                                "match": {
                                    "project.name": "is there life on mars?"
                                }
                            },
                            {
                                "match": {
                                    "user.name": "is there life on mars?"
                                }
                            },
                            {
                                "match": {
                                    "description": "is there life on mars?"
                                }
                            },
                            {
                                "term": {
                                    "media": "is there life on mars?"
                                }
                            },
                            {
                                "term": {
                                    "tags": "is there life on mars?"
                                }
                            }
                        ]
                    }
                }
            ]

            expected = {
                **query,
                **AGGREGATIONS,
                **PAGE_1
            }

            self.assertEquals(expected, search.to_dict())


class TestSearchMultiNodes(AbstractPillarTest):
    def test(self):
        with self.app.app_context():
            queries = [{
                'query': '',
                'terms': {},
                'page': 0,
                'project_id': ''
            }, {
                'query': '',
                'terms': {},
                'page': 1,
                'project_id': 'MyProjectId'
            }]
            search = create_multi_node_search(queries)

            first = {
                **EMPTY_QUERY,
                **AGGREGATIONS,
                **SORTED_DESC_BY_CREATED,
                **PAGE_1
            }
            project_query = copy.deepcopy(EMPTY_QUERY)
            project_query['query']['bool']['filter'] = [IN_PROJECT]
            page_2 = copy.deepcopy(PAGE_1)
            page_2['from'] = 10

            second = {
                ** project_query,
                **AGGREGATIONS,
                **SORTED_DESC_BY_CREATED,
                **page_2,
            }

            expected = [
                NODE_INDEX,
                first,
                NODE_INDEX,
                second
            ]

            self.assertEquals(expected, search.to_dict())
