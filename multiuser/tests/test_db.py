# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy import create_engine

from multiuser import db


# global session object
session = None


def setup_module():
    global session
    session = db.new_session('sqlite:///:memory:', echo=True)

setup = setup_module

def teardown_module():
    session.close()

teardown = teardown_module


def test_hub():
    hub = db.Hub(
        server=db.Server(
            ip = u'1.2.3.4',
            port = 1234,
        )
    )
    session.add(hub)
    session.commit()
    assert hub.server.ip == u'1.2.3.4'
    hub.server.port == 1234


def test_user():
    hub = db.Hub()
    session.add(hub)
    kaylee = db.User(name=u'kaylee')
    session.add(kaylee)
    session.commit()
    session.add(kaylee.new_cookie_token())
    session.add(kaylee.new_cookie_token())
    session.add(kaylee.new_api_token())
    session.commit()
    assert len(kaylee.api_tokens) == 1
    assert len(kaylee.cookie_tokens) == 2

def test_runthrough():
    hub = db.Hub()
    session.add(hub)
    session.commit()
    
