# -*- coding: utf-8 -*-
import os

debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')
PATH_PREFIX = '/blog'
CHECK_HOST = not debug
UPS_HEADER_NAME = 'X-Viifly'