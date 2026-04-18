# Python json (1/3)
source: https://github.com/python/cpython/blob/main/Doc/library/json.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
:mod:`!json` --- JSON encoder and decoder
=========================================

.. module:: json
   :synopsis: Encode and decode the JSON format.

**Source code:** :source:`Lib/json/__init__.py`

--------------

`JSON (JavaScript Object Notation) <https://json.org>`_, specified by
:rfc:`7159` (which obsoletes :rfc:`4627`) and by
`ECMA-404 <https://ecma-international.org/publications-and-standards/standards/ecma-404/>`_,
is a lightweight data interchange format inspired by
`JavaScript <https://en.wikipedia.org/wiki/JavaScript>`_ object literal syntax
(although it is not a strict subset of JavaScript [#rfc-errata]_ ).

.. note::
   The term "object" in the context of JSON processing in Python can be
   ambiguous. All values in Python are objects. In JSON, an object refers to
   any data wrapped in curly braces, similar to a Python dictionary.

.. warning::
   Be cautious when parsing JSON data from untrusted sources. A malicious
   JSON string may cause the decoder to consume considerable CPU and memory
   resources. Limiting the size of data to be parsed is recommended.

This module exposes an API familiar to users of the standard library
:mod:`marshal` and :mod:`pickle` modules.

Encoding basic Python object hierarchies::

>>> import json
    >>> json.dumps(['foo', {'bar': ('baz', None, 1.0, 2)}])
    '["foo", {"bar": ["baz", null, 1.0, 2]}]'
    >>> print(json.dumps("\"foo\bar"))
    "\"foo\bar"
    >>> print(json.dumps('\u1234'))
    "\u1234"
    >>> print(json.dumps('\\'))
    "\\"
    >>> print(json.dumps({"c": 0, "b": 0, "a": 0}, sort_keys=True))
    {"a": 0, "b": 0, "c": 0}
    >>> from io import StringIO
    >>> io = StringIO()
    >>> json.dump(['streaming API'], io)
    >>> io.getvalue()
    '["streaming API"]'

Compact encoding::

>>> import json
    >>> json.dumps([1, 2, 3, {'4': 5, '6': 7}], separators=(',', ':'))
    '[1,2,3,{"4":5,"6":7}]'

Pretty printing::

>>> import json
    >>> print(json.dumps({'6': 7, '4': 5}, sort_keys=True, indent=4))
    {
        "4": 5,
        "6": 7
    }

Customizing JSON object encoding::

>>> import json
   >>> def custom_json(obj):
   ...     if isinstance(obj, complex):
   ...         return {'__complex__': True, 'real': obj.real, 'imag': obj.imag}
   ...     raise TypeError(f'Cannot serialize object of {type(obj)}')
   ...
   >>> json.dumps(1 + 2j, default=custom_json)
   '{"__complex__": true, "real": 1.0, "imag": 2.0}'

Decoding JSON::

>>> import json
    >>> json.loads('["foo", {"bar":["baz", null, 1.0, 2]}]')
    ['foo', {'bar': ['baz', None, 1.0, 2]}]
    >>> json.loads('"\\"foo\\bar"')
    '"foo\x08ar'
    >>> from io import StringIO
    >>> io = StringIO('["streaming API"]')
    >>> json.load(io)
    ['streaming API']

Customizing JSON object decoding::

>>> import json
    >>> def as_complex(dct):
    ...     if '__complex__' in dct:
    ...         return complex(dct['real'], dct['imag'])
    ...     return dct
    ...
    >>> json.loads('{"__complex__": true, "real": 1, "imag": 2}',
    ...     object_hook=as_complex)
    (1+2j)
    >>> import decimal
    >>> json.loads('1.1', parse_float=decimal.Decimal)
    Decimal('1.1')

Extending :class:`JSONEncoder`::

>>> import json
    >>> class ComplexEncoder(json.JSONEncoder):
    ...     def default(self, obj):
    ...         if isinstance(obj, complex):
    ...             return [obj.real, obj.imag]
    ...         # Let the base class default method raise the TypeError
    ...         return super().default(obj)
    ...
    >>> json.dumps(2 + 1j, cls=ComplexEncoder)
    '[2.0, 1.0]'
    >>> ComplexEncoder().encode(2 + 1j)
    '[2.0, 1.0]'
    >>> list(ComplexEncoder().iterencode(2 + 1j))
    ['[2.0', ', 1.0', ']']

Using :mod:`!json` from the shell to validate and pretty-print:

.. code-block:: shell-session

$ echo '{"json":"obj"}' | python -m json
    {
        "json": "obj"
    }
    $ echo '{1.2:3.4}' | python -m json
    Expecting property name enclosed in double quotes: line 1 column 2 (char 1)

See :ref:`json-commandline` for detailed documentation.

.. note::

JSON is a subset of `YAML <https://yaml.org/>`_ 1.2.  The JSON produced by
   this module's default settings (in particular, the default *separators*
   value) is also a subset of YAML 1.0 and 1.1.  This module can thus also be
   used as a YAML serializer.

.. note::

This module's encoders and decoders preserve input and output order by
   default.  Order is only lost if the underlying containers are unordered.

Basic Usage
-----------

.. function:: dump(obj, fp, *, skipkeys=False, ensure_ascii=True, \
                   check_circular=True, allow_nan=True, cls=None, \
                   indent=None, separators=None, default=None, \
                   sort_keys=False, **kw)

Serialize *obj* as a JSON formatted stream to *fp* (a ``.write()``-supporting
   :term:`file-like object`) using this :ref:`Python-to-JSON conversion table
   <py-to-json-table>`.

.. note::

Unlike :mod:`pickle` and :mod:`marshal`, JSON is not a framed protocol,
      so trying to serialize multiple objects with repeated calls to
      :func:`dump` using the same *fp* will result in an invalid JSON file.

:param object obj:
      The Python object to be serialized.

:param fp:
      The file-like object *obj* will be serialized to.
      The :mod:`!json` module always produces :class:`str` objects,
      not :class:`bytes` objects,
      therefore ``fp.write()`` must support :class:`str` input.
   :type fp: :term:`file-like object`

:param bool skipkeys:
      If ``True``, keys that are not of a basic type
      (:class:`str`, :class:`int`, :class:`float`, :class:`bool`, ``None``)
      will be skipped instead of raising a :exc:`TypeError`.
      Default ``False``.

:param bool ensure_ascii:
      If ``True`` (the default), the output is guaranteed to
      have all incoming non-ASCII and non-printable characters escaped.
      If ``False``, all characters will be outputted as-is, except for
      the characters that must be escaped: quotation mark, reverse solidus,
      and the control characters U+0000 through U+001F.

:param bool check_circular:
      If ``False``, the circular reference check for container types is skipped
      and a circular reference will result in a :exc:`RecursionError` (or worse).
      Default ``True``.

:param bool allow_nan:
      If ``False``, serialization of out-of-range :class:`float` values
      (``nan``, ``inf``, ``-inf``) will result in a :exc:`ValueError`,
      in strict compliance with the JSON specification.
      If ``True`` (the default), their JavaScript equivalents
      (``NaN``, ``Infinity``, ``-Infinity``) are used.

:param cls:
      If set, a custom JSON encoder with the
      :meth:`~JSONEncoder.default` method overridden,
      for serializing into custom datatypes.
      If ``None`` (the default), :class:`!JSONEncoder` is used.
   :type cls: a :class:`JSONEncoder` subclass

:param indent:
      If a positive integer or string, JSON array elements and
      object members will be pretty-printed with that indent level.
      A positive integer indents that many spaces per level;
      a string (such as ``"\t"``) is used to indent each level.
      If zero, negative, or ``""`` (the empty string),
      only newlines are inserted.
      If ``None`` (the default), the most compact representation is used.
   :type indent: int | str | None

:param separators:
      A two-tuple: ``(item_separator, key_separator)``.
      If ``None`` (the default), *separators* defaults to
      ``(', ', ': ')`` if *indent* is ``None``,
      and ``(',', ': ')`` otherwise.
      For the most compact JSON,
      specify ``(',', ':')`` to eliminate whitespace.
   :type separators: tuple | None

:param default:
      A function that is called for objects that can't otherwise be serialized.
      It should return a JSON encodable version of the object
      or raise a :exc:`TypeError`.
      If ``None`` (the default), :exc:`!TypeError` is raised.
   :type default: :term:`callable` | None

:param bool sort_keys:
      If ``True``, dictionaries will be outputted sorted by key.
      Default ``False``.

.. versionchanged:: 3.2
      Allow strings for *indent* in addition to integers.

.. versionchanged:: 3.4
      Use ``(',', ': ')`` as default if *indent* is not ``None``.

.. versionchanged:: 3.6
      All optional parameters are now :ref:`keyword-only <keyword-only_parameter>`.

.. function:: dumps(obj, *, skipkeys=False, ensure_ascii=True, \
                    check_circular=True, allow_nan=True, cls=None, \
                    indent=None, separators=None, default=None, \
                    sort_keys=False, **kw)

Serialize *obj* to a JSON formatted :class:`str` using this :ref:`conversion
   table <py-to-json-table>`.  The arguments have the same meaning as in
   :func:`dump`.

.. note::

Keys in key/value pairs of JSON are always of the type :class:`str`. When
      a dictionary is converted into JSON, all the keys of the dictionary are
      coerced to strings. As a result of this, if a dictionary is converted
      into JSON and then back into a dictionary, the dictionary may not equal
      the original one. That is, ``loads(dumps(x)) != x`` if x has non-string
      keys.

.. function:: load(fp, *, cls=None, object_hook=None, parse_float=None, \
                   parse_int=None, parse_constant=None, \
                   object_pairs_hook=None, array_hook=None, **kw)

Deserialize *fp* to a Python object
   using the :ref:`JSON-to-Python conversion table <json-to-py-table>`.

:param fp:
      A ``.read()``-supporting :term:`text file` or :term:`binary file`
      containing the JSON document to be deserialized.
   :type fp: :term:`file-like object`

:param cls:
      If set, a custom JSON decoder.
      Additional keyword arguments to :func:`!load`
      will be passed to the constructor of *cls*.
      If ``None`` (the default), :class:`!JSONDecoder` is used.
   :type cls: a :class:`JSONDecoder` subclass

:param object_hook:
      If set, a function that is called with the result of
      any JSON object literal decoded (a :class:`dict`).
      The return value of this function will be used
      instead of the :class:`dict`.
      This feature can be used to implement custom decoders,
      for example `JSON-RPC <https://www.jsonrpc.org>`_ class hinting.
      Default ``None``.
   :type object_hook: :term:`callable` | None

:param object_pairs_hook:
      If set, a function that is called with the result of
      any JSON object literal decoded with an ordered list of pairs.
      The return value of this function will be used
      instead of the :class:`dict`.
      This feature can be used to implement custom decoders.
      If *object_hook* is also set, *object_pairs_hook* takes priority.
      Default ``None``.
   :type object_pairs_hook: :term:`callable` | None

:param array_hook:
      If set, a function that is called with the result of
      any JSON array literal decoded with as a Python list.
      The return value of this function will be used
      instead of the :class:`list`.
      This feature can be used to implement custom decoders.
      Default ``None``.
   :type array_hook: :term:`callable` | None

:param parse_float:
      If set, a function that is called with
      the string of every JSON float to be decoded.
      If ``None`` (the default), it is equivalent to ``float(num_str)``.
      This can be used to parse JSON floats into custom datatypes,
      for example :class:`decimal.Decimal`.
   :type parse_float: :term:`callable` | None

:param parse_int:
      If set, a function that is called with
      the string of every JSON int to be decoded.
      If ``None`` (the default), it is equivalent to ``int(num_str)``.
      This can be used to parse JSON integers into custom datatypes,
      for example :class:`float`.
   :type parse_int: :term:`callable` | None

:param parse_constant:
      If set, a function that is called with one of the following strings:
      ``'-Infinity'``, ``'Infinity'``, or ``'NaN'``.
      This can be used to raise an exception
      if invalid JSON numbers are encountered.
      Default ``None``.
   :type parse_constant: :term:`callable` | None

:raises JSONDecodeError:
      When the data being deserialized is not a valid JSON document.

:raises UnicodeDecodeError:
      When the data being deserialized does not contain
      UTF-8, UTF-16 or UTF-32 encoded data.

.. versionchanged:: 3.1

* Added the optional *object_pairs_hook* parameter.
      * *parse_constant* doesn't get called on 'null', 'true', 'false' anymore.

.. versionchanged:: 3.6

* All optional parameters are now :ref:`keyword-only <keyword-only_parameter>`.
      * *fp* can now be a :term:`binary file`.
        The input encoding should be UTF-8, UTF-16 or UTF-32.

.. versionchanged:: 3.11
      The default *parse_int* of :func:`int` now limits the maximum length of
      the integer string via the interpreter's :ref:`integer string
      conversion length limitation <int_max_str_digits>` to help avoid denial
      of service attacks.

.. versionchanged:: 3.15
      Added the optional *array_hook* parameter.

.. function:: loads(s, *, cls=None, object_hook=None, parse_float=None, parse_int=None, parse_constant=None, object_pairs_hook=None, array_hook=None, **kw)

Identical to :func:`load`, but instead of a file-like object,
   deserialize *s* (a :class:`str`, :class:`bytes` or :class:`bytearray`
   instance containing a JSON document) to a Python object using this
   :ref:`conversion table <json-to-py-table>`.

.. versionchanged:: 3.6
      *s* can now be of type :class:`bytes` or :class:`bytearray`. The
      input encoding should be UTF-8, UTF-16 or UTF-32.

.. versionchanged:: 3.9
      The keyword argument *encoding* has been removed.

Encoders and Decoders
---------------------
