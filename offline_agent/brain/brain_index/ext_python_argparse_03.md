# Python argparse (3/7)
source: https://github.com/python/cpython/blob/main/Doc/library/argparse.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
ed by the ``-`` prefix, and the remaining arguments will be assumed to
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

By default, :mod:`!argparse` automatically handles the internal naming and
display names of arguments, simplifying the process without requiring
additional configuration.
As such, you do not need to specify the dest_ and metavar_ parameters.
For optional arguments, the dest_ parameter defaults to the argument name, with
underscores ``_`` replacing hyphens ``-``. The metavar_ parameter defaults to
the upper-cased name. For example::

>>> parser = argparse.ArgumentParser(prog='PROG')
   >>> parser.add_argument('--foo-bar')
   >>> parser.parse_args(['--foo-bar', 'FOO-BAR'])
   Namespace(foo_bar='FOO-BAR')
   >>> parser.print_help()
   usage:  [-h] [--foo-bar FOO-BAR]

optional arguments:
    -h, --help  show this help message and exit
    --foo-bar FOO-BAR

.. _action:

action
^^^^^^

:class:`ArgumentParser` objects associate command-line arguments with actions.  These
actions can do just about anything with the command-line arguments associated with
them, though most actions simply add an attribute to the object returned by
:meth:`~ArgumentParser.parse_args`.  The ``action`` keyword argument specifies
how the command-line arguments should be handled. The supplied actions are:

* ``'store'`` - This just stores the argument's value.  This is the default
  action.

* ``'store_const'`` - This stores the value specified by the const_ keyword
  argument; note that the const_ keyword argument defaults to ``None``.  The
  ``'store_const'`` action is most commonly used with optional arguments that
  specify some sort of flag.  For example::

>>> parser = argparse.ArgumentParser()
    >>> parser.add_argument('--foo', action='store_const', const=42)
    >>> parser.parse_args(['--foo'])
    Namespace(foo=42)

* ``'store_true'`` and ``'store_false'`` - These are special cases of
  ``'store_const'`` that respectively store the values ``True`` and ``False``
  with default values of ``False`` and
  ``True``::

>>> parser = argparse.ArgumentParser()
    >>> parser.add_argument('--foo', action='store_true')
    >>> parser.add_argument('--bar', action='store_false')
    >>> parser.add_argument('--baz', action='store_false')
    >>> parser.parse_args('--foo --bar'.split())
    Namespace(foo=True, bar=False, baz=True)

* ``'append'`` - This appends each argument value to a list.
  It is useful for allowing an option to be specified multiple times.
  If the default value is a non-empty list, the parsed value will start
  with the default list's elements and any values from the command line
  will be appended after those default values. Example usage::

>>> parser = argparse.ArgumentParser()
    >>> parser.add_argument('--foo', action='append', default=['0'])
    >>> parser.parse_args('--foo 1 --foo 2'.split())
    Namespace(foo=['0', '1', '2'])

* ``'append_const'`` - This appends the value specified by
  the const_ keyword argument to a list; note that the const_ keyword
  argument defaults to ``None``. The ``'append_const'`` action is typically
  useful when multiple arguments need to store constants to the same list. For
  example::

>>> parser = argparse.ArgumentParser()
    >>> parser.add_argument('--str', dest='types', action='append_const', const=str)
    >>> parser.add_argument('--int', dest='types', action='append_const', const=int)
    >>> parser.parse_args('--str --int'.split())
    Namespace(types=[<class 'str'>, <class 'int'>])

* ``'extend'`` - This appends each item from a multi-value
  argument to a list.
  The ``'extend'`` action is typically used with the nargs_ keyword argument
  value ``'+'`` or ``'*'``.
  Note that when nargs_ is ``None`` (the default) or ``'?'``, each
  character of the argument string will be appended to the list.
  Example usage::

>>> parser = argparse.ArgumentParser()
    >>> parser.add_argument("--foo", action="extend", nargs="+", type=str)
    >>> parser.parse_args(["--foo", "f1", "--foo", "f2", "f3", "f4"])
    Namespace(foo=['f1', 'f2', 'f3', 'f4'])

.. versionadded:: 3.8

* ``'count'`` - This counts the number of times an argument occurs. For
  example, this is useful for increasing verbosity levels::

