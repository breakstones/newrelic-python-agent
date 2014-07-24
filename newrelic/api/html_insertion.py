import re

_head_start_p = b"""(?P<head><head[^>]*>)"""

def _xua_meta_p(tag):
  return (b"""(?P<xuaTAG><\s*meta[^>]+http-equiv\s*=\s*['"]"""
          b"""x-ua-compatible['"][^>]*>)""".replace(b'TAG', tag))

def _charset_meta_p(tag):
  return (b"""(?P<charsetTAG><\s*meta[^>]+charset\s*=[^>]*>)""".replace(
      b'TAG', tag))

_body_start_p = b"""(?P<body><body[^>]*>)"""

_body_start_re = re.compile(b""".*""" + _body_start_p + b""".*""",
       re.IGNORECASE | re.DOTALL)

_insertion_point_re = re.compile(b'('
   b'(.*' + _charset_meta_p(b'1') + b'.*' + _xua_meta_p(b'2') + b')|'
   b'(.*' + _xua_meta_p(b'1') + b'.*' + _charset_meta_p(b'2') + b')|'
   b'(.*' + _charset_meta_p(b'3') + b')|'
   b'(.*' + _xua_meta_p(b'3') + b')|'
   b'(.*' + _head_start_p + b'))?'
   b'(.*' + _body_start_p + b'.*)?',
   re.IGNORECASE | re.DOTALL)

def insert_html_snippet(data, html_to_be_inserted):
   matchobj = _insertion_point_re.match(data)

   if not matchobj:
       return data

   if matchobj.start('body') == -1:
       return None

   # Use the best match we have from the head element for
   # the place to insert the text.

   for name in ('xua3', 'charset3', 'xua2', 'charset2', 'head'):
       end = matchobj.end(name)

       if end != -1:
           text = html_to_be_inserted()

           if not text:
               return data

           return text.join((data[:end], data[end:]))

   # Fallback to inserting text prior to the body element.

   start = matchobj.start('body')
   if start != -1:
       text = html_to_be_inserted()

       if not text:
           return data

       return text.join((data[:start], data[start:]))

   # Something went very wrong as we should never get here.

   return None

def verify_body_exists(data):
    return _body_start_re.match(data) != -1
