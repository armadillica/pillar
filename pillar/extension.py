"""Pillar extensions support.

Each Pillar extension should create a subclass of PillarExtension, which
can then be registered to the application at app creation time:

    from pillar_server import PillarServer
    from attract_server import AttractExtension

    app = PillarServer('.')
    app.load_extension(AttractExtension(), url_prefix='/attract')
    app.process_extensions()  # Always process extensions after the last one is loaded.

    if __name__ == '__main__':
        app.run('::0', 5000)

"""

import abc
import typing

import flask
import pillarsdk


class PillarExtension(object, metaclass=abc.ABCMeta):
    # Set to True when your extension implements the project_settings() method.
    has_project_settings = False

    # Set to True when your extension implements the context_processor() method.
    has_context_processor = False

    # List of Celery task modules introduced by this extension.
    celery_task_modules: typing.List[str] = []

    # Set of user roles used/introduced by this extension.
    user_roles: typing.Set[str] = set()
    user_roles_indexable: typing.Set[str] = set()

    # User capabilities introduced by this extension. The final set of
    # capabilities is the union of all app-level and extension-level caps.
    user_caps: typing.Mapping[str, typing.FrozenSet] = {}

    @property
    @abc.abstractmethod
    def name(self):
        """The name of this extension.

        The name determines the path at which Eve exposes the extension's
        resources (/{extension name}/{resource name}), as well as the
        MongoDB collection in which those resources are stored
        ({extensions name}.{resource name}).

        :rtype: unicode
        """

    @property
    def icon(self) -> str:
        """Returns the icon HTML class, for use like i.pi-{{ext.icon}}

        Defaults to the extension name.
        """
        return self.name

    @abc.abstractmethod
    def flask_config(self):
        """Returns extension-specific defaults for the Flask configuration.

        Use this to set sensible default values for configuration settings
        introduced by the extension.

        :rtype: dict
        """

    @abc.abstractmethod
    def blueprints(self):
        """Returns the list of top-level blueprints for the extension.

        These blueprints will be mounted at the url prefix given to
        app.load_extension().

        :rtype: list of flask.Blueprint objects.
        """

    @abc.abstractmethod
    def eve_settings(self):
        """Returns extensions to the Eve settings.

        Currently only the DOMAIN key is used to insert new resources into
        Eve's configuration.

        :rtype: dict
        """

    @property
    def template_path(self):
        """Returns the path where templates for this extension are stored.

        Note that this path is not connected to any blueprint, so it is up to
        the extension to provide extension-unique subdirectories.
        """
        return None

    @property
    def static_path(self):
        """Returns the path where static files are stored.

        Registers an endpoint named 'static_<extension name>', to use like:
        `url_for('static_attract', filename='js/somefile.js')`

        May return None, in which case the extension will not be able to serve
        static files.
        """
        return None

    def setup_app(self, app):
        """Called during app startup, after all extensions have loaded."""

    def sidebar_links(self, project: pillarsdk.Project) -> str:
        """Returns the sidebar link(s) for the given projects.

        :returns: HTML as a string for the sidebar.
        """

        return ''

    def project_settings(self, project: pillarsdk.Project, **template_args: dict) -> flask.Response:
        """Renders the project settings page for this extension.

        Set YourExtension.has_project_settings = True and Pillar will call this function.

        :param project: the project for which to render the settings.
        :param template_args: additional template arguments.
        :returns: a Flask HTTP response
        """

    def context_processor(self) -> dict:
        """Returns a dictionary that gets injected into the Flask Jinja2 namespace.

        Set has_context_processor  to True when your extension implements this method.
        """

        return {}
