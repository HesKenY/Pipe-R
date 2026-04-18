# Python argparse (7/7)
source: https://github.com/python/cpython/blob/main/Doc/library/argparse.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
group = parser.add_argument_group('Group title', 'Group description')
     >>> exclusive_group = group.add_mutually_exclusive_group(required=True)
     >>> exclusive_group.add_argument('--foo', help='foo help')
     >>> exclusive_group.add_argument('--bar', help='bar help')
     >>> parser.print_help()
     usage: PROG [-h] (--foo FOO | --bar BAR)

options:
       -h, --help  show this help message and exit

Group title:
       Group description

--foo FOO   foo help
       --bar BAR   bar help

.. deprecated-removed:: 3.11 3.14
      Calling :meth:`add_argument_group` or :meth:`add_mutually_exclusive_group`
      on a mutually exclusive group now raises an exception. This nesting was
      never supported, often failed to work correctly, and was unintentionally
      exposed through inheritance.

Parser defaults
^^^^^^^^^^^^^^^

.. method:: ArgumentParser.set_defaults(**kwargs)

Most of the time, the attributes of the object returned by :meth:`parse_args`
   will be fully determined by inspecting the command-line arguments and the argument
   actions.  :meth:`set_defaults` allows some additional
   attributes that are determined without any inspection of the command line to
   be added::

>>> parser = argparse.ArgumentParser()
     >>> parser.add_argument('foo', type=int)
     >>> parser.set_defaults(bar=42, baz='badger')
     >>> parser.parse_args(['736'])
     Namespace(bar=42, baz='badger', foo=736)

Note that defaults can be set at both the parser level using :meth:`set_defaults`
   and at the argument level using :meth:`add_argument`. If both are called for the
   same argument, the last default set for an argument is used::

>>> parser = argparse.ArgumentParser()
     >>> parser.add_argument('--foo', default='bar')
     >>> parser.set_defaults(foo='spam')
     >>> parser.parse_args([])
     Namespace(foo='spam')

Parser-level defaults can be particularly useful when working with multiple
   parsers.  See the :meth:`~ArgumentParser.add_subparsers` method for an
   example of this type.

.. method:: ArgumentParser.get_default(dest)

Get the default value for a namespace attribute, as set by either
   :meth:`~ArgumentParser.add_argument` or by
   :meth:`~ArgumentParser.set_defaults`::

>>> parser = argparse.ArgumentParser()
     >>> parser.add_argument('--foo', default='badger')
     >>> parser.get_default('foo')
     'badger'

Printing help
^^^^^^^^^^^^^

In most typical applications, :meth:`~ArgumentParser.parse_args` will take
care of formatting and printing any usage or error messages.  However, several
formatting methods are available:

.. method:: ArgumentParser.print_usage(file=None)

Print a brief description of how the :class:`ArgumentParser` should be
   invoked on the command line.  If *file* is ``None``, :data:`sys.stdout` is
   assumed.

.. method:: ArgumentParser.print_help(file=None)

Print a help message, including the program usage and information about the
   arguments registered with the :class:`ArgumentParser`.  If *file* is
   ``None``, :data:`sys.stdout` is assumed.

There are also variants of these methods that simply return a string instead of
printing it:

.. method:: ArgumentParser.format_usage()

Return a string containing a brief description of how the
   :class:`ArgumentParser` should be invoked on the command line.

.. method:: ArgumentParser.format_help()

Return a string containing a help message, including the program usage and
   information about the arguments registered with the :class:`ArgumentParser`.

Partial parsing
^^^^^^^^^^^^^^^

.. method:: ArgumentParser.parse_known_args(args=None, namespace=None)

Sometimes a script only needs to handle a specific set of command-line
   arguments, leaving any unrecognized arguments for another script or program.
   In these cases, the :meth:`~ArgumentParser.parse_known_args` method can be
   useful.

This method works similarly to :meth:`~ArgumentParser.parse_args`, but it does
   not raise an error for extra, unrecognized arguments. Instead, it parses the
   known arguments and returns a two item tuple that contains the populated
   namespace and the list of any unrecognized arguments.

::

>>> parser = argparse.ArgumentParser()
      >>> parser.add_argument('--foo', action='store_true')
      >>> parser.add_argument('bar')
      >>> parser.parse_known_args(['--foo', '--badger', 'BAR', 'spam'])
      (Namespace(bar='BAR', foo=True), ['--badger', 'spam'])

.. warning::
   :ref:`Prefix matching <prefix-matching>` rules apply to
   :meth:`~ArgumentParser.parse_known_args`. The parser may consume an option even if it's just
   a prefix of one of its known options, instead of leaving it in the remaining
   arguments list.

Customizing file parsing
^^^^^^^^^^^^^^^^^^^^^^^^

.. method:: ArgumentParser.convert_arg_line_to_args(arg_line)

