# Python argparse (5/7)
source: https://github.com/python/cpython/blob/main/Doc/library/argparse.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
None, const=None, default=None, \
                  type=None, choices=None, required=False, help=None, \
                  metavar=None)

:class:`!Action` objects are used by an :class:`ArgumentParser` to represent the information
   needed to parse a single argument from one or more strings from the
   command line. The :class:`!Action` class must accept the two positional arguments
   plus any keyword arguments passed to :meth:`ArgumentParser.add_argument`
   except for the ``action`` itself.

Instances of :class:`!Action` (or return value of any callable to the
   ``action`` parameter) should have attributes :attr:`!dest`,
   :attr:`!option_strings`, :attr:`!default`, :attr:`!type`, :attr:`!required`,
   :attr:`!help`, etc. defined. The easiest way to ensure these attributes
   are defined is to call :meth:`!Action.__init__`.

.. method:: __call__(parser, namespace, values, option_string=None)

:class:`!Action` instances should be callable, so subclasses must override the
      :meth:`!__call__` method, which should accept four parameters:

* *parser* - The :class:`ArgumentParser` object which contains this action.

* *namespace* - The :class:`Namespace` object that will be returned by
        :meth:`~ArgumentParser.parse_args`.  Most actions add an attribute to this
        object using :func:`setattr`.

* *values* - The associated command-line arguments, with any type conversions
        applied.  Type conversions are specified with the type_ keyword argument to
        :meth:`~ArgumentParser.add_argument`.

* *option_string* - The option string that was used to invoke this action.
        The ``option_string`` argument is optional, and will be absent if the action
        is associated with a positional argument.

The :meth:`!__call__` method may perform arbitrary actions, but will typically set
      attributes on the ``namespace`` based on ``dest`` and ``values``.

.. method:: format_usage()

:class:`!Action` subclasses can define a :meth:`!format_usage` method that takes no argument
      and return a string which will be used when printing the usage of the program.
      If such method is not provided, a sensible default will be used.

.. class:: BooleanOptionalAction

A subclass of :class:`Action` for handling boolean flags with positive
   and negative options. Adding a single argument such as ``--foo`` automatically
   creates both ``--foo`` and ``--no-foo`` options, storing ``True`` and ``False``
   respectively::

>>> import argparse
       >>> parser = argparse.ArgumentParser()
       >>> parser.add_argument('--foo', action=argparse.BooleanOptionalAction)
       >>> parser.parse_args(['--no-foo'])
       Namespace(foo=False)

Single-dash long options are also supported.
   For example, negative option ``-nofoo`` is automatically added for
   positive option ``-foo``.
   But no additional options are added for short options such as ``-f``.

.. versionadded:: 3.9

.. versionchanged:: 3.15
      Added support for single-dash options.

Added support for alternate prefix_chars_.

The parse_args() method
-----------------------

.. method:: ArgumentParser.parse_args(args=None, namespace=None)

Convert argument strings to objects and assign them as attributes of the
   namespace.  Return the populated namespace.

Previous calls to :meth:`add_argument` determine exactly what objects are
   created and how they are assigned. See the documentation for
   :meth:`!add_argument` for details.

* args_ - List of strings to parse.  The default is taken from
     :data:`sys.argv`.

* namespace_ - An object to take the attributes.  The default is a new empty
     :class:`Namespace` object.

Option value syntax
^^^^^^^^^^^^^^^^^^^

The :meth:`~ArgumentParser.parse_args` method supports several ways of
specifying the value of an option (if it takes one).  In the simplest case, the
option and its value are passed as two separate arguments::

>>> parser = argparse.ArgumentParser(prog='PROG')
   >>> parser.add_argument('-x')
   >>> parser.add_argument('--foo')
   >>> parser.parse_args(['-x', 'X'])
   Namespace(foo=None, x='X')
   >>> parser.parse_args(['--foo', 'FOO'])
   Namespace(foo='FOO', x=None)

For long options (options with names longer than a single character), the option
and value can also be passed as a single command-line argument, using ``=`` to
separate them::

>>> parser.parse_args(['--foo=FOO'])
   Namespace(foo='FOO', x=None)

For short options (options only one character long), the option and its value
can be concatenated::

>>> parser.parse_args(['-xX'])
   Namespace(foo=None, x='X')

