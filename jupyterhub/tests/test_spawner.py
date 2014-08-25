"""Tests for process spawning"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import getpass
import logging
import signal
import sys

import mock
import simplepam

from tornado import gen
from tornado.ioloop import IOLoop
from tornado.testing import AsyncTestCase, gen_test
from IPython.utils.py3compat import unicode_type

from ..spawner import LocalProcessSpawner
from .. import db

_echo_sleep = """
import sys, time
print(sys.argv)
time.sleep(10)
"""

_uninterruptible = """
import time
while True:
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        print("interrupted")
"""

def sleep(t):
    """async time.sleep"""
    loop = IOLoop.current()
    return gen.Task(loop.add_timeout, loop.time() + t)

class TestLocalProcessSpawner(AsyncTestCase):
    
    def setup_class(cls):
        session = cls.session = db.new_session('sqlite:///:memory:')
        user = cls.user = db.User(
            name=getpass.getuser(),
            server = db.Server(),
        )
        hub = cls.hub = db.Hub(
            server = db.Server(),
        )
        session.add(user)
        session.add(hub)
        session.commit()
        cls.log = logging.getLogger()
        logging.basicConfig(level=logging.DEBUG)
        cls.cmd = [sys.executable, '-c', _echo_sleep]
    
    spawner_class = LocalProcessSpawner
    
    def new_spawner(self, **kwargs):
        kwargs.setdefault('cmd', self.cmd)
        kwargs.setdefault('user', self.user)
        kwargs.setdefault('hub', self.hub)
        kwargs.setdefault('log', self.log)
        kwargs.setdefault('INTERRUPT_TIMEOUT', 2)
        kwargs.setdefault('TERM_TIMEOUT', 1)
        kwargs.setdefault('KILL_TIMEOUT', 1)
        
        return self.spawner_class(**kwargs)
    
    @gen_test
    def test_spawner(self):
        spawner = self.new_spawner()
        yield spawner.start()
        
        status = yield spawner.poll()
        self.assertEqual(status, None)
        
        yield spawner.stop()
        status = yield spawner.poll()
        self.assertEqual(status, -signal.SIGINT)

    @gen_test(timeout=10)
    def test_stop_spawner_sigint_fails(self):
        spawner = self.new_spawner(cmd=[sys.executable, '-c', _uninterruptible])
        yield spawner.start()
        
        status = yield spawner.poll()
        self.assertEqual(status, None)
        
        # wait for the process to get to the while True: loop
        yield sleep(1)
        
        yield spawner.stop()
        status = yield spawner.poll()
        self.assertEqual(status, -signal.SIGTERM)

    @gen_test
    def test_stop_spawner_stop_now(self):
        spawner = self.new_spawner()
        yield spawner.start()
        
        status = yield spawner.poll()
        self.assertEqual(status, None)
        
        yield spawner.stop(now=True)
        status = yield spawner.poll()
        self.assertEqual(status, -signal.SIGTERM)

