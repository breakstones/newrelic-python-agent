import os, sys, string, re

import setuptools

copyright = '(C) Copyright 2010-2011 New Relic Inc. All rights reserved.'

python_version = '%d.%d' % sys.version_info[:2]
package_name = 'python-%s' % python_version

script_directory = os.path.dirname(__file__)
if not script_directory:
  script_directory = os.getcwd()

version_file = os.path.join(script_directory, 'VERSION')
package_version = open(version_file).read().strip()

packages = [
  "newrelic",
  "newrelic.api",
  "newrelic.core",
  "newrelic.hooks",
  "newrelic.lib",
  "newrelic.lib.sqlparse",
  "newrelic.lib.sqlparse.engine",
  "newrelic.scripts",
]

package_directory = 'newrelic-%s' % package_version

setuptools.setup(
  name = "newrelic",
  version = package_version,
  description = "Python agent for New Relic",
  author = "New Relic",
  author_email = "support@newrelic.com",
  license = copyright,
  url = "http://www.newrelic.com",
  packages = packages,
  package_dir = { 'newrelic': '%s/newrelic' % package_directory },
  extra_path = ("newrelic", "newrelic-%s" % package_version),
)