Several short options can be joined together, using only a single ``-`` prefix,
as long as only the last option (or none of them) requires a value::

>>> parser = argparse.ArgumentParser(prog='PROG')
   >>> parser.add_argument('-x', action='store_true')
   >>> parser.add_argument('-y', action='store_true')
   >>> parser.add_argument('-z')
   >>> parser.parse_args(['-xyzZ'])
   Namespace(x=True, y=True, z='Z')

Invalid arguments
^^^^^^^^^^^^^^^^^

While parsing the command line, :meth:`~ArgumentParser.parse_args` checks for a
variety of errors, including ambiguous options, invalid types, invalid options,
wrong number of positional arguments, etc.  When it encounters such an error,
it exits and prints the error along with a usage message::

>>> parser = argparse.ArgumentParser(prog='PROG')
   >>> parser.add_argument('--foo', type=int)
   >>> parser.add_argument('bar', nargs='?')

>>> # invalid type
   >>> parser.parse_args(['--foo', 'spam'])
   usage: PROG [-h] [--foo FOO] [bar]
   PROG: error: argument --foo: invalid int value: 'spam'

>>> # invalid option
   >>> parser.parse_args(['--bar'])
   usage: PROG [-h] [--foo FOO] [bar]
   PROG: error: no such option: --bar

>>> # wrong number of arguments
   >>> parser.parse_args(['spam', 'badger'])
   usage: PROG [-h] [--foo FOO] [bar]
   PROG: error: extra arguments found: badger

Arguments containing ``-``
^^^^^^^^^^^^^^^^^^^^^^^^^^

The :meth:`~ArgumentParser.parse_args` method attempts to give errors whenever
the user has clearly made a mistake, but some situations are inherently
ambiguous.  For example, the command-line argument ``-1`` could either be an
attempt to specify an option or an attempt to provide a positional argument.
The :meth:`~ArgumentParser.parse_args` method is cautious here: positional
arguments may only begin with ``-`` if they look like negative numbers and
there are no options in the parser that look like negative numbers::

>>> parser = argparse.ArgumentParser(prog='PROG')
   >>> parser.add_argument('-x')
   >>> parser.add_argument('foo', nargs='?')

>>> # no negative number options, so -1 is a positional argument
   >>> parser.parse_args(['-x', '-1'])
   Namespace(foo=None, x='-1')

>>> # no negative number options, so -1 and -5 are positional arguments
   >>> parser.parse_args(['-x', '-1', '-5'])
   Namespace(foo='-5', x='-1')

>>> parser = argparse.ArgumentParser(prog='PROG')
   >>> parser.add_argument('-1', dest='one')
   >>> parser.add_argument('foo', nargs='?')

>>> # negative number options present, so -1 is an option
   >>> parser.parse_args(['-1', 'X'])
   Namespace(foo=None, one='X')

>>> # negative number options present, so -2 is an option
   >>> parser.parse_args(['-2'])
   usage: PROG [-h] [-1 ONE] [foo]
   PROG: error: no such option: -2

>>> # negative number options present, so both -1s are options
   >>> parser.parse_args(['-1', '-1'])
   usage: PROG [-h] [-1 ONE] [foo]
   PROG: error: argument -1: expected one argument

If you have positional arguments that must begin with ``-`` and don't look
like negative numbers, you can insert the pseudo-argument ``'--'`` which tells
:meth:`~ArgumentParser.parse_args` that everything after that is a positional
argument::

>>> parser.parse_args(['--', '-f'])
   Namespace(foo='-f', one=None)

See also :ref:`the argparse howto on ambiguous arguments <specifying-ambiguous-arguments>`
for more details.

.. _prefix-matching:

Argument abbreviations (prefix matching)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :meth:`~ArgumentParser.parse_args` method :ref:`by default <allow_abbrev>`
allows long options to be abbreviated to a prefix, if the abbreviation is
unambiguous (the prefix matches a unique option)::

>>> parser = argparse.ArgumentParser(prog='PROG')
   >>> parser.add_argument('-bacon')
   >>> parser.add_argument('-badger')
   >>> parser.parse_args('-bac MMM'.split())
   Namespace(bacon='MMM', badger=None)
   >>> parser.parse_args('-bad WOOD'.split())
   Namespace(bacon=None, badger='WOOD')
   >>> parser.parse_args('-ba BA'.split())
   usage: PROG [-h] [-bacon BACON] [-badger BADGER]
   PROG: error: ambiguous option: -ba could match -badger, -bacon

