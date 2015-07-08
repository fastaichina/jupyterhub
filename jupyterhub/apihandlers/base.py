"""Base API handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json

from http.client import responses
from urllib.parse import urlparse

from tornado import web

from ..handlers import BaseHandler

class APIHandler(BaseHandler):

    def check_origin(self):
        """Check Origin for cross-site API requests.
        
        Copied from WebSocket with changes:
        
        - allow unspecified host/origin (e.g. scripts)
        """
        if self.allow_origin == '*':
            return True

        host = self.request.headers.get("Host")
        origin = self.request.headers.get("Origin")

        # If no header is provided, assume it comes from a script/curl.
        # We are only concerned with cross-site browser stuff here.
        if origin is None or host is None:
            return True
        
        origin = origin.lower()
        origin_host = urlparse(origin).netloc
        
        # OK if origin matches host
        if origin_host == host:
            return True
        
        # Check CORS headers
        if self.allow_origin:
            allow = self.allow_origin == origin
        elif self.allow_origin_pat:
            allow = bool(self.allow_origin_pat.match(origin))
        else:
            # No CORS headers deny the request
            allow = False
        if not allow:
            self.log.warn("Blocking Cross Origin API request.  Origin: %s, Host: %s",
                origin, host,
            )
        return allow

    def prepare(self):
        if not self.check_origin():
            raise web.HTTPError(404)
        return super().prepare()

    def get_json_body(self):
        """Return the body of the request as JSON data."""
        if not self.request.body:
            return None
        body = self.request.body.strip().decode('utf-8')
        try:
            model = json.loads(body)
        except Exception:
            self.log.debug("Bad JSON: %r", body)
            self.log.error("Couldn't parse JSON", exc_info=True)
            raise web.HTTPError(400, 'Invalid JSON in body of request')
        return model
    
    def write_error(self, status_code, **kwargs):
        """Write JSON errors instead of HTML"""
        exc_info = kwargs.get('exc_info')
        message = ''
        status_message = responses.get(status_code, 'Unknown Error')
        if exc_info:
            exception = exc_info[1]
            # get the custom message, if defined
            try:
                message = exception.log_message % exception.args
            except Exception:
                pass

            # construct the custom reason, if defined
            reason = getattr(exception, 'reason', '')
            if reason:
                status_message = reason
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({
            'status': status_code,
            'message': message or status_message,
        }))

    def user_model(self, user):
        model = {
            'name': user.name,
            'admin': user.admin,
            'server': user.server.base_url if user.running else None,
            'pending': None,
            'last_activity': user.last_activity.isoformat(),
        }
        if user.spawn_pending:
            model['pending'] = 'spawn'
        elif user.stop_pending:
            model['pending'] = 'stop'
        return model
    
    _model_types = {
        'name': str,
        'admin': bool,
    }
    
    def _check_user_model(self, model):
        if not isinstance(model, dict):
            raise web.HTTPError(400, "Invalid JSON data: %r" % model)
        if not set(model).issubset(set(self._model_types)):
            raise web.HTTPError(400, "Invalid JSON keys: %r" % model)
        for key, value in model.items():
            if not isinstance(value, self._model_types[key]):
                raise web.HTTPError(400, "user.%s must be %s, not: %r" % (
                    key, self._model_types[key], type(value)
                ))
