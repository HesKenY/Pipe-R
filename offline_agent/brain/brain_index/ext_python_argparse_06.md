# Python argparse (6/7)
source: https://github.com/python/cpython/blob/main/Doc/library/argparse.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
encountered at the command line

* dest_ - name of the attribute under which subcommand name will be
     stored; by default ``None`` and no value is stored

* required_ - Whether or not a subcommand must be provided, by default
     ``False`` (added in 3.7)

* help_ - help for sub-parser group in help output, by default ``None``

* metavar_ - string presenting available subcommands in help; by default it
     is ``None`` and presents subcommands in form {cmd1, cmd2, ..}

Some example usage::

>>> # create the top-level parser
     >>> parser = argparse.ArgumentParser(prog='PROG')
     >>> parser.add_argument('--foo', action='store_true', help='foo help')
     >>> subparsers = parser.add_subparsers(help='subcommand help')
     >>>
     >>> # create the parser for the "a" command
     >>> parser_a = subparsers.add_parser('a', help='a help')
     >>> parser_a.add_argument('bar', type=int, help='bar help')
     >>>
     >>> # create the parser for the "b" command
     >>> parser_b = subparsers.add_parser('b', help='b help')
     >>> parser_b.add_argument('--baz', choices=('X', 'Y', 'Z'), help='baz help')
     >>>
     >>> # parse some argument lists
     >>> parser.parse_args(['a', '12'])
     Namespace(bar=12, foo=False)
     >>> parser.parse_args(['--foo', 'b', '--baz', 'Z'])
     Namespace(baz='Z', foo=True)

Note that the object returned by :meth:`~ArgumentParser.parse_args` will only contain
   attributes for the main parser and the subparser that was selected by the
   command line (and not any other subparsers).  So in the example above, when
   the ``a`` command is specified, only the ``foo`` and ``bar`` attributes are
   present, and when the ``b`` command is specified, only the ``foo`` and
   ``baz`` attributes are present.

Similarly, when a help message is requested from a subparser, only the help
   for that particular parser will be printed.  The help message will not
   include parent parser or sibling parser messages.  (A help message for each
   subparser command, however, can be given by supplying the ``help=`` argument
   to :meth:`~_SubParsersAction.add_parser` as above.)

::

>>> parser.parse_args(['--help'])
     usage: PROG [-h] [--foo] {a,b} ...

positional arguments:
       {a,b}   subcommand help
         a     a help
         b     b help

options:
       -h, --help  show this help message and exit
       --foo   foo help

>>> parser.parse_args(['a', '--help'])
     usage: PROG a [-h] bar

positional arguments:
       bar     bar help

options:
       -h, --help  show this help message and exit

>>> parser.parse_args(['b', '--help'])
     usage: PROG b [-h] [--baz {X,Y,Z}]

options:
       -h, --help     show this help message and exit
       --baz {X,Y,Z}  baz help

The :meth:`~ArgumentParser.add_subparsers` method also supports ``title`` and ``description``
   keyword arguments.  When either is present, the subparser's commands will
   appear in their own group in the help output.  For example::

>>> parser = argparse.ArgumentParser()
     >>> subparsers = parser.add_subparsers(title='subcommands',
     ...                                    description='valid subcommands',
     ...                                    help='additional help')
     >>> subparsers.add_parser('foo')
     >>> subparsers.add_parser('bar')
     >>> parser.parse_args(['-h'])
     usage:  [-h] {foo,bar} ...

options:
       -h, --help  show this help message and exit

subcommands:
       valid subcommands

{foo,bar}   additional help

One particularly effective way of handling subcommands is to combine the use
   of the :meth:`~ArgumentParser.add_subparsers` method with calls to :meth:`~ArgumentParser.set_defaults` so
   that each subparser knows which Python function it should execute.  For
   example::

>>> # subcommand functions
     >>> def foo(args):
     ...     print(args.x * args.y)
     ...
     >>> def bar(args):
     ...     print('((%s))' % args.z)
     ...
     >>> # create the top-level parser
     >>> parser = argparse.ArgumentParser()
     >>> subparsers = parser.add_subparsers(required=True)
     >>>
     >>> # create the parser for the "foo" command
     >>> parser_foo = subparsers.add_parser('foo')
     >>> parser_foo.add_argument('-x', type=int, default=1)
     >>> parser_foo.add_argument('y', type=float)
     >>> parser_foo.set_defaults(func=foo)
     >>>
     >>> # create the parser for the "bar" command
     >>> parser_bar = subparsers.add_parser('bar')
     >>> parser_bar.add_argument('z')
     >>> parser_bar.set_defaults(func=bar)
     >>>
     >>> # parse the args and call whatever function was selected
     >>> args = parser.parse_args('foo 1 -x 2'.split())
     >>> args.func(args)
     2.0
     >>>
     >>> # parse the args and call whatever function was selected
     >>> args = parser.parse_args('bar XYZYX'.split())
     >>> args.func(args)
     ((XYZYX))

