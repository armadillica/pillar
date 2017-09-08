"""Commandline interface.

Run commands with 'flask <command>'
"""

import logging

from flask_script import Manager

from pillar import current_app
from pillar.cli.celery import manager_celery
from pillar.cli.maintenance import manager_maintenance
from pillar.cli.operations import manager_operations
from pillar.cli.setup import manager_setup

log = logging.getLogger(__name__)
manager = Manager(current_app)

manager.add_command('celery', manager_celery)
manager.add_command("maintenance", manager_maintenance)
manager.add_command("setup", manager_setup)
manager.add_command("operations", manager_operations)