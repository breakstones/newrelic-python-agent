import sys

from newrelic.core.stack_trace import exception_stack, current_stack

def function0():
    raise RuntimeError('function0')

def function1():
    function0()

def function2():
    function1()

def function3():
    function2()

def function4():
    function3()

def function5():
    function4()

def function6():
    function5()

def function7():
    function6()

def function8():
    function7()

def function9():
    function8()

def function10():
    function9()

def function11():
    function10()

def function12():
    function11()

def format_stack_trace(frames):
    result = ['Traceback (most recent call last):']
    result.extend(['File "{0}", line {1}, in {2}'.format(*v) for v in frames])
    return result

# When using a try/except with stack trace formatting being done within
# the except block, all line numbers for the combine stack trace will be
# correct.

def test_trace_inline():
    try:
        function12()
    except Exception:
        tb = sys.exc_info()[2]
        actual = exception_stack(tb, limit=14)
        require = format_stack_trace(_stack_trace_inline)
        assert actual == require

_stack_trace_inline = [
    (__file__, test_trace_inline.__code__.co_firstlineno+2,
        test_trace_inline.__name__),
    (__file__, function12.__code__.co_firstlineno+1, function12.__name__),
    (__file__, function11.__code__.co_firstlineno+1, function11.__name__),
    (__file__, function10.__code__.co_firstlineno+1, function10.__name__),
    (__file__, function9.__code__.co_firstlineno+1, function9.__name__),
    (__file__, function8.__code__.co_firstlineno+1, function8.__name__),
    (__file__, function7.__code__.co_firstlineno+1, function7.__name__),
    (__file__, function6.__code__.co_firstlineno+1, function6.__name__),
    (__file__, function5.__code__.co_firstlineno+1, function5.__name__),
    (__file__, function4.__code__.co_firstlineno+1, function4.__name__),
    (__file__, function3.__code__.co_firstlineno+1, function3.__name__),
    (__file__, function2.__code__.co_firstlineno+1, function2.__name__),
    (__file__, function1.__code__.co_firstlineno+1, function1.__name__),
    (__file__, function0.__code__.co_firstlineno+1, function0.__name__)
]

# Where the traceback is saved away and then returned to a scope outside
# of the except block, the line numbers for the exception part of the
# stack are correct, but things go funny with what is joined from the
# current stack. In particular, the line numbers of parent stack frames
# can be wrong as what the traceback holds is a reference to the live
# stack frames and since the execution point of the stack frames changes
# so does the line number.
#
# The consequence of this is that rather than the line number for the
# stack frame for test_trace_passed1() being line 1, it is line 2,
# which is where the parent stack frame is being calculated within the
# exception_stack() function.

def _test_trace_passed1():
    try:
        function12()
    except Exception:
        return sys.exc_info()[2]

def test_trace_passed1():
    tb = _test_trace_passed1()
    actual = exception_stack(tb, limit=15)
    require = format_stack_trace(_stack_trace_passed1)
    assert actual == require, (actual, require)

_stack_trace_passed1 = [
    (__file__, test_trace_passed1.__code__.co_firstlineno+2,
        test_trace_passed1.__name__),
    (__file__, _test_trace_passed1.__code__.co_firstlineno+2,
        _test_trace_passed1.__name__),
    (__file__, function12.__code__.co_firstlineno+1, function12.__name__),
    (__file__, function11.__code__.co_firstlineno+1, function11.__name__),
    (__file__, function10.__code__.co_firstlineno+1, function10.__name__),
    (__file__, function9.__code__.co_firstlineno+1, function9.__name__),
    (__file__, function8.__code__.co_firstlineno+1, function8.__name__),
    (__file__, function7.__code__.co_firstlineno+1, function7.__name__),
    (__file__, function6.__code__.co_firstlineno+1, function6.__name__),
    (__file__, function5.__code__.co_firstlineno+1, function5.__name__),
    (__file__, function4.__code__.co_firstlineno+1, function4.__name__),
    (__file__, function3.__code__.co_firstlineno+1, function3.__name__),
    (__file__, function2.__code__.co_firstlineno+1, function2.__name__),
    (__file__, function1.__code__.co_firstlineno+1, function1.__name__),
    (__file__, function0.__code__.co_firstlineno+1, function0.__name__)
]

# An additional example for the changing line numbers as described above
# is the following. Note that _test_trace_passed2b() does not actually
# appear. This is correct, as the intersection point for the stack trace
# is test_trace_passed2() and the line number shows the call to the
# function _test_trace_passed2b() where the code is excuting within that
# frame. This is instead of being at the point of call for the function
# _test_trace_passed2a() where the exception was generated.

def _test_trace_passed2a():
    try:
        function12()
    except Exception:
        return sys.exc_info()[2]

