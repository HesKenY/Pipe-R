# Python argparse (2/7)
source: https://github.com/python/cpython/blob/main/Doc/library/argparse.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
lp='FOO!')
   >>> parser.add_argument('bar', nargs='*', default=[1, 2, 3], help='BAR!')
   >>> parser.print_help()
   usage: PROG [-h] [--foo FOO] [bar ...]

positional arguments:
    bar         BAR! (default: [1, 2, 3])

options:
    -h, --help  show this help message and exit
    --foo FOO   FOO! (default: 42)

:class:`MetavarTypeHelpFormatter` uses the name of the type_ argument for each
argument as the display name for its values (rather than using the dest_
as the regular formatter does)::

>>> parser = argparse.ArgumentParser(
   ...     prog='PROG',
   ...     formatter_class=argparse.MetavarTypeHelpFormatter)
   >>> parser.add_argument('--foo', type=int)
   >>> parser.add_argument('bar', type=float)
   >>> parser.print_help()
   usage: PROG [-h] [--foo int] float

positional arguments:
     float

options:
     -h, --help  show this help message and exit
     --foo int

prefix_chars
^^^^^^^^^^^^

Most command-line options will use ``-`` as the prefix, e.g. ``-f/--foo``.
Parsers that need to support different or additional prefix
characters, e.g. for options
like ``+f`` or ``/foo``, may specify them using the ``prefix_chars=`` argument
to the :class:`ArgumentParser` constructor::

>>> parser = argparse.ArgumentParser(prog='PROG', prefix_chars='-+')
   >>> parser.add_argument('+f')
   >>> parser.add_argument('++bar')
   >>> parser.parse_args('+f X ++bar Y'.split())
   Namespace(bar='Y', f='X')

The ``prefix_chars=`` argument defaults to ``'-'``. Supplying a set of
characters that does not include ``-`` will cause ``-f/--foo`` options to be
disallowed.

fromfile_prefix_chars
^^^^^^^^^^^^^^^^^^^^^

Sometimes, when dealing with a particularly long argument list, it
may make sense to keep the list of arguments in a file rather than typing it out
at the command line.  If the ``fromfile_prefix_chars=`` argument is given to the
:class:`ArgumentParser` constructor, then arguments that start with any of the
specified characters will be treated as files, and will be replaced by the
arguments they contain.  For example::

>>> with open('args.txt', 'w', encoding=sys.getfilesystemencoding()) as fp:
   ...     fp.write('-f\nbar')
   ...
   >>> parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
   >>> parser.add_argument('-f')
   >>> parser.parse_args(['-f', 'foo', '@args.txt'])
   Namespace(f='bar')

Arguments read from a file must be one per line by default (but see also
:meth:`~ArgumentParser.convert_arg_line_to_args`) and are treated as if they
were in the same place as the original file referencing argument on the command
line.  So in the example above, the expression ``['-f', 'foo', '@args.txt']``
is considered equivalent to the expression ``['-f', 'foo', '-f', 'bar']``.

.. note::

Empty lines are treated as empty strings (``''``), which are allowed as values but
   not as arguments. Empty lines that are read as arguments will result in an
   "unrecognized arguments" error.

:class:`ArgumentParser` uses :term:`filesystem encoding and error handler`
to read the file containing arguments.

The ``fromfile_prefix_chars=`` argument defaults to ``None``, meaning that
arguments will never be treated as file references.

.. versionchanged:: 3.12
   :class:`ArgumentParser` changed encoding and errors to read arguments files
   from default (e.g. :func:`locale.getpreferredencoding(False) <locale.getpreferredencoding>`
   and ``"strict"``) to the :term:`filesystem encoding and error handler`.
   Arguments file should be encoded in UTF-8 instead of ANSI Codepage on Windows.

argument_default
^^^^^^^^^^^^^^^^

Generally, argument defaults are specified either by passing a default to
:meth:`~ArgumentParser.add_argument` or by calling the
:meth:`~ArgumentParser.set_defaults` methods with a specific set of name-value
pairs.  Sometimes however, it may be useful to specify a single parser-wide
default for arguments.  This can be accomplished by passing the
``argument_default=`` keyword argument to :class:`ArgumentParser`.  For example,
to globally suppress attribute creation on :meth:`~ArgumentParser.parse_args`
calls, we supply ``argument_default=SUPPRESS``::

>>> parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
   >>> parser.add_argument('--foo')
   >>> parser.add_argument('bar', nargs='?')
   >>> parser.parse_args(['--foo', '1', 'BAR'])
   Namespace(bar='BAR', foo='1')
   >>> parser.parse_args([])
   Namespace()

