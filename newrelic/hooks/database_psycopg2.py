import os

from newrelic.agent import (wrap_object, ObjectProxy, wrap_function_wrapper,
        register_database_client, FunctionTrace, callable_name,
        DatabaseTrace, current_transaction)

from newrelic.api.database_trace import enable_datastore_instance_feature

from .database_dbapi2 import (ConnectionWrapper as DBAPI2ConnectionWrapper,
        ConnectionFactory as DBAPI2ConnectionFactory)

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote
try:
    from urlparse import parse_qsl
except ImportError:
    from urllib.parse import parse_qsl

from newrelic.packages.requests.packages.urllib3 import util as ul3_util

class ConnectionWrapper(DBAPI2ConnectionWrapper):

    def __enter__(self):
        transaction = current_transaction()
        name = callable_name(self.__wrapped__.__enter__)
        with FunctionTrace(transaction, name):
            self.__wrapped__.__enter__()

        # Must return a reference to self as otherwise will be
        # returning the inner connection object. If 'as' is used
        # with the 'with' statement this will mean no longer
        # using the wrapped connection object and nothing will be
        # tracked.

        return self

    def __exit__(self, exc, value, tb):
        transaction = current_transaction()
        name = callable_name(self.__wrapped__.__exit__)
        with FunctionTrace(transaction, name):
            if exc is None:
                with DatabaseTrace(transaction, 'COMMIT',
                        self._nr_dbapi2_module, self._nr_connect_params):
                    return self.__wrapped__.__exit__(exc, value, tb)
            else:
                with DatabaseTrace(transaction, 'ROLLBACK',
                        self._nr_dbapi2_module, self._nr_connect_params):
                    return self.__wrapped__.__exit__(exc, value, tb)

class ConnectionFactory(DBAPI2ConnectionFactory):

    __connection_wrapper__ = ConnectionWrapper

def instance_info(args, kwargs):

    def _bind_params(dsn=None, *args, **kwargs):
        return dsn

    dsn = _bind_params(*args, **kwargs)

    try:
        if dsn and (dsn.startswith('postgres://')
                or dsn.startswith('postgresql://')):

            # Parse dsn as URI
            #
            # According to PGSQL, connect URIs are in the format of RFC 3896
            # https://www.postgresql.org/docs/9.5/static/libpq-connect.html

            parsed_uri = ul3_util.parse_url(dsn)

            host = parsed_uri.hostname or None
            host = host and unquote(host)

            port = parsed_uri.port

            db_name = parsed_uri.path
            db_name = db_name and db_name.lstrip('/')
            db_name = db_name or None

            query = parsed_uri.query or ''
            qp = dict(parse_qsl(query))

            # Query parameters override hierarchical values in URI.

            host = qp.get('hostaddr') or qp.get('host') or host or None
            port = qp.get('port') or port
            db_name = qp.get('dbname') or db_name

        elif dsn:

            # Parse dsn as a key-value connection string

            kv = dict([pair.split('=', 2) for pair in dsn.split()])
            host = kv.get('hostaddr') or kv.get('host')
            port = kv.get('port')
            db_name = kv.get('dbname')

        else:

            # No dsn, so get the instance info from keyword arguments.

            host = kwargs.get('hostaddr') or kwargs.get('host')
            port = kwargs.get('port')
            db_name = kwargs.get('database')

        # Ensure non-None values are strings.

        (host, port, db_name) = [str(s) if s is not None else s
                for s in (host, port, db_name)]

    except Exception:
        host, port, db_name = ('unknown', 'unknown', 'unknown')

    return (host, port, db_name)

def _add_defaults(parsed_host, parsed_port, parsed_database):

    # ENV variables set the default values

    parsed_host = parsed_host or os.environ.get('PGHOST')
    parsed_port = parsed_port or os.environ.get('PGPORT')
    database = parsed_database or os.environ.get('PGDATABASE')

    if parsed_host is None:
        host = 'localhost'
        port = 'default'
    elif parsed_host.startswith('/'):
        host = 'localhost'
        port = '%s/.s.PGSQL.%s' % (parsed_host, parsed_port or '5432')
    else:
        host = parsed_host
        port = parsed_port or '5432'

    return (host, port, database)

def instrument_psycopg2(module):
    register_database_client(module, database_product='Postgres',
            quoting_style='single', explain_query='explain',
            explain_stmts=('select', 'insert', 'update', 'delete'),
            instance_info=instance_info)

    enable_datastore_instance_feature(module)

    wrap_object(module, 'connect', ConnectionFactory, (module,))

def wrapper_psycopg2_register_type(wrapped, instance, args, kwargs):
    def _bind_params(obj, scope=None):
        return obj, scope

    obj, scope = _bind_params(*args, **kwargs)

    if isinstance(scope, ObjectProxy):
        scope = scope.__wrapped__

    if scope is not None:
        return wrapped(obj, scope)
    else:
        return wrapped(obj)

# As we can't get in reliably and monkey patch the register_type()
# function in psycopg2._psycopg2 before it is imported, we also need to
# monkey patch the other references to it in other psycopg2 sub modules.
# In doing that we need to make sure it has not already been monkey
# patched by checking to see if it is already an ObjectProxy.

def instrument_psycopg2__psycopg2(module):
    if hasattr(module, 'register_type'):
        if not isinstance(module.register_type, ObjectProxy):
            wrap_function_wrapper(module, 'register_type',
                    wrapper_psycopg2_register_type)

def instrument_psycopg2_extensions(module):
    if hasattr(module, 'register_type'):
        if not isinstance(module.register_type, ObjectProxy):
            wrap_function_wrapper(module, 'register_type',
                    wrapper_psycopg2_register_type)

def instrument_psycopg2__json(module):
    if hasattr(module, 'register_type'):
        if not isinstance(module.register_type, ObjectProxy):
            wrap_function_wrapper(module, 'register_type',
                    wrapper_psycopg2_register_type)

def instrument_psycopg2__range(module):
    if hasattr(module, 'register_type'):
        if not isinstance(module.register_type, ObjectProxy):
            wrap_function_wrapper(module, 'register_type',
                    wrapper_psycopg2_register_type)