An error is produced for arguments that could produce more than one options.
This feature can be disabled by setting :ref:`allow_abbrev` to ``False``.

.. _args:

Beyond ``sys.argv``
^^^^^^^^^^^^^^^^^^^

Sometimes it may be useful to have an :class:`ArgumentParser` parse arguments other than those
of :data:`sys.argv`.  This can be accomplished by passing a list of strings to
:meth:`~ArgumentParser.parse_args`.  This is useful for testing at the
interactive prompt::

>>> parser = argparse.ArgumentParser()
   >>> parser.add_argument(
   ...     'integers', metavar='int', type=int, choices=range(10),
   ...     nargs='+', help='an integer in the range 0..9')
   >>> parser.add_argument(
   ...     '--sum', dest='accumulate', action='store_const', const=sum,
   ...     default=max, help='sum the integers (default: find the max)')
   >>> parser.parse_args(['1', '2', '3', '4'])
   Namespace(accumulate=<built-in function max>, integers=[1, 2, 3, 4])
   >>> parser.parse_args(['1', '2', '3', '4', '--sum'])
   Namespace(accumulate=<built-in function sum>, integers=[1, 2, 3, 4])

.. _namespace:

The Namespace object
^^^^^^^^^^^^^^^^^^^^

.. class:: Namespace

Simple class used by default by :meth:`~ArgumentParser.parse_args` to create
   an object holding attributes and return it.

This class is deliberately simple, just an :class:`object` subclass with a
   readable string representation. If you prefer to have dict-like view of the
   attributes, you can use the standard Python idiom, :func:`vars`::

>>> parser = argparse.ArgumentParser()
      >>> parser.add_argument('--foo')
      >>> args = parser.parse_args(['--foo', 'BAR'])
      >>> vars(args)
      {'foo': 'BAR'}

It may also be useful to have an :class:`ArgumentParser` assign attributes to an
   already existing object, rather than a new :class:`Namespace` object.  This can
   be achieved by specifying the ``namespace=`` keyword argument::

>>> class C:
      ...     pass
      ...
      >>> c = C()
      >>> parser = argparse.ArgumentParser()
      >>> parser.add_argument('--foo')
      >>> parser.parse_args(args=['--foo', 'BAR'], namespace=c)
      >>> c.foo
      'BAR'

Other utilities
---------------

Subcommands
^^^^^^^^^^^^

.. method:: ArgumentParser.add_subparsers(*, [title], [description], [prog], \
                                          [parser_class], [action], \
                                          [dest], [required], \
                                          [help], [metavar])

Many programs split up their functionality into a number of subcommands,
   for example, the ``svn`` program can invoke subcommands like ``svn
   checkout``, ``svn update``, and ``svn commit``.  Splitting up functionality
   this way can be a particularly good idea when a program performs several
   different functions which require different kinds of command-line arguments.
   :class:`ArgumentParser` supports the creation of such subcommands with the
   :meth:`!add_subparsers` method.  The :meth:`!add_subparsers` method is normally
   called with no arguments and returns a special action object.  This object
   has a single method, :meth:`~_SubParsersAction.add_parser`, which takes a
   command name and any :class:`!ArgumentParser` constructor arguments, and
   returns an :class:`!ArgumentParser` object that can be modified as usual.

Description of parameters:

* *title* - title for the sub-parser group in help output; by default
     "subcommands" if description is provided, otherwise uses title for
     positional arguments

* *description* - description for the sub-parser group in help output, by
     default ``None``

* *prog* - usage information that will be displayed with subcommand help,
     by default the name of the program and any positional arguments before the
     subparser argument

* *parser_class* - class which will be used to create sub-parser instances, by
     default the class of the current parser (e.g. :class:`ArgumentParser`)

* action_ - the basic type of action to be taken when this argument is
     encountered at the command line

* dest_ - name of the attribute under which subcommand name will be
     stored; by default ``None`` and no value is stored

* required_ - Whether or not a subcommand must be provided, by default
     ``False`` (added in 3.7)

* help_ - help for sub-parser group in help output, by default ``None``

* metavar_ - string presenting available subcommands in help; by default it
     is ``None`` and presents subcommands in form {cmd1, cmd2, ..}

Some example usage::