.. _allow_abbrev:

allow_abbrev
^^^^^^^^^^^^

Normally, when you pass an argument list to the
:meth:`~ArgumentParser.parse_args` method of an :class:`ArgumentParser`,
it :ref:`recognizes abbreviations <prefix-matching>` of long options.

This feature can be disabled by setting ``allow_abbrev`` to ``False``::

>>> parser = argparse.ArgumentParser(prog='PROG', allow_abbrev=False)
   >>> parser.add_argument('--foobar', action='store_true')
   >>> parser.add_argument('--foonley', action='store_false')
   >>> parser.parse_args(['--foon'])
   usage: PROG [-h] [--foobar] [--foonley]
   PROG: error: unrecognized arguments: --foon

.. versionadded:: 3.5

conflict_handler
^^^^^^^^^^^^^^^^

:class:`ArgumentParser` objects do not allow two actions with the same option
string.  By default, :class:`ArgumentParser` objects raise an exception if an
attempt is made to create an argument with an option string that is already in
use::

>>> parser = argparse.ArgumentParser(prog='PROG')
   >>> parser.add_argument('-f', '--foo', help='old foo help')
   >>> parser.add_argument('--foo', help='new foo help')
   Traceback (most recent call last):
    ..
   ArgumentError: argument --foo: conflicting option string(s): --foo

Sometimes (e.g. when using parents_) it may be useful to simply override any
older arguments with the same option string.  To get this behavior, the value
``'resolve'`` can be supplied to the ``conflict_handler=`` argument of
:class:`ArgumentParser`::

>>> parser = argparse.ArgumentParser(prog='PROG', conflict_handler='resolve')
   >>> parser.add_argument('-f', '--foo', help='old foo help')
   >>> parser.add_argument('--foo', help='new foo help')
   >>> parser.print_help()
   usage: PROG [-h] [-f FOO] [--foo FOO]

options:
    -h, --help  show this help message and exit
    -f FOO      old foo help
    --foo FOO   new foo help

Note that :class:`ArgumentParser` objects only remove an action if all of its
option strings are overridden.  So, in the example above, the old ``-f/--foo``
action is retained as the ``-f`` action, because only the ``--foo`` option
string was overridden.

add_help
^^^^^^^^

By default, :class:`ArgumentParser` objects add an option which simply displays
the parser's help message. If ``-h`` or ``--help`` is supplied at the command
line, the :class:`!ArgumentParser` help will be printed.

Occasionally, it may be useful to disable the addition of this help option.
This can be achieved by passing ``False`` as the ``add_help=`` argument to
:class:`ArgumentParser`::

>>> parser = argparse.ArgumentParser(prog='PROG', add_help=False)
   >>> parser.add_argument('--foo', help='foo help')
   >>> parser.print_help()
   usage: PROG [--foo FOO]

options:
    --foo FOO  foo help

The help option is typically ``-h/--help``. The exception to this is
if the ``prefix_chars=`` is specified and does not include ``-``, in
which case ``-h`` and ``--help`` are not valid options.  In
this case, the first character in ``prefix_chars`` is used to prefix
the help options::

>>> parser = argparse.ArgumentParser(prog='PROG', prefix_chars='+/')
   >>> parser.print_help()
   usage: PROG [+h]

options:
     +h, ++help  show this help message and exit

exit_on_error
^^^^^^^^^^^^^

Normally, when you pass an invalid argument list to the :meth:`~ArgumentParser.parse_args`
method of an :class:`ArgumentParser`, it will print a *message* to :data:`sys.stderr` and exit with a status
code of 2.

If the user would like to catch errors manually, the feature can be enabled by setting
``exit_on_error`` to ``False``::

>>> parser = argparse.ArgumentParser(exit_on_error=False)
   >>> parser.add_argument('--integers', type=int)
   _StoreAction(option_strings=['--integers'], dest='integers', nargs=None, const=None, default=None, type=<class 'int'>, choices=None, help=None, metavar=None)
   >>> try:
   ...     parser.parse_args('--integers a'.split())
   ... except argparse.ArgumentError:
   ...     print('Catching an argumentError')
   ...
   Catching an argumentError

.. versionadded:: 3.9

suggest_on_error
^^^^^^^^^^^^^^^^

By default, when a user passes an invalid argument choice or subparser name,
:class:`ArgumentParser` will exit with error info and provide suggestions for
mistyped arguments. The error message will list the permissible argument
choices (if specified) or subparser names, along with a "maybe you meant"
suggestion if a close match is found. Note that this only applies for arguments
when the choices specified are strings::

