# Python argparse (1/7)
source: https://github.com/python/cpython/blob/main/Doc/library/argparse.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
:mod:`!argparse` --- Parser for command-line options, arguments and subcommands
================================================================================

.. module:: argparse
   :synopsis: Command-line option and argument parsing library.

.. versionadded:: 3.2

**Source code:** :source:`Lib/argparse.py`

.. note::

While :mod:`!argparse` is the default recommended standard library module
   for implementing basic command line applications, authors with more
   exacting requirements for exactly how their command line applications
   behave may find it doesn't provide the necessary level of control.
   Refer to :ref:`choosing-an-argument-parser` for alternatives to
   consider when ``argparse`` doesn't support behaviors that the application
   requires (such as entirely disabling support for interspersed options and
   positional arguments, or accepting option parameter values that start
   with ``-`` even when they correspond to another defined option).

--------------

.. sidebar:: Tutorial

This page contains the API reference information. For a more gentle
   introduction to Python command-line parsing, have a look at the
   :ref:`argparse tutorial <argparse-tutorial>`.

The :mod:`!argparse` module makes it easy to write user-friendly command-line
interfaces. The program defines what arguments it requires, and :mod:`!argparse`
will figure out how to parse those out of :data:`sys.argv`.  The :mod:`!argparse`
module also automatically generates help and usage messages.  The module
will also issue errors when users give the program invalid arguments.

The :mod:`!argparse` module's support for command-line interfaces is built
around an instance of :class:`argparse.ArgumentParser`.  It is a container for
argument specifications and has options that apply to the parser as whole::

parser = argparse.ArgumentParser(
                       prog='ProgramName',
                       description='What the program does',
                       epilog='Text at the bottom of help')

The :meth:`ArgumentParser.add_argument` method attaches individual argument
specifications to the parser.  It supports positional arguments, options that
accept values, and on/off flags::

parser.add_argument('filename')           # positional argument
   parser.add_argument('-c', '--count')      # option that takes a value
   parser.add_argument('-v', '--verbose',
                       action='store_true')  # on/off flag

The :meth:`ArgumentParser.parse_args` method runs the parser and places
the extracted data in a :class:`argparse.Namespace` object::

args = parser.parse_args()
   print(args.filename, args.count, args.verbose)

.. note::
   If you're looking for a guide about how to upgrade :mod:`optparse` code
   to :mod:`!argparse`, see :ref:`Upgrading Optparse Code <upgrading-optparse-code>`.

ArgumentParser objects
----------------------

.. class:: ArgumentParser(prog=None, usage=None, description=None, \
                          epilog=None, parents=[], \
                          formatter_class=argparse.HelpFormatter, \
                          prefix_chars='-', fromfile_prefix_chars=None, \
                          argument_default=None, conflict_handler='error', \
                          add_help=True, allow_abbrev=True, exit_on_error=True, \
                          *, suggest_on_error=True, color=True)

Create a new :class:`ArgumentParser` object. All parameters should be passed
   as keyword arguments. Each parameter has its own more detailed description
   below, but in short they are:

* prog_ - The name of the program (default: generated from the ``__main__``
     module attributes and ``sys.argv[0]``)

* usage_ - The string describing the program usage (default: generated from
     arguments added to parser)

* description_ - Text to display before the argument help
     (by default, no text)

* epilog_ - Text to display after the argument help (by default, no text)

* parents_ - A list of :class:`ArgumentParser` objects whose arguments should
     also be included

* formatter_class_ - A class for customizing the help output

* prefix_chars_ - The set of characters that prefix optional arguments
     (default: '-')

* fromfile_prefix_chars_ - The set of characters that prefix files from
     which additional arguments should be read (default: ``None``)

* argument_default_ - The global default value for arguments
     (default: ``None``)

* conflict_handler_ - The strategy for resolving conflicting optionals
     (usually unnecessary)

* add_help_ - Add a ``-h/--help`` option to the parser (default: ``True``)

* allow_abbrev_ - Allows long options to be abbreviated if the
     abbreviation is unambiguous (default: ``True``)