This way, you can let :meth:`~ArgumentParser.parse_args` do the job of calling the
   appropriate function after argument parsing is complete.  Associating
   functions with actions like this is typically the easiest way to handle the
   different actions for each of your subparsers.  However, if it is necessary
   to check the name of the subparser that was invoked, the ``dest`` keyword
   argument to the :meth:`~ArgumentParser.add_subparsers` call will work::

>>> parser = argparse.ArgumentParser()
     >>> subparsers = parser.add_subparsers(dest='subparser_name')
     >>> subparser1 = subparsers.add_parser('1')
     >>> subparser1.add_argument('-x')
     >>> subparser2 = subparsers.add_parser('2')
     >>> subparser2.add_argument('y')
     >>> parser.parse_args(['2', 'frobble'])
     Namespace(subparser_name='2', y='frobble')

.. versionchanged:: 3.7
      New *required* keyword-only parameter.

.. versionchanged:: 3.14
      Subparser's *prog* is no longer affected by a custom usage message in
      the main parser.

.. method:: _SubParsersAction.add_parser(name, *, help=None, aliases=None, \
                                         deprecated=False, **kwargs)

Create and return a new :class:`ArgumentParser` object for the
   subcommand *name*.

The *name* argument is the name of the sub-command.

The *help* argument provides a short description for this sub-command.

The *aliases* argument allows providing alternative names for this
   sub-command. For example::

>>> parser = argparse.ArgumentParser()
      >>> subparsers = parser.add_subparsers()
      >>> checkout = subparsers.add_parser('checkout', aliases=['co'])
      >>> checkout.add_argument('foo')
      >>> parser.parse_args(['co', 'bar'])
      Namespace(foo='bar')

The *deprecated* argument, if ``True``, marks the sub-command as
   deprecated and will issue a warning when used. For example::

>>> parser = argparse.ArgumentParser(prog='chicken.py')
      >>> subparsers = parser.add_subparsers()
      >>> fly = subparsers.add_parser('fly', deprecated=True)
      >>> args = parser.parse_args(['fly'])
      chicken.py: warning: command 'fly' is deprecated
      Namespace()

All other keyword arguments are passed directly to the
   :class:`!ArgumentParser` constructor.

.. versionadded:: 3.13
      Added the *deprecated* parameter.

FileType objects
^^^^^^^^^^^^^^^^

.. class:: FileType(mode='r', bufsize=-1, encoding=None, errors=None)

The :class:`FileType` factory creates objects that can be passed to the type
   argument of :meth:`ArgumentParser.add_argument`.  Arguments that have
   :class:`FileType` objects as their type will open command-line arguments as
   files with the requested modes, buffer sizes, encodings and error handling
   (see the :func:`open` function for more details)::

>>> parser = argparse.ArgumentParser()
      >>> parser.add_argument('--raw', type=argparse.FileType('wb', 0))
      >>> parser.add_argument('out', type=argparse.FileType('w', encoding='UTF-8'))
      >>> parser.parse_args(['--raw', 'raw.dat', 'file.txt'])
      Namespace(out=<_io.TextIOWrapper name='file.txt' mode='w' encoding='UTF-8'>, raw=<_io.FileIO name='raw.dat' mode='wb'>)

FileType objects understand the pseudo-argument ``'-'`` and automatically
   convert this into :data:`sys.stdin` for readable :class:`FileType` objects and
   :data:`sys.stdout` for writable :class:`FileType` objects::

>>> parser = argparse.ArgumentParser()
      >>> parser.add_argument('infile', type=argparse.FileType('r'))
      >>> parser.parse_args(['-'])
      Namespace(infile=<_io.TextIOWrapper name='<stdin>' encoding='UTF-8'>)

.. note::

If one argument uses *FileType* and then a subsequent argument fails,
      an error is reported but the file is not automatically closed.
      This can also clobber the output files.
      In this case, it would be better to wait until after the parser has
      run and then use the :keyword:`with`-statement to manage the files.