>>> parser = argparse.ArgumentParser(suggest_on_error=True)
   >>> parser.add_argument('--action', choices=['debug', 'dryrun'])
   >>> parser.parse_args(['--action', 'debugg'])
   usage: tester.py [-h] [--action {debug,dryrun}]
   tester.py: error: argument --action: invalid choice: 'debugg', maybe you meant 'debug'? (choose from debug, dryrun)

You can disable suggestions by setting ``suggest_on_error`` to ``False``.

.. versionadded:: 3.14
.. versionchanged:: 3.15
   Changed default value of ``suggest_on_error`` from ``False`` to ``True``.

color
^^^^^

By default, the help message is printed in color using `ANSI escape sequences
<https://en.wikipedia.org/wiki/ANSI_escape_code>`__.
If you want plain text help messages, you can disable this :ref:`in your local
environment <using-on-controlling-color>`, or in the argument parser itself
by setting ``color`` to ``False``::

>>> parser = argparse.ArgumentParser(description='Process some integers.',
   ...                                  color=False)
   >>> parser.add_argument('--action', choices=['sum', 'max'])
   >>> parser.add_argument('integers', metavar='N', type=int, nargs='+',
   ...                     help='an integer for the accumulator')
   >>> parser.parse_args(['--help'])

Note that when ``color=True``, colored output depends on both environment
variables and terminal capabilities.  However, if ``color=False``, colored
output is always disabled, even if environment variables like ``FORCE_COLOR``
are set.

.. versionadded:: 3.14

To highlight inline code in your description or epilog text, you can use
backticks::

>>> parser = argparse.ArgumentParser(
   ...     formatter_class=argparse.RawDescriptionHelpFormatter,
   ...     epilog='''Examples:
   ...   `python -m myapp --verbose`
   ...   `python -m myapp --config settings.json`
   ... ''')

When colors are enabled, the text inside backticks will be displayed in a
distinct color to help examples stand out. When colors are disabled, backticks
are preserved as-is, which is readable in plain text.

.. note::

Backtick markup only applies to description and epilog text. It does not
   apply to individual argument ``help`` strings.

.. versionadded:: 3.15

The add_argument() method
-------------------------

.. method:: ArgumentParser.add_argument(name or flags..., *, [action], [nargs], \
                           [const], [default], [type], [choices], [required], \
                           [help], [metavar], [dest], [deprecated])

Define how a single command-line argument should be parsed.  Each parameter
   has its own more detailed description below, but in short they are:

* `name or flags`_ - Either a name or a list of option strings, e.g. ``'foo'``
     or ``'-f', '--foo'``.

* action_ - The basic type of action to be taken when this argument is
     encountered at the command line.

* nargs_ - The number of command-line arguments that should be consumed.

* const_ - A constant value required by some action_ and nargs_ selections.

* default_ - The value produced if the argument is absent from the
     command line and if it is absent from the namespace object.

* type_ - The type to which the command-line argument should be converted.

* choices_ - A sequence of the allowable values for the argument.

* required_ - Whether or not the command-line option may be omitted
     (optionals only).

* help_ - A brief description of what the argument does.

* metavar_ - A name for the argument in usage messages.

* dest_ - The name of the attribute to be added to the object returned by
     :meth:`parse_args`.

* deprecated_ - Whether or not use of the argument is deprecated.

The method returns an :class:`Action` object representing the argument.

The following sections describe how each of these are used.

.. _`name or flags`:

name or flags
^^^^^^^^^^^^^

The :meth:`~ArgumentParser.add_argument` method must know whether an optional
argument, like ``-f`` or ``--foo``, or a positional argument, like a list of
filenames, is expected.  The first arguments passed to
:meth:`~ArgumentParser.add_argument` must therefore be either a series of
flags, or a simple argument name.

For example, an optional argument could be created like::

>>> parser.add_argument('-f', '--foo')

while a positional argument could be created like::

>>> parser.add_argument('bar')

When :meth:`~ArgumentParser.parse_args` is called, optional arguments will be
identified by the ``-`` prefix, and the remaining arguments will be assumed to
be positional::

>>> parser = argparse.ArgumentParser(prog='PROG')
   >>> parser.add_argument('-f', '--foo')
   >>> parser.add_argument('bar')
   >>> parser.parse_args(['BAR'])
   Namespace(bar='BAR', foo=None)
   >>> parser.parse_args(['BAR', '--foo', 'FOO'])
   Namespace(bar='BAR', foo='FOO')
   >>> parser.parse_args(['--foo', 'FOO'])
   usage: PROG [-h] [-f FOO] bar
   PROG: error: the following arguments are required: bar
