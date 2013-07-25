# -*- coding: utf-8 -*-

import webapp2
from google.appengine.api import xmpp
from home import BaseHandler

class XMPPHandler(webapp2.RequestHandler):
    def post(self):
        message = xmpp.Message(self.request.POST)
        if message.body[0:5].lower() == 'hello':
            message.reply("Greetings!")

class ChatPageHandler(BaseHandler):
    def get(self):
        ctx = {'content':'has', 'uri_for':webapp2.uri_for}
        self.render_response('page.html', ctx)


