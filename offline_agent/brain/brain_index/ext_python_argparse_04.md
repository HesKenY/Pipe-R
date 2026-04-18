# Python argparse (4/7)
source: https://github.com/python/cpython/blob/main/Doc/library/argparse.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
to ``?`` or ``*``, the ``default`` value
is used when no command-line argument was present::

>>> parser = argparse.ArgumentParser()
   >>> parser.add_argument('foo', nargs='?', default=42)
   >>> parser.parse_args(['a'])
   Namespace(foo='a')
   >>> parser.parse_args([])
   Namespace(foo=42)

For required_ arguments, the ``default`` value is ignored. For example, this
applies to positional arguments with nargs_ values other than ``?`` or ``*``,
or optional arguments marked as ``required=True``.

Providing ``default=argparse.SUPPRESS`` causes no attribute to be added if the
command-line argument was not present::

>>> parser = argparse.ArgumentParser()
   >>> parser.add_argument('--foo', default=argparse.SUPPRESS)
   >>> parser.parse_args([])
   Namespace()
   >>> parser.parse_args(['--foo', '1'])
   Namespace(foo='1')

.. _argparse-type:

type
^^^^

By default, the parser reads command-line arguments in as simple
strings. However, quite often the command-line string should instead be
interpreted as another type, such as a :class:`float` or :class:`int`.  The
``type`` keyword for :meth:`~ArgumentParser.add_argument` allows any
necessary type-checking and type conversions to be performed.

If the type_ keyword is used with the default_ keyword, the type converter
is only applied if the default is a string.

The argument to ``type`` can be a callable that accepts a single string or
the name of a registered type (see :meth:`~ArgumentParser.register`)
If the function raises :exc:`ArgumentTypeError`, :exc:`TypeError`, or
:exc:`ValueError`, the exception is caught and a nicely formatted error
message is displayed. Other exception types are not handled.

Common built-in types and functions can be used as type converters:

.. testcode::

import argparse
   import pathlib

parser = argparse.ArgumentParser()
   parser.add_argument('count', type=int)
   parser.add_argument('distance', type=float)
   parser.add_argument('street', type=ascii)
   parser.add_argument('code_point', type=ord)
   parser.add_argument('datapath', type=pathlib.Path)

User defined functions can be used as well:

.. doctest::

>>> def hyphenated(string):
   ...     return '-'.join([word[:4] for word in string.casefold().split()])
   ...
   >>> parser = argparse.ArgumentParser()
   >>> _ = parser.add_argument('short_title', type=hyphenated)
   >>> parser.parse_args(['"The Tale of Two Cities"'])
   Namespace(short_title='"the-tale-of-two-citi')

The :func:`bool` function is not recommended as a type converter.  All it does
is convert empty strings to ``False`` and non-empty strings to ``True``.
This is usually not what is desired::

>>> parser = argparse.ArgumentParser()
   >>> _ = parser.add_argument('--verbose', type=bool)
   >>> parser.parse_args(['--verbose', 'False'])
   Namespace(verbose=True)

See :class:`BooleanOptionalAction` or ``action='store_true'`` for common
alternatives.

In general, the ``type`` keyword is a convenience that should only be used for
simple conversions that can only raise one of the three supported exceptions.
Anything with more interesting error-handling or resource management should be
done downstream after the arguments are parsed.

For example, JSON or YAML conversions have complex error cases that require
better reporting than can be given by the ``type`` keyword.  A
:exc:`~json.JSONDecodeError` would not be well formatted and a
:exc:`FileNotFoundError` exception would not be handled at all.

Even :class:`~argparse.FileType` has its limitations for use with the ``type``
keyword.  If one argument uses :class:`~argparse.FileType` and then a
subsequent argument fails, an error is reported but the file is not
automatically closed.  In this case, it would be better to wait until after
the parser has run and then use the :keyword:`with`-statement to manage the
files.

For type checkers that simply check against a fixed set of values, consider
using the choices_ keyword instead.

.. _choices:

choices
^^^^^^^

Some command-line arguments should be selected from a restricted set of values.
These can be handled by passing a sequence object as the *choices* keyword
argument to :meth:`~ArgumentParser.add_argument`.  When the command line is
parsed, argument values will be checked, and an error message will be displayed
if the argument was not one of the acceptable values::

>>> parser = argparse.ArgumentParser(prog='game.py')
   >>> parser.add_argument('move', choices=['rock', 'paper', 'scissors'])
   >>> parser.parse_args(['rock'])
   Namespace(move='rock')
   >>> parser.parse_args(['fire'])
   usage: game.py [-h] {rock,paper,scissors}
   game.py: error: argument move: invalid choice: 'fire' (choose from 'rock',
   'paper', 'scissors')