* exit_on_error_ - Determines whether or not :class:`!ArgumentParser` exits with
     error info when an error occurs. (default: ``True``)

* suggest_on_error_ - Enables suggestions for mistyped argument choices
     and subparser names (default: ``True``)

* color_ - Allow color output (default: ``True``)

.. versionchanged:: 3.5
      *allow_abbrev* parameter was added.

.. versionchanged:: 3.8
      In previous versions, *allow_abbrev* also disabled grouping of short
      flags such as ``-vv`` to mean ``-v -v``.

.. versionchanged:: 3.9
      *exit_on_error* parameter was added.

.. versionchanged:: 3.14
      *suggest_on_error* and *color* parameters were added.

.. versionchanged:: 3.15
      *suggest_on_error* default changed to ``True``.

The following sections describe how each of these are used.

.. _prog:

prog
^^^^

By default, :class:`ArgumentParser` calculates the name of the program
to display in help messages depending on the way the Python interpreter was run:

* The :func:`base name <os.path.basename>` of ``sys.argv[0]`` if a file was
  passed as argument.
* The Python interpreter name followed by ``sys.argv[0]`` if a directory or
  a zipfile was passed as argument.
* The Python interpreter name followed by ``-m`` followed by the
  module or package name if the :option:`-m` option was used.

This default is almost always desirable because it will make the help messages
match the string that was used to invoke the program on the command line.
However, to change this default behavior, another value can be supplied using
the ``prog=`` argument to :class:`ArgumentParser`::

>>> parser = argparse.ArgumentParser(prog='myprogram')
   >>> parser.print_help()
   usage: myprogram [-h]

options:
    -h, --help  show this help message and exit

Note that the program name, whether determined from ``sys.argv[0]``,
from the ``__main__`` module attributes or from the
``prog=`` argument, is available to help messages using the ``%(prog)s`` format
specifier.

::

>>> parser = argparse.ArgumentParser(prog='myprogram')
   >>> parser.add_argument('--foo', help='foo of the %(prog)s program')
   >>> parser.print_help()
   usage: myprogram [-h] [--foo FOO]

options:
    -h, --help  show this help message and exit
    --foo FOO   foo of the myprogram program

.. versionchanged:: 3.14
   The default ``prog`` value now reflects how ``__main__`` was actually executed,
   rather than always being ``os.path.basename(sys.argv[0])``.

usage
^^^^^

By default, :class:`ArgumentParser` calculates the usage message from the
arguments it contains. The default message can be overridden with the
``usage=`` keyword argument::

>>> parser = argparse.ArgumentParser(prog='PROG', usage='%(prog)s [options]')
   >>> parser.add_argument('--foo', nargs='?', help='foo help')
   >>> parser.add_argument('bar', nargs='+', help='bar help')
   >>> parser.print_help()
   usage: PROG [options]

positional arguments:
    bar          bar help

options:
    -h, --help   show this help message and exit
    --foo [FOO]  foo help

The ``%(prog)s`` format specifier is available to fill in the program name in
your usage messages.

When a custom usage message is specified for the main parser, you may also want to
consider passing  the ``prog`` argument to :meth:`~ArgumentParser.add_subparsers`
or the ``prog`` and the ``usage`` arguments to
:meth:`~_SubParsersAction.add_parser`, to ensure consistent command prefixes and
usage information across subparsers.

.. _description:

description
^^^^^^^^^^^

Most calls to the :class:`ArgumentParser` constructor will use the
``description=`` keyword argument.  This argument gives a brief description of
what the program does and how it works.  In help messages, the description is
displayed between the command-line usage string and the help messages for the
various arguments.

By default, the description will be line-wrapped so that it fits within the
given space.  To change this behavior, see the formatter_class_ argument.

epilog
^^^^^^

Some programs like to display additional description of the program after the
description of the arguments.  Such text can be specified using the ``epilog=``
argument to :class:`ArgumentParser`::

>>> parser = argparse.ArgumentParser(
   ...     description='A foo that bars',
   ...     epilog="And that's how you'd foo a bar")
   >>> parser.print_help()
   usage: argparse.py [-h]

