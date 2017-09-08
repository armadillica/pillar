import argparse
import contextlib
import pathlib
import subprocess
import sys

BABEL_CONFIG = pathlib.Path('translations.cfg')


@contextlib.contextmanager
def create_messages_pot() -> pathlib.Path:
    """Extract the translatable strings from the source code

    This creates a temporary messages.pot file, to be used to init or
    update the translation .mo files.

    It works as a generator, yielding the temporarily created pot file.
    The messages.pot file will be deleted at the end of it if all went well.

    :return The path of the messages.pot file created.
    """
    if not BABEL_CONFIG.is_file():
        print("No translations config file found: %s" % (BABEL_CONFIG))
        sys.exit(-1)
        return

    messages_pot = pathlib.Path('messages.pot')
    subprocess.run(('pybabel', 'extract', '-F', BABEL_CONFIG, '-k', 'lazy_gettext', '-o', messages_pot, '.'))
    yield messages_pot
    messages_pot.unlink()


def init(locale):
    """
    Initialize the translations for a new language.
    """
    with create_messages_pot() as messages_pot:
        subprocess.run(('pybabel', 'init', '-i', messages_pot, '-d', 'translations', '-l', locale))


def update():
    """
    Update the strings to be translated.
    """
    with create_messages_pot() as messages_pot:
        subprocess.run(('pybabel', 'update', '-i', messages_pot, '-d', 'translations'))


def compile():
    """
    Compile the translation to be used.
    """
    if pathlib.Path('translations').is_dir():
        subprocess.run(('pybabel', 'compile','-d', 'translations'))
    else:
        print("No translations folder available")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description='Translate Pillar')

    parser.add_argument(
            'mode',
            type=str,
            help='Init once, update often, compile before deploying.',
            choices=['init', 'update', 'compile'])

    parser.add_argument(
            'languages',
            nargs='*',
            type=str,
            help='Languages to initialize: pt it es ...')

    args = parser.parse_args()
    if args.mode == 'init' and not args.languages:
        parser.error("init requires languages")

    return args


def main():
    """
    When calling from the setup.py entry-point we need to parse the arguments
    and init/update/compile the translations strings
    """
    args = parse_arguments()

    if args.mode == 'init':
        for language in args.languages:
            init(language)

    elif args.mode == 'update':
        update()

    else: # mode == 'compile'
        compile()


if __name__ == '__main__':
    main()

