import sys
import os

import newrelic.api.transaction
import newrelic.api.import_hook
import newrelic.api.external_trace
import newrelic.api.function_trace
import newrelic.api.name_transaction
import newrelic.api.object_wrapper
import newrelic.api.pre_function

def instrument_gluon_compileapp(module):

    # Wrap the run_models_in() function as first phase
    # in executing a request after URL has been mapped
    # to a specific view. The name given to the web
    # transaction is combination of the application name
    # and view path. Marked with group of 'Custom' as we
    # have defined the formatting.

    def name_transaction_run_models_in(environment):
        return '%s::%s' % (environment['request'].application,
                environment['response'].view)

    newrelic.api.name_transaction.wrap_name_transaction(module, 'run_models_in',
            name=name_transaction_run_models_in, group='Custom')

    # Wrap functions which coordinate the execution of
    # the separate models, controller and view phases of
    # the request handling. This is done for timing how
    # long taken within these phases of request
    # handling. Use use a 'Custom' group qualified by
    # the phase.

    def name_function_run_models_in(environment):
        return '%s/%s' % (environment['request'].controller,
                environment['request'].function)

    newrelic.api.function_trace.wrap_function_trace(module, 'run_models_in',
            name=name_function_run_models_in, group='Custom/Models')

    def name_function_run_controller_in(controller, function, environment):
        return '%s/%s' % (controller, function)

    newrelic.api.function_trace.wrap_function_trace(module, 'run_controller_in',
            name=name_function_run_controller_in, group='Custom/Controller')

    def name_function_run_view_in(environment):
        return '%s/%s' % (environment['request'].controller,
                environment['request'].function)

    newrelic.api.function_trace.wrap_function_trace(module, 'run_view_in',
            name=name_function_run_view_in, group='Custom/View')

def instrument_gluon_restricted(module):

    # Wrap function which executes all the compiled
    # Python code files. The name used corresponds to
    # path of the resource within the context of the
    # application directory. The group used is either
    # 'Script/Execute' or 'Template/Render' based on
    # whether we can work out whether code object
    # corresponded to compiled template file or not.

    def name_function_restricted(code, environment={}, layer='Unknown'):
        if 'request' in environment:
            folder = environment['request'].folder
            if layer.startswith(folder):
                return layer[len(folder):]
        return layer

    def group_function_restricted(code, environment={}, layer='Unknown'):
        parts = layer.split('.')
        if parts[-1] in ['html'] or parts[-2:] in [['html','pyc']] :
            return 'Template/Render'
        return 'Script/Execute'

    newrelic.api.function_trace.wrap_function_trace(module, 'restricted',
            name=name_function_restricted, group=group_function_restricted)

def instrument_gluon_main(module):

    # Wrap main function which dispatches the various
    # phases of a request in order to capture any
    # errors. Need to use a custom object wrapper as we
    # need to ignore exceptions of type HTTP as that
    # type of exception is used to programmatically
    # return a valid response. For the case of a 404,
    # where we want to name the web transactions as
    # such, we pick that up later.

    class error_serve_controller(object):
        def __init__(self, wrapped):
            self.__wrapped = wrapped
        def __call__(self, request, response, session):
            txn = newrelic.api.transaction.transaction()
            if txn:
                HTTP = newrelic.api.import_hook.import_module('gluon.http').HTTP
                try:
                    return self.__wrapped(request, response, session)
                except HTTP, e:
                    raise
                except:
                    txn.notice_error(*sys.exc_info())
                    raise
            else:
                return self.__wrapped(request, response, session)
        def __getattr__(self, name):
            return getattr(self.__wrapped, name)

    newrelic.api.object_wrapper.wrap_object(
            module, 'serve_controller', error_serve_controller)

def instrument_gluon_template(module):

    # Wrap parsing/compilation of template files, using
    # the name of the template relative to the context
    # of the application it is contained in. Use a group
    # of 'Template/Compile'. Rendering of template is
    # picked up when executing the code object created
    # from this compilation step.

    def name_function_parse_template(filename, path='views/',
            context=dict(), *args):
        if 'request' in context:
            folder = context['request'].folder
            if path.startswith(folder):
                return '%s/%s' % (path[len(folder):], filename)
        else:
            return '%s/%s' % (path, filename)

    newrelic.api.function_trace.wrap_function_trace(module, 'parse_template',
            name=name_function_parse_template, group='Template/Compile')

def instrument_gluon_tools(module):

    # Wrap utility function for fetching an external URL.

    def url_external_fetch(url, *args):
        return url

    newrelic.api.external_trace.wrap_external_trace(
            module, 'fetch', library='gluon.tools.fetch',
            url=url_external_fetch)

    # Wrap utility function for fetching GEOCODE data.
    # The URL in this case is hardwired in code to point
    # at Google service and not part of arguments to we
    # need to hard code it here as well.

    newrelic.api.external_trace.wrap_external_trace(
            module, 'geocode', library='gluon.tools.geocode',
            url='http://maps.google.com/maps/geo')

def instrument_gluon_http(module):

    # This one is tricky. The only way to pick up that a
    # static file is being served up is to wrap the to()
    # method of a HTTP response object when actual
    # response is being generated. We need to qualify
    # this so only actually do anything when called from
    # the wsgibase() function within 'gluon.main'. To do
    # this need to go stack diving and look back at the
    # parent stack frame. Doing that we can look at
    # details of where calling code is located as well
    # as sneak a peak at local variables in the calling
    # stack to determine if we were handling a static
    # file and what type of file was being served.
    # Normally static file URLs would be left alone but
    # don't want to risk black hole rule and instead
    # generate custom wildcard URLs with precedence to
    # extension. When can work out how to reliably get
    # the application name then can incorporate that
    # into the pattern as well in style used for web
    # transaction names for views. The application name
    # should normally be the first path segment, but the
    # fact that arbitrary rewrite rules can be used may
    # mean that isn't always the case.

    def name_transaction_name_not_found(response, *args):
        txn = newrelic.api.transaction.transaction()
        if not txn:
            return

        frame = sys._getframe(1)

        if os.path.split(frame.f_code.co_filename)[-1] != 'main.py':
            return
        if frame.f_code.co_name != 'wsgibase':
            return

        if response.status == 400:
            txn.name_transaction('400', 'Uri')
            return

        if response.status == 404:
            txn.name_transaction('404', 'Uri')
            return

        if 'static_file' not in frame.f_locals:
            return

        if frame.f_locals['static_file']:
            if 'environ' in frame.f_locals:
                environ = frame.f_locals['environ']
                path_info = environ.get('PATH_INFO', '')

                if path_info:
                    parts = os.path.split(path_info)
                    if parts[1] == '':
                        if parts[0] == '/':
                            txn.name_transaction('*', 'Custom')
                        else:
                            name = '%s/*' % parts[0].lstrip('/')
                            txn.name_transaction(name, 'Custom')
                    else:
                        extension = os.path.splitext(parts[1])[-1]
                        name = '%s/*%s' % (parts[0].lstrip('/'), extension)
                        txn.name_transaction(name, 'Custom')
                else:
                    txn.name_transaction('*', 'Custom')

            else:
                txn.name_transaction('*', 'Custom')

    newrelic.api.pre_function.wrap_pre_function(
            module, 'HTTP.to', name_transaction_name_not_found)