A foo that bars

options:
    -h, --help  show this help message and exit

And that's how you'd foo a bar

As with the description_ argument, the ``epilog=`` text is by default
line-wrapped, but this behavior can be adjusted with the formatter_class_
argument to :class:`ArgumentParser`.

parents
^^^^^^^

Sometimes, several parsers share a common set of arguments. Rather than
repeating the definitions of these arguments, a single parser with all the
shared arguments and passed to ``parents=`` argument to :class:`ArgumentParser`
can be used.  The ``parents=`` argument takes a list of :class:`ArgumentParser`
objects, collects all the positional and optional actions from them, and adds
these actions to the :class:`ArgumentParser` object being constructed::

>>> parent_parser = argparse.ArgumentParser(add_help=False)
   >>> parent_parser.add_argument('--parent', type=int)

>>> foo_parser = argparse.ArgumentParser(parents=[parent_parser])
   >>> foo_parser.add_argument('foo')
   >>> foo_parser.parse_args(['--parent', '2', 'XXX'])
   Namespace(foo='XXX', parent=2)

>>> bar_parser = argparse.ArgumentParser(parents=[parent_parser])
   >>> bar_parser.add_argument('--bar')
   >>> bar_parser.parse_args(['--bar', 'YYY'])
   Namespace(bar='YYY', parent=None)

Note that most parent parsers will specify ``add_help=False``.  Otherwise, the
:class:`ArgumentParser` will see two ``-h/--help`` options (one in the parent
and one in the child) and raise an error.

.. note::
   You must fully initialize the parsers before passing them via ``parents=``.
   If you change the parent parsers after the child parser, those changes will
   not be reflected in the child.

.. _formatter_class:

formatter_class
^^^^^^^^^^^^^^^

:class:`ArgumentParser` objects allow the help formatting to be customized by
specifying an alternate formatting class.  Currently, there are four such
classes:

.. class:: RawDescriptionHelpFormatter
           RawTextHelpFormatter
           ArgumentDefaultsHelpFormatter
           MetavarTypeHelpFormatter

:class:`RawDescriptionHelpFormatter` and :class:`RawTextHelpFormatter` give
more control over how textual descriptions are displayed.
By default, :class:`ArgumentParser` objects line-wrap the description_ and
epilog_ texts in command-line help messages::

>>> parser = argparse.ArgumentParser(
   ...     prog='PROG',
   ...     description='''this description
   ...         was indented weird
   ...             but that is okay''',
   ...     epilog='''
   ...             likewise for this epilog whose whitespace will
   ...         be cleaned up and whose words will be wrapped
   ...         across a couple lines''')
   >>> parser.print_help()
   usage: PROG [-h]

this description was indented weird but that is okay

options:
    -h, --help  show this help message and exit

likewise for this epilog whose whitespace will be cleaned up and whose words
   will be wrapped across a couple lines

Passing :class:`RawDescriptionHelpFormatter` as ``formatter_class=``
indicates that description_ and epilog_ are already correctly formatted and
should not be line-wrapped::

>>> parser = argparse.ArgumentParser(
   ...     prog='PROG',
   ...     formatter_class=argparse.RawDescriptionHelpFormatter,
   ...     description=textwrap.dedent('''\
   ...         Please do not mess up this text!
   ...         --------------------------------
   ...             I have indented it
   ...             exactly the way
   ...             I want it
   ...         '''))
   >>> parser.print_help()
   usage: PROG [-h]

Please do not mess up this text!
   --------------------------------
      I have indented it
      exactly the way
      I want it

options:
    -h, --help  show this help message and exit

:class:`RawTextHelpFormatter` maintains whitespace for all sorts of help text,
including argument descriptions. However, multiple newlines are replaced with
one. If you wish to preserve multiple blank lines, add spaces between the
newlines.

:class:`ArgumentDefaultsHelpFormatter` automatically adds information about
default values to each of the argument help messages::

>>> parser = argparse.ArgumentParser(
   ...     prog='PROG',
   ...     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
   >>> parser.add_argument('--foo', type=int, default=42, help='FOO!')
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
