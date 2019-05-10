import copy

from pillar.api.search import queries
from pillar.tests import AbstractPillarTest

SOURCE = {
    "_source": {
        "include": ["full_name", "objectID", "username"]
    }
}

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
        "roles": {
            "terms": {
                "field": "roles"
            }
        }
    }
}

PAGE_1 = {
    "from": 0,
    "size": 10
}


class TestSearchUsers(AbstractPillarTest):
    def test_empty_query(self):
        with self.app.app_context():
            search = queries.create_user_search(query='', terms={}, page=0)

            expected = {
                **SOURCE,
                **EMPTY_QUERY,
                **AGGREGATIONS,
                **PAGE_1
            }
            self.assertEqual(expected, search.to_dict())

    def test_query(self):
        with self.app.app_context():
            search = queries.create_user_search(query='Jens', terms={}, page=0)
            query = copy.deepcopy(EMPTY_QUERY)
            query['query']['bool']['must'] = [
                {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "username": "Jens"
                                }
                            },
                            {
                                "match": {
                                    "full_name": "Jens"
                                }
                            },
                            {
                                "match": {
                                    "email": {
                                        "query": "Jens",
                                        "boost": 1
                                    }
                                }
                            },
                            {
                                "term": {
                                    "username_exact": {
                                        "value": "Jens",
                                        "boost": 50
                                    }
                                }
                            }
                        ]
                    }
                }
            ]

            expected = {
                **SOURCE,
                **query,
                **AGGREGATIONS,
                **PAGE_1
            }
            self.assertEqual(expected, search.to_dict())

    def test_email_query(self):
        with self.app.app_context():
            search = queries.create_user_search(query='mail@mail.com', terms={}, page=0)
            query = copy.deepcopy(EMPTY_QUERY)
            query['query']['bool']['must'] = [
                {
                    "bool": {
                        "should": [
                            {
                                "term": {
                                    "email_exact": {
                                        "value": "mail@mail.com",
                                        "boost": 50
                                    }
                                }
                            },
                            {
                                "match": {
                                    "username": "mail@mail.com"
                                }
                            },
                            {
                                "match": {
                                    "full_name": "mail@mail.com"
                                }
                            },
                            {
                                "match": {
                                    "email": {
                                        "query": "mail@mail.com",
                                        "boost": 25
                                    }
                                }
                            },
                            {
                                "term": {
                                    "username_exact": {
                                        "value": "mail@mail.com",
                                        "boost": 50
                                    }
                                }
                            }
                        ]
                    }
                }
            ]

            expected = {
                **SOURCE,
                **query,
                **AGGREGATIONS,
                **PAGE_1
            }
            self.assertEqual(expected, search.to_dict())


class TestSearchUsersAdmin(AbstractPillarTest):
    def test_empty_query(self):
        with self.app.app_context():
            search = queries.create_user_admin_search(query='', terms={}, page=0)

            expected = {
                **EMPTY_QUERY,
                **AGGREGATIONS,
                **PAGE_1
            }
            self.assertEqual(expected, search.to_dict())

    def test_query(self):
        with self.app.app_context():
            search = queries.create_user_admin_search(query='Jens', terms={}, page=0)
            query = copy.deepcopy(EMPTY_QUERY)
            query['query']['bool']['must'] = [
                {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "username": "Jens"
                                }
                            },
                            {
                                "match": {
                                    "full_name": "Jens"
                                }
                            },
                            {
                                "match": {
                                    "email": {
                                        "query": "Jens",
                                        "boost": 1
                                    }
                                }
                            },
                            {
                                "term": {
                                    "username_exact": {
                                        "value": "Jens",
                                        "boost": 50
                                    }
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
            self.assertEqual(expected, search.to_dict())

    def test_terms(self):
        with self.app.app_context():
            search = queries.create_user_admin_search(query='', terms={'roles': 'Admin'}, page=0)
            query = copy.deepcopy(EMPTY_QUERY)
            query['query']['bool']['filter'] = [
                {
                    "term": {
                        "roles": "Admin"
                    }
                }
            ]

            expected = {
                **query,
                **AGGREGATIONS,
                **PAGE_1
            }
            self.assertEqual(expected, search.to_dict())

    def test_object_id_query(self):
        with self.app.app_context():
            search = queries.create_user_admin_search(query='563aca02c379cf0005e8e17d', terms={}, page=0)
            query = copy.deepcopy(EMPTY_QUERY)
            query['query']['bool']['must'] = [
                {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "username": "563aca02c379cf0005e8e17d"
                                }
                            },
                            {
                                "match": {
                                    "full_name": "563aca02c379cf0005e8e17d"
                                }
                            },
                            {
                                "match": {
                                    "email": {
                                        "query": "563aca02c379cf0005e8e17d",
                                        "boost": 1
                                    }
                                }
                            },
                            {
                                "term": {
                                    "username_exact": {
                                        "value": "563aca02c379cf0005e8e17d",
                                        "boost": 50
                                    }
                                }
                            },
                            {
                                "term": {
                                    "objectID": {
                                        "value": "563aca02c379cf0005e8e17d",
                                        "boost": 100
                                    }
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
            self.assertEqual(expected, search.to_dict())