Arguments that are read from a file (see the *fromfile_prefix_chars*
   keyword argument to the :class:`ArgumentParser` constructor) are read one
   argument per line. :meth:`convert_arg_line_to_args` can be overridden for
   fancier reading.

This method takes a single argument *arg_line* which is a string read from
   the argument file.  It returns a list of arguments parsed from this string.
   The method is called once per line read from the argument file, in order.

A useful override of this method is one that treats each space-separated word
   as an argument.  The following example demonstrates how to do this::

class MyArgumentParser(argparse.ArgumentParser):
        def convert_arg_line_to_args(self, arg_line):
            return arg_line.split()

Exiting methods
^^^^^^^^^^^^^^^

.. method:: ArgumentParser.exit(status=0, message=None)

This method terminates the program, exiting with the specified *status*
   and, if given, it prints a *message* to :data:`sys.stderr` before that.
   The user can override this method to handle these steps differently::

class ErrorCatchingArgumentParser(argparse.ArgumentParser):
        def exit(self, status=0, message=None):
            if status:
                raise Exception(f'Exiting because of an error: {message}')
            exit(status)

.. method:: ArgumentParser.error(message)

This method prints a usage message, including the *message*, to
   :data:`sys.stderr` and terminates the program with a status code of 2.

Intermixed parsing
^^^^^^^^^^^^^^^^^^

.. method:: ArgumentParser.parse_intermixed_args(args=None, namespace=None)
.. method:: ArgumentParser.parse_known_intermixed_args(args=None, namespace=None)

A number of Unix commands allow the user to intermix optional arguments with
   positional arguments.  The :meth:`~ArgumentParser.parse_intermixed_args`
   and :meth:`~ArgumentParser.parse_known_intermixed_args` methods
   support this parsing style.

These parsers do not support all the :mod:`!argparse` features, and will raise
   exceptions if unsupported features are used.  In particular, subparsers,
   and mutually exclusive groups that include both
   optionals and positionals are not supported.

The following example shows the difference between
   :meth:`~ArgumentParser.parse_known_args` and
   :meth:`~ArgumentParser.parse_intermixed_args`: the former returns ``['2',
   '3']`` as unparsed arguments, while the latter collects all the positionals
   into ``rest``.  ::

>>> parser = argparse.ArgumentParser()
      >>> parser.add_argument('--foo')
      >>> parser.add_argument('cmd')
      >>> parser.add_argument('rest', nargs='*', type=int)
      >>> parser.parse_known_args('doit 1 --foo bar 2 3'.split())
      (Namespace(cmd='doit', foo='bar', rest=[1]), ['2', '3'])
      >>> parser.parse_intermixed_args('doit 1 --foo bar 2 3'.split())
      Namespace(cmd='doit', foo='bar', rest=[1, 2, 3])

:meth:`~ArgumentParser.parse_known_intermixed_args` returns a two item tuple
   containing the populated namespace and the list of remaining argument strings.
   :meth:`~ArgumentParser.parse_intermixed_args` raises an error if there are any
   remaining unparsed argument strings.

.. versionadded:: 3.7

Registering custom types or actions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. method:: ArgumentParser.register(registry_name, value, object)

Sometimes it's desirable to use a custom string in error messages to provide
   more user-friendly output. In these cases, :meth:`!register` can be used to
   register custom actions or types with a parser and allow you to reference the
   type by their registered name instead of their callable name.

The :meth:`!register` method accepts three arguments - a *registry_name*,
   specifying the internal registry where the object will be stored (e.g.,
   ``action``, ``type``), *value*, which is the key under which the object will
   be registered, and object, the callable to be registered.

The following example shows how to register a custom type with a parser::

>>> import argparse
      >>> parser = argparse.ArgumentParser()
      >>> parser.register('type', 'hexadecimal integer', lambda s: int(s, 16))
      >>> parser.add_argument('--foo', type='hexadecimal integer')
      _StoreAction(option_strings=['--foo'], dest='foo', nargs=None, const=None, default=None, type='hexadecimal integer', choices=None, required=False, help=None, metavar=None, deprecated=False)
      >>> parser.parse_args(['--foo', '0xFA'])
      Namespace(foo=250)
      >>> parser.parse_args(['--foo', '1.2'])
      usage: PROG [-h] [--foo FOO]
      PROG: error: argument --foo: invalid 'hexadecimal integer' value: '1.2'

Exceptions
----------

.. exception:: ArgumentError

An error from creating or using an argument (optional or positional).

The string value of this exception is the message, augmented with
   information about the argument that caused it.

.. exception:: ArgumentTypeError

Raised when something goes wrong converting a command line string to a type.

.. rubric:: Guides and Tutorials

.. toctree::
   :maxdepth: 1

../howto/argparse.rst
   ../howto/argparse-optparse.rst