.. versionchanged:: 3.4
      Added the *encoding* and *errors* parameters.

.. deprecated:: 3.14

Argument groups
^^^^^^^^^^^^^^^

.. method:: ArgumentParser.add_argument_group(title=None, description=None, *, \
                                              [argument_default], [conflict_handler])

By default, :class:`ArgumentParser` groups command-line arguments into
   "positional arguments" and "options" when displaying help
   messages. When there is a better conceptual grouping of arguments than this
   default one, appropriate groups can be created using the
   :meth:`!add_argument_group` method::

>>> parser = argparse.ArgumentParser(prog='PROG', add_help=False)
     >>> group = parser.add_argument_group('group')
     >>> group.add_argument('--foo', help='foo help')
     >>> group.add_argument('bar', help='bar help')
     >>> parser.print_help()
     usage: PROG [--foo FOO] bar

group:
       bar    bar help
       --foo FOO  foo help

The :meth:`add_argument_group` method returns an argument group object which
   has an :meth:`~ArgumentParser.add_argument` method just like a regular
   :class:`ArgumentParser`.  When an argument is added to the group, the parser
   treats it just like a normal argument, but displays the argument in a
   separate group for help messages.  The :meth:`!add_argument_group` method
   accepts *title* and *description* arguments which can be used to
   customize this display::

>>> parser = argparse.ArgumentParser(prog='PROG', add_help=False)
     >>> group1 = parser.add_argument_group('group1', 'group1 description')
     >>> group1.add_argument('foo', help='foo help')
     >>> group2 = parser.add_argument_group('group2', 'group2 description')
     >>> group2.add_argument('--bar', help='bar help')
     >>> parser.print_help()
     usage: PROG [--bar BAR] foo

group1:
       group1 description

foo    foo help

group2:
       group2 description

--bar BAR  bar help

The optional, keyword-only parameters argument_default_ and conflict_handler_
   allow for finer-grained control of the behavior of the argument group. These
   parameters have the same meaning as in the :class:`ArgumentParser` constructor,
   but apply specifically to the argument group rather than the entire parser.

Note that any arguments not in your user-defined groups will end up back
   in the usual "positional arguments" and "optional arguments" sections.

Within each argument group, arguments are displayed in help output in the
   order in which they are added.

.. deprecated-removed:: 3.11 3.14
      Calling :meth:`add_argument_group` on an argument group now raises an
      exception. This nesting was never supported, often failed to work
      correctly, and was unintentionally exposed through inheritance.

.. deprecated:: 3.14
      Passing prefix_chars_ to :meth:`add_argument_group`
      is now deprecated.

Mutual exclusion
^^^^^^^^^^^^^^^^

.. method:: ArgumentParser.add_mutually_exclusive_group(required=False)

Create a mutually exclusive group. :mod:`!argparse` will make sure that only
   one of the arguments in the mutually exclusive group was present on the
   command line::

>>> parser = argparse.ArgumentParser(prog='PROG')
     >>> group = parser.add_mutually_exclusive_group()
     >>> group.add_argument('--foo', action='store_true')
     >>> group.add_argument('--bar', action='store_false')
     >>> parser.parse_args(['--foo'])
     Namespace(bar=True, foo=True)
     >>> parser.parse_args(['--bar'])
     Namespace(bar=False, foo=False)
     >>> parser.parse_args(['--foo', '--bar'])
     usage: PROG [-h] [--foo | --bar]
     PROG: error: argument --bar: not allowed with argument --foo

The :meth:`add_mutually_exclusive_group` method also accepts a *required*
   argument, to indicate that at least one of the mutually exclusive arguments
   is required::

>>> parser = argparse.ArgumentParser(prog='PROG')
     >>> group = parser.add_mutually_exclusive_group(required=True)
     >>> group.add_argument('--foo', action='store_true')
     >>> group.add_argument('--bar', action='store_false')
     >>> parser.parse_args([])
     usage: PROG [-h] (--foo | --bar)
     PROG: error: one of the arguments --foo --bar is required

Note that currently mutually exclusive argument groups do not support the
   *title* and *description* arguments of
   :meth:`~ArgumentParser.add_argument_group`. However, a mutually exclusive
   group can be added to an argument group that has a title and description.
   For example::

>>> parser = argparse.ArgumentParser(prog='PROG')
     >>> group = parser.add_argument_group('Group title', 'Group description')
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