def _test_trace_passed2b(tb):
    actual = exception_stack(tb, limit=15)
    require = format_stack_trace(_stack_trace_passed2)
    assert actual == require, (actual, require)

def test_trace_passed2():
    tb = _test_trace_passed2a()
    _test_trace_passed2b(tb)

_stack_trace_passed2 = [
    (__file__, test_trace_passed2.__code__.co_firstlineno+2,
        test_trace_passed2.__name__),
    (__file__, _test_trace_passed2a.__code__.co_firstlineno+2,
        _test_trace_passed2a.__name__),
    (__file__, function12.__code__.co_firstlineno+1, function12.__name__),
    (__file__, function11.__code__.co_firstlineno+1, function11.__name__),
    (__file__, function10.__code__.co_firstlineno+1, function10.__name__),
    (__file__, function9.__code__.co_firstlineno+1, function9.__name__),
    (__file__, function8.__code__.co_firstlineno+1, function8.__name__),
    (__file__, function7.__code__.co_firstlineno+1, function7.__name__),
    (__file__, function6.__code__.co_firstlineno+1, function6.__name__),
    (__file__, function5.__code__.co_firstlineno+1, function5.__name__),
    (__file__, function4.__code__.co_firstlineno+1, function4.__name__),
    (__file__, function3.__code__.co_firstlineno+1, function3.__name__),
    (__file__, function2.__code__.co_firstlineno+1, function2.__name__),
    (__file__, function1.__code__.co_firstlineno+1, function1.__name__),
    (__file__, function0.__code__.co_firstlineno+1, function0.__name__)
]

# Here we limit to bottom most stack frames within just the exception
# stack.

def test_trace_truncated():
    try:
        function12()
    except Exception:
        tb = sys.exc_info()[2]
        actual = exception_stack(tb, limit=5)
        require = format_stack_trace(_stack_trace_limit_truncated)
        assert actual == require

_stack_trace_limit_truncated = [
    (__file__, function4.__code__.co_firstlineno+1, function4.__name__),
    (__file__, function3.__code__.co_firstlineno+1, function3.__name__),
    (__file__, function2.__code__.co_firstlineno+1, function2.__name__),
    (__file__, function1.__code__.co_firstlineno+1, function1.__name__),
    (__file__, function0.__code__.co_firstlineno+1, function0.__name__)
]

# Previous examples truncated at stack frame of test as can't easily
# compare to frames above. This test collects all stack frames to make
# sure doesn't blow up, but can't compare.

def test_trace_exception_full():
    try:
        function12()
    except Exception:
        tb = sys.exc_info()[2]
        actual = exception_stack(tb)

# Test just the ability to get the current stack frame. Limited so we
# can compare to what we expect.

def skip0(skip, limit):
    return current_stack(skip=skip, limit=limit)

def skip1(skip, limit):
    return skip0(skip, limit)

def skip2(skip, limit):
    return skip1(skip, limit)

def skip3(skip, limit):
    return skip2(skip, limit)

def skip4(skip, limit):
    return skip3(skip, limit)

def skip5(skip, limit):
    return skip4(skip, limit)

def test_trace_current():
    actual = skip5(skip=0, limit=5)
    require = format_stack_trace(_stack_trace_current)
    assert actual == require

_stack_trace_current = [
    (__file__, skip4.__code__.co_firstlineno+1, skip4.__name__),
    (__file__, skip3.__code__.co_firstlineno+1, skip3.__name__),
    (__file__, skip2.__code__.co_firstlineno+1, skip2.__name__),
    (__file__, skip1.__code__.co_firstlineno+1, skip1.__name__),
    (__file__, skip0.__code__.co_firstlineno+1, skip0.__name__)
]

# Test the ability to skip some frames at the bottom of the stack. This
# is actually relied upon when generated combine stack trace for exception
# but this tests it in isolation.

def test_trace_current_skip():
    actual = skip5(skip=1, limit=5)
    require = format_stack_trace(_stack_trace_current_skip)
    assert actual == require

_stack_trace_current_skip = [
    (__file__, skip5.__code__.co_firstlineno+1, skip5.__name__),
    (__file__, skip4.__code__.co_firstlineno+1, skip4.__name__),
    (__file__, skip3.__code__.co_firstlineno+1, skip3.__name__),
    (__file__, skip2.__code__.co_firstlineno+1, skip2.__name__),
    (__file__, skip1.__code__.co_firstlineno+1, skip1.__name__)
]

# Previous examples truncated current stack as can't easily compare to
# frames above. This test collects all stack frames to make sure doesn't
# blow up, but can't compare.

def test_trace_current_full():
    actual = skip5(skip=0, limit=1000)