>>> parser = argparse.ArgumentParser()
    >>> parser.add_argument('--verbose', '-v', action='count', default=0)
    >>> parser.parse_args(['-vvv'])
    Namespace(verbose=3)

Note, the *default* will be ``None`` unless explicitly set to *0*.

* ``'help'`` - This prints a complete help message for all the options in the
  current parser and then exits. By default a help action is automatically
  added to the parser. See :class:`ArgumentParser` for details of how the
  output is created.

* ``'version'`` - This expects a ``version=`` keyword argument in the
  :meth:`~ArgumentParser.add_argument` call, and prints version information
  and exits when invoked::

>>> import argparse
    >>> parser = argparse.ArgumentParser(prog='PROG')
    >>> parser.add_argument('--version', action='version', version='%(prog)s 2.0')
    >>> parser.parse_args(['--version'])
    PROG 2.0

You may also specify an arbitrary action by passing an :class:`Action` subclass
(e.g. :class:`BooleanOptionalAction`) or other object that implements the same
interface. Only actions that consume command-line arguments (e.g. ``'store'``,
``'append'``, ``'extend'``, or custom actions with non-zero ``nargs``) can be used
with positional arguments.

The recommended way to create a custom action is to extend :class:`Action`,
overriding the :meth:`!__call__` method and optionally the :meth:`!__init__` and
:meth:`!format_usage` methods. You can also register custom actions using the
:meth:`~ArgumentParser.register` method and reference them by their registered name.

An example of a custom action::

>>> class FooAction(argparse.Action):
   ...     def __init__(self, option_strings, dest, nargs=None, **kwargs):
   ...         if nargs is not None:
   ...             raise ValueError("nargs not allowed")
   ...         super().__init__(option_strings, dest, **kwargs)
   ...     def __call__(self, parser, namespace, values, option_string=None):
   ...         print('%r %r %r' % (namespace, values, option_string))
   ...         setattr(namespace, self.dest, values)
   ...
   >>> parser = argparse.ArgumentParser()
   >>> parser.add_argument('--foo', action=FooAction)
   >>> parser.add_argument('bar', action=FooAction)
   >>> args = parser.parse_args('1 --foo 2'.split())
   Namespace(bar=None, foo=None) '1' None
   Namespace(bar='1', foo=None) '2' '--foo'
   >>> args
   Namespace(bar='1', foo='2')

For more details, see :class:`Action`.

.. _nargs:

nargs
^^^^^

:class:`ArgumentParser` objects usually associate a single command-line argument with a
single action to be taken.  The ``nargs`` keyword argument associates a
different number of command-line arguments with a single action.
See also :ref:`specifying-ambiguous-arguments`. The supported values are:

* ``N`` (an integer).  ``N`` arguments from the command line will be gathered
  together into a list.  For example::

>>> parser = argparse.ArgumentParser()
     >>> parser.add_argument('--foo', nargs=2)
     >>> parser.add_argument('bar', nargs=1)
     >>> parser.parse_args('c --foo a b'.split())
     Namespace(bar=['c'], foo=['a', 'b'])

Note that ``nargs=1`` produces a list of one item.  This is different from
  the default, in which the item is produced by itself.

.. index:: single: ? (question mark); in argparse module

* ``'?'``. One argument will be consumed from the command line if possible, and
  produced as a single item.  If no command-line argument is present, the value from
  default_ will be produced.  Note that for optional arguments, there is an
  additional case - the option string is present but not followed by a
  command-line argument.  In this case the value from const_ will be produced.  Some
  examples to illustrate this::

>>> parser = argparse.ArgumentParser()
     >>> parser.add_argument('--foo', nargs='?', const='c', default='d')
     >>> parser.add_argument('bar', nargs='?', default='d')
     >>> parser.parse_args(['XX', '--foo', 'YY'])
     Namespace(bar='XX', foo='YY')
     >>> parser.parse_args(['XX', '--foo'])
     Namespace(bar='XX', foo='c')
     >>> parser.parse_args([])
     Namespace(bar='d', foo='d')

One of the more common uses of ``nargs='?'`` is to allow optional input and
  output files::

>>> parser = argparse.ArgumentParser()
     >>> parser.add_argument('infile', nargs='?')
     >>> parser.add_argument('outfile', nargs='?')
     >>> parser.parse_args(['input.txt', 'output.txt'])
     Namespace(infile='input.txt', outfile='output.txt')
     >>> parser.parse_args(['input.txt'])
     Namespace(infile='input.txt', outfile=None)
     >>> parser.parse_args([])
     Namespace(infile=None, outfile=None)

