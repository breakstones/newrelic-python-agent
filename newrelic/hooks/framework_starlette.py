from newrelic.api.asgi_application import wrap_asgi_application
from newrelic.api.background_task import BackgroundTaskWrapper
from newrelic.api.time_trace import current_trace
from newrelic.api.function_trace import FunctionTraceWrapper, wrap_function_trace
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper, function_wrapper, FunctionWrapper
from newrelic.core.trace_cache import trace_cache
from newrelic.api.time_trace import record_exception
from newrelic.core.config import ignore_status_code
from newrelic.common.coroutine import is_coroutine_function
from newrelic.api.transaction import current_transaction


def framework_details():
    import starlette

    return ("Starlette", getattr(starlette, "__version__", None))


def bind_request(request, *args, **kwargs):
    return request


def bind_exc(request, exc, *args, **kwargs):
    return exc


class RequestContext(object):
    def __init__(self, request):
        self.request = request
        self.force_propagate = False
        self.thread_id = None

    def __enter__(self):
        trace = getattr(self.request, "_nr_trace", None)
        self.force_propagate = trace and current_trace() is None

        # Propagate trace context onto the current task
        if self.force_propagate:
            self.thread_id = trace_cache().thread_start(trace)
    
    def __exit__(self, exc, value, tb):
        # Remove any context from the current thread as it was force propagated above
        if self.force_propagate:
            trace_cache().thread_stop(self.thread_id)


@function_wrapper
def route_naming_wrapper(wrapped, instance, args, kwargs):

    with RequestContext(bind_request(*args, **kwargs)):
        transaction = current_transaction()
        if transaction:
            transaction.set_transaction_name(callable_name(wrapped))
        return wrapped(*args, **kwargs)


def bind_endpoint(path, endpoint, *args, **kwargs):
    return path, endpoint, args, kwargs


def bind_exception(request, exc, *args, **kwargs):
    return request, exc, args, kwargs


def bind_add_exception_handler(exc_class_or_status_code, handler, *args, **kwargs):
    return exc_class_or_status_code, handler, args, kwargs


def wrap_route(wrapped, instance, args, kwargs):
    path, endpoint, args, kwargs = bind_endpoint(*args, **kwargs)
    endpoint = route_naming_wrapper(FunctionTraceWrapper(endpoint))
    return wrapped(path, endpoint, *args, **kwargs)


def wrap_request(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)
    instance._nr_trace = current_trace()

    return result


def wrap_background_method(wrapped, instance, args, kwargs):
    func = getattr(instance, "func", None)
    if func:
        instance.func = BackgroundTaskWrapper(func)
    return wrapped(*args, **kwargs)


@function_wrapper
def wrap_middleware(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)

    dispatch_func = getattr(result, "dispatch_func", None)
    name = dispatch_func and callable_name(dispatch_func)

    return FunctionTraceWrapper(result, name=name)


def bind_middleware(middleware_class, *args, **kwargs):
    return middleware_class, args, kwargs


def wrap_add_middleware(wrapped, instance, args, kwargs):
    middleware, args, kwargs = bind_middleware(*args, **kwargs)
    return wrapped(wrap_middleware(middleware), *args, **kwargs)


def bind_middleware_starlette(
    debug=False, routes=None, middleware=None, *args, **kwargs
):
    return middleware


def wrap_starlette(wrapped, instance, args, kwargs):
    middlewares = bind_middleware_starlette(*args, **kwargs)
    if middlewares:
        for middleware in middlewares:
            cls = getattr(middleware, "cls", None)
            if cls and not hasattr(cls, "__wrapped__"):
                middleware.cls = wrap_middleware(cls)

    return wrapped(*args, **kwargs)


def record_response_error(response, value=None):
    status_code = getattr(response, "status_code", None)
    exc = getattr(value, "__class__", None)
    tb = getattr(value, "__traceback__", None)
    if not ignore_status_code(status_code):
        record_exception(exc, value, tb)


async def wrap_exception_handler_async(coro):
    response = await coro
    record_response_error(response)
    return response


def wrap_exception_handler(wrapped, instance, args, kwargs):
    if is_coroutine_function(wrapped):
        return wrap_exception_handler_async(wrapped(*args, **kwargs))
    else:
        with RequestContext(bind_request(*args, **kwargs)):
            response = wrapped(*args, **kwargs)
            record_response_error(response, bind_exc(*args, **kwargs))
            return response


def wrap_add_exception_handler(wrapped, instance, args, kwargs):
    exc_class_or_status_code, handler, args, kwargs = bind_add_exception_handler(*args, **kwargs)
    handler = FunctionWrapper(handler, wrap_exception_handler)
    return wrapped(exc_class_or_status_code, handler, *args, **kwargs)


def instrument_starlette_applications(module):
    framework = framework_details()
    version_info = tuple(int(v) for v in framework[1].split(".", 3)[:3])

    wrap_asgi_application(module, "Starlette.__call__", framework=framework)
    wrap_function_wrapper(module, "Starlette.add_middleware", wrap_add_middleware)

    if version_info >= (0, 12, 13):
        wrap_function_wrapper(module, "Starlette.__init__", wrap_starlette)


def instrument_starlette_routing(module):
    wrap_function_wrapper(module, "Route.__init__", wrap_route)


def instrument_starlette_requests(module):
    wrap_function_wrapper(module, "Request.__init__", wrap_request)


def instrument_starlette_middleware_errors(module):
    wrap_function_trace(module, "ServerErrorMiddleware.__call__")


def instrument_starlette_exceptions(module):
    wrap_function_trace(module, "ExceptionMiddleware.__call__")

    wrap_function_wrapper(module, "ExceptionMiddleware.http_exception",
        wrap_exception_handler)

    wrap_function_wrapper(module, "ExceptionMiddleware.add_exception_handler",
        wrap_add_exception_handler)


def instrument_starlette_background_task(module):
    wrap_function_wrapper(module, "BackgroundTask.__call__", wrap_background_method)
