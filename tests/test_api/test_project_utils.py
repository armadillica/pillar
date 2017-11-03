# -*- encoding: utf-8 -*-

"""Unit tests for pillar.api.project.utils."""

import logging

from bson import ObjectId
from pillar.tests import AbstractPillarTest

log = logging.getLogger(__name__)


class ProjectUtilsTest(AbstractPillarTest):
    def test_project_id_from_url(self):
        self.enter_app_context()

        self.ensure_project_exists({'_id': ObjectId(24 * 'a'), 'url': 'project1'})
        self.ensure_project_exists({'_id': ObjectId(24 * 'b'), 'url': 'project2'})
        self.ensure_project_exists({'_id': ObjectId(24 * 'c'), 'url': 'project3'})

        from pillar.api.projects.utils import project_id

        pid1 = project_id('project1')
        pid2 = project_id('project2')
        pid3 = project_id('project3')

        self.assertEqual(ObjectId(24 * 'a'), pid1)
        self.assertEqual(ObjectId(24 * 'b'), pid2)
        self.assertEqual(ObjectId(24 * 'c'), pid3)