.. index:: single: * (asterisk); in argparse module

* ``'*'``.  All command-line arguments present are gathered into a list.  Note that
  it generally doesn't make much sense to have more than one positional argument
  with ``nargs='*'``, but multiple optional arguments with ``nargs='*'`` is
  possible.  For example::

>>> parser = argparse.ArgumentParser()
     >>> parser.add_argument('--foo', nargs='*')
     >>> parser.add_argument('--bar', nargs='*')
     >>> parser.add_argument('baz', nargs='*')
     >>> parser.parse_args('a b --foo x y --bar 1 2'.split())
     Namespace(bar=['1', '2'], baz=['a', 'b'], foo=['x', 'y'])

.. index:: single: + (plus); in argparse module

* ``'+'``. Just like ``'*'``, all command-line arguments present are gathered into a
  list.  Additionally, an error message will be generated if there wasn't at
  least one command-line argument present.  For example::

>>> parser = argparse.ArgumentParser(prog='PROG')
     >>> parser.add_argument('foo', nargs='+')
     >>> parser.parse_args(['a', 'b'])
     Namespace(foo=['a', 'b'])
     >>> parser.parse_args([])
     usage: PROG [-h] foo [foo ...]
     PROG: error: the following arguments are required: foo

If the ``nargs`` keyword argument is not provided, the number of arguments consumed
is determined by the action_.  Generally this means a single command-line argument
will be consumed and a single item (not a list) will be produced.
Actions that do not consume command-line arguments (e.g.
``'store_const'``) set ``nargs=0``.

.. _const:

const
^^^^^

The ``const`` argument of :meth:`~ArgumentParser.add_argument` is used to hold
constant values that are not read from the command line but are required for
the various :class:`ArgumentParser` actions.  The two most common uses of it are:

* When :meth:`~ArgumentParser.add_argument` is called with
  ``action='store_const'`` or ``action='append_const'``.  These actions add the
  ``const`` value to one of the attributes of the object returned by
  :meth:`~ArgumentParser.parse_args`. See the action_ description for examples.
  If ``const`` is not provided to :meth:`~ArgumentParser.add_argument`, it will
  receive a default value of ``None``.

* When :meth:`~ArgumentParser.add_argument` is called with option strings
  (like ``-f`` or ``--foo``) and ``nargs='?'``.  This creates an optional
  argument that can be followed by zero or one command-line arguments.
  When parsing the command line, if the option string is encountered with no
  command-line argument following it, the value from ``const`` will be used.
  See the nargs_ description for examples.

.. versionchanged:: 3.11
   ``const=None`` by default, including when ``action='append_const'`` or
   ``action='store_const'``.

.. _default:

default
^^^^^^^

All optional arguments and some positional arguments may be omitted at the
command line.  The ``default`` keyword argument of
:meth:`~ArgumentParser.add_argument`, whose value defaults to ``None``,
specifies what value should be used if the command-line argument is not present.
For optional arguments, the ``default`` value is used when the option string
was not present at the command line::

>>> parser = argparse.ArgumentParser()
   >>> parser.add_argument('--foo', default=42)
   >>> parser.parse_args(['--foo', '2'])
   Namespace(foo='2')
   >>> parser.parse_args([])
   Namespace(foo=42)

If the target namespace already has an attribute set, the action *default*
will not overwrite it::

>>> parser = argparse.ArgumentParser()
   >>> parser.add_argument('--foo', default=42)
   >>> parser.parse_args([], namespace=argparse.Namespace(foo=101))
   Namespace(foo=101)

If the ``default`` value is a string, the parser parses the value as if it
were a command-line argument.  In particular, the parser applies any type_
conversion argument, if provided, before setting the attribute on the
:class:`Namespace` return value.  Otherwise, the parser uses the value as is::

>>> parser = argparse.ArgumentParser()
   >>> parser.add_argument('--length', default='10', type=int)
   >>> parser.add_argument('--width', default=10.5, type=int)
   >>> parser.parse_args()
   Namespace(length=10, width=10.5)

For positional arguments with nargs_ equal to ``?`` or ``*``, the ``default`` value
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