Any sequence can be passed as the *choices* value, so :class:`list` objects,
:class:`tuple` objects, and custom sequences are all supported.

Use of :class:`enum.Enum` is not recommended because it is difficult to
control its appearance in usage, help, and error messages.

Note that *choices* are checked after any type_
conversions have been performed, so objects in *choices*
should match the type_ specified. This can make *choices*
appear unfamiliar in usage, help, or error messages.

To keep *choices* user-friendly, consider a custom type wrapper that
converts and formats values, or omit type_ and handle conversion in
your application code.

Formatted choices override the default *metavar* which is normally derived
from *dest*.  This is usually what you want because the user never sees the
*dest* parameter.  If this display isn't desirable (perhaps because there are
many choices), just specify an explicit metavar_.

.. _required:

required
^^^^^^^^

In general, the :mod:`!argparse` module assumes that flags like ``-f`` and ``--bar``
indicate *optional* arguments, which can always be omitted at the command line.
To make an option *required*, ``True`` can be specified for the ``required=``
keyword argument to :meth:`~ArgumentParser.add_argument`::

>>> parser = argparse.ArgumentParser()
   >>> parser.add_argument('--foo', required=True)
   >>> parser.parse_args(['--foo', 'BAR'])
   Namespace(foo='BAR')
   >>> parser.parse_args([])
   usage: [-h] --foo FOO
   : error: the following arguments are required: --foo

As the example shows, if an option is marked as ``required``,
:meth:`~ArgumentParser.parse_args` will report an error if that option is not
present at the command line.

.. note::

Required options are generally considered bad form because users expect
    *options* to be *optional*, and thus they should be avoided when possible.

.. _help:

help
^^^^

The ``help`` value is a string containing a brief description of the argument.
When a user requests help (usually by using ``-h`` or ``--help`` at the
command line), these ``help`` descriptions will be displayed with each
argument.

The ``help`` strings can include various format specifiers to avoid repetition
of things like the program name or the argument default_.  The available
specifiers include the program name, ``%(prog)s`` and most keyword arguments to
:meth:`~ArgumentParser.add_argument`, e.g. ``%(default)s``, ``%(type)s``, etc.::

>>> parser = argparse.ArgumentParser(prog='frobble')
   >>> parser.add_argument('bar', nargs='?', type=int, default=42,
   ...                     help='the bar to %(prog)s (default: %(default)s)')
   >>> parser.print_help()
   usage: frobble [-h] [bar]

positional arguments:
    bar     the bar to frobble (default: 42)

options:
    -h, --help  show this help message and exit

As the help string supports %-formatting, if you want a literal ``%`` to appear
in the help string, you must escape it as ``%%``.

:mod:`!argparse` supports silencing the help entry for certain options, by
setting the ``help`` value to ``argparse.SUPPRESS``::

>>> parser = argparse.ArgumentParser(prog='frobble')
   >>> parser.add_argument('--foo', help=argparse.SUPPRESS)
   >>> parser.print_help()
   usage: frobble [-h]

options:
     -h, --help  show this help message and exit

.. _metavar:

metavar
^^^^^^^

When :class:`ArgumentParser` generates help messages, it needs some way to refer
to each expected argument.  By default, :class:`!ArgumentParser` objects use the dest_
value as the "name" of each object.  By default, for positional argument
actions, the dest_ value is used directly, and for optional argument actions,
the dest_ value is uppercased.  So, a single positional argument with
``dest='bar'`` will be referred to as ``bar``. A single
optional argument ``--foo`` that should be followed by a single command-line argument
will be referred to as ``FOO``.  An example::

>>> parser = argparse.ArgumentParser()
   >>> parser.add_argument('--foo')
   >>> parser.add_argument('bar')
   >>> parser.parse_args('X --foo Y'.split())
   Namespace(bar='X', foo='Y')
   >>> parser.print_help()
   usage:  [-h] [--foo FOO] bar

positional arguments:
    bar

options:
    -h, --help  show this help message and exit
    --foo FOO

An alternative name can be specified with ``metavar``::

>>> parser = argparse.ArgumentParser()
   >>> parser.add_argument('--foo', metavar='YYY')
   >>> parser.add_argument('bar', metavar='XXX')
   >>> parser.parse_args('X --foo Y'.split())
   Namespace(bar='X', foo='Y')
   >>> parser.print_help()
   usage:  [-h] [--foo YYY] XXX

