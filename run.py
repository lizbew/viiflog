# -*- coding: utf-8 -*-

import webapp2
import xmpphandlers

config = {}
config['webapp2_extras.sessions'] = {
        'secret_key': 'jfdfaeti78fdFfinlifjser'
}
app = webapp2.WSGIApplication([
           ('/_ad/xmpp/message/chat/', xmpphandlers.XMPPHandler),
           ('/chat/', xmpphandlers.ChatPageHandler)
          ],
          debug=True,
          config=config)