positional arguments:
    XXX

options:
    -h, --help  show this help message and exit
    --foo YYY

Note that ``metavar`` only changes the *displayed* name - the name of the
attribute on the :meth:`~ArgumentParser.parse_args` object is still determined
by the dest_ value.

Different values of ``nargs`` may cause the metavar to be used multiple times.
Providing a tuple to ``metavar`` specifies a different display for each of the
arguments::

>>> parser = argparse.ArgumentParser(prog='PROG')
   >>> parser.add_argument('-x', nargs=2)
   >>> parser.add_argument('--foo', nargs=2, metavar=('bar', 'baz'))
   >>> parser.print_help()
   usage: PROG [-h] [-x X X] [--foo bar baz]

options:
    -h, --help     show this help message and exit
    -x X X
    --foo bar baz

.. _dest:

dest
^^^^

Most :class:`ArgumentParser` actions add some value as an attribute of the
object returned by :meth:`~ArgumentParser.parse_args`.  The name of this
attribute is determined by the ``dest`` keyword argument of
:meth:`~ArgumentParser.add_argument`.  For positional argument actions,
``dest`` is normally supplied as the first argument to
:meth:`~ArgumentParser.add_argument`::

>>> parser = argparse.ArgumentParser()
   >>> parser.add_argument('bar')
   >>> parser.parse_args(['XXX'])
   Namespace(bar='XXX')

For optional argument actions, the value of ``dest`` is normally inferred from
the option strings.  :class:`ArgumentParser` generates the value of ``dest`` by
taking the first double-dash long option string and stripping away the initial
``-`` characters.
If no double-dash long option strings were supplied, ``dest`` will be derived
from the first single-dash long option string by stripping the initial ``-``
character.
If no long option strings were supplied, ``dest`` will be derived from
the first short option string by stripping the initial ``-`` character.  Any
internal ``-`` characters will be converted to ``_`` characters to make sure
the string is a valid attribute name.  The examples below illustrate this
behavior::

>>> parser = argparse.ArgumentParser()
   >>> parser.add_argument('-f', '--foo-bar', '--foo')
   >>> parser.add_argument('-q', '-quz')
   >>> parser.add_argument('-x', '-y')
   >>> parser.parse_args('-f 1 -q 2 -x 3'.split())
   Namespace(foo_bar='1', quz='2', x='3')
   >>> parser.parse_args('--foo 1 -quz 2 -y 3'.split())
   Namespace(foo_bar='1', quz='2', x='2')

``dest`` allows a custom attribute name to be provided::

>>> parser = argparse.ArgumentParser()
   >>> parser.add_argument('--foo', dest='bar')
   >>> parser.parse_args('--foo XXX'.split())
   Namespace(bar='XXX')

.. versionchanged:: 3.15
   Single-dash long option now takes precedence over short options.

.. _deprecated:

deprecated
^^^^^^^^^^

During a project's lifetime, some arguments may need to be removed from the
command line. Before removing them, you should inform
your users that the arguments are deprecated and will be removed.
The ``deprecated`` keyword argument of
:meth:`~ArgumentParser.add_argument`, which defaults to ``False``,
specifies if the argument is deprecated and will be removed
in the future.
For arguments, if ``deprecated`` is ``True``, then a warning will be
printed to :data:`sys.stderr` when the argument is used::

>>> import argparse
   >>> parser = argparse.ArgumentParser(prog='snake.py')
   >>> parser.add_argument('--legs', default=0, type=int, deprecated=True)
   >>> parser.parse_args([])
   Namespace(legs=0)
   >>> parser.parse_args(['--legs', '4'])  # doctest: +SKIP
   snake.py: warning: option '--legs' is deprecated
   Namespace(legs=4)

.. versionadded:: 3.13

Action classes
^^^^^^^^^^^^^^

:class:`!Action` classes implement the Action API, a callable which returns a callable
which processes arguments from the command-line. Any object which follows
this API may be passed as the ``action`` parameter to
:meth:`~ArgumentParser.add_argument`.

.. class:: Action(option_strings, dest, nargs=None, const=None, default=None, \
                  type=None, choices=None, required=False, help=None, \
                  metavar=None)

:class:`!Action` objects are used by an :class:`ArgumentParser` to represent the information
   needed to parse a single argument from one or more strings from the
   command line. The :class:`!Action` class must accept the two positional arguments
   plus any keyword arguments passed to :meth:`ArgumentParser.add_argument`
   except for the ``action`` itself.
