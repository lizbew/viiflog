# -*- coding: utf-8 -*-
import webapp2
#import jinja2
import os.path
import markdown
import StringIO
import models
# import urllib
import logging
#import json
# from google.appengine.api import users
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import images
import webapp2_extras.routes
# from webapp2_extras import jinja2
# from webapp2_extras import sessions
from webapp2_extras import json

#from webapp2_extras.appengine.users import admin_required
from oauth2client.appengine import OAuth2Decorator

from google.appengine.api import xmpp

from config import *
from handlers import *
from admin import *
#sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

#JINJA_ENVIRONMENT = jinja2.Environment(
#    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
#    extensions=['jinja2.ext.autoescape'])

#def render_template(template_name, template_values={}):
#    template = JINJA_ENVIRONMENT.get_template(template_name)
#    return template.render(template_values)


# debug = False
if debug:
    logging.info('Running in Debug mode!')






#def create_img_url(uploaded_file):
#    if uploaded_file and uploaded_file.is_img():
#        return images.get_serving_url(blob_key=uploaded_file.store_key)
#    return None

decorator = OAuth2Decorator(
    client_id='211371041097.apps.googleusercontent.com',
    client_secret='fidnf_xinsd_ddsdffdfdi_xixixw__',
    scope='https://www.googleapis.com/auth/plus.login',
    callback_path=uri_for_static('/oauth2callback'))

class RedirectHandler(webapp2.RequestHandler):
    def get(self):
        self.redirect(webapp2.uri_for('home'))

class MainHandler(BaseHandler):
    def get(self):
        #self.response.headers['Content-Type'] = 'text/plain'
        post_list = models.query_post(None)
        #category_list = models.get_category_list()
        #self.response.write(render_template('post.html', {'post_list':post_list, 'category_list':category_list}))
        self.render_response_post_list('Home', post_list)

class PostHandler(BaseHandler):
    def get(self, post_id):
        # post_id = self.request.get('id')
        post = None
        if post_id:
            try:
                post = models.get_post_by_id(int(post_id))
            except ValueError:
                self.abort(404)
                return
        if post:
            self.render_response_post_list(post.title, [post], 'single')
        else:
            self.redirect(self.uri_for('home'))

class CategoryHandler(BaseHandler):
    def get(self, name):
        post_list = models.find_post_by_category(name, self.get_page_size())
        self.render_response_post_list('Posts in category ' + name, post_list)

class TagHandler(BaseHandler):
    def get(self, name):
        post_list = models.find_post_by_tag(name, self.get_page_size()) 
        self.render_response_post_list('Posts tagged ' + name, post_list)




class PageHandler(BaseHandler):
    def get(self, page):
        page_file = self.resolvePagePath(page)
        if not page_file:
            self.abort(404)
            return
        context = {}
        context['title'] = page
        context['content'] = convert_markdown_file(page_file)
        context['uri_for'] = webapp2.uri_for
        context['uri_for_static'] = uri_for_static
        self.render_response('page.html', context) 

    def resolvePagePath(self, page):
        if not page or len(page.strip()) == 0:
            return None
        page_path = os.path.join(os.path.dirname(__name__), '_page', page) + '.md'
        if os.path.exists(page_path):
            return page_path
        else:
            return None

class ApiPostHandler(BaseHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'application/json'
        json_data = {}
        post_list = models.query_post(None)
        posts = []
        if post_list:
            for p in post_list:
                posts.append(self.extr_post_info(p))
        json_data['posts'] = posts
        json_data['post_num'] = len(posts)
        self.response.write(json.encode(json_data))
     
    def extr_post_info(self, post):
        info = {}
        info['id'] = post.get_id()
        info['title'] = post.title
        info['author'] = post.author.nick_name
        info['published_date'] = post.published_date.isoformat()
        info['url'] = self.uri_for('post', post_id=post.get_id())
        #if debug:
        #    info['url'] = self.request.host_url + info['url']
        return info


class XMPPHandler(webapp2.RequestHandler):
    def post(self):
        message = xmpp.Message(self.request.POST)
        if message.body[0:5].lower() == 'hello':
            message.reply("Greetings!")

class ChatPageHandler(BaseHandler):
    def get(self):
        xmpp.send_presence('my12time@gmail.com', status="visited page")
        ctx = {'content':'has', 'uri_for':webapp2.uri_for, 'uri_for_static':uri_for_static}
        self.render_response('page.html', ctx)


def convert_markdown_file(md_file):
    outBuf= StringIO.StringIO()
    markdown.markdownFromFile(input=md_file, output=outBuf)
    return outBuf.getvalue()

def convert_markdown_text(md_text):
    return markdown.markdown(md_text)

def handle_404(request, response, exception):
    # logging.exception(exception)
    logging.info('404 return for {0}, visited reference {1}'.format(request.url, request.headers.get('Referer')))
    response.write('Oops! Page not found!')
    response.set_status(404)

def handle_500(request, response, exception):
    logging.exception(exception)
    response.write('A server error occurred!')
    response.set_status(500)


routes = [ webapp2.Route('/', MainHandler, 'home'),
           webapp2.Route('/admin', AdminHandler, 'admin-home'),
           webapp2.Route('/admin/post/list', AdminPostListHandler, 'admin-post-list'),
           webapp2.Route('/admin/post', AdminPostHandler, 'admin-post'),
           webapp2.Route('/admin/post/delete', AdminDeletePostHandler, 'admin-post-delete'),
           webapp2.Route('/admin/user', AdminUserHandler, 'admin-user'),
           webapp2.Route('/admin/category', AdminCategoryHandler, 'admin-category'),
           webapp2.Route('/admin/file', AdminFileHandler, 'admin-file'),
           webapp2.Route('/admin/file/<file_id:\d+>/delete', AdminFileDeleteHandler, 'admin-file-delete'),
           webapp2.Route('/posts/', MainHandler, 'post-list'),
           webapp2.Route('/posts/<post_id:\d+>', PostHandler, 'post'),
           webapp2.Route('/category/<name>', CategoryHandler, 'post-by-category'),
           webapp2.Route('/tag/<name>', TagHandler, 'post-by-tag'),
           webapp2.Route('/upload', UploadHandler, 'upload'),
           webapp2.Route('/serv/<file_id:\d+>/<file_name>', ServeHandler, 'serv'),
           webapp2.Route('/page/<page>', PageHandler, 'page'),
           webapp2.Route('/api/v1/posts', ApiPostHandler, 'api-post'),
           webapp2.Route(decorator.callback_path, decorator.callback_handler(), 'oauth2callback')]

if PATH_PREFIX:
    routes = [ webapp2_extras.routes.PathPrefixRoute(PATH_PREFIX, routes),
               webapp2.Route('/', RedirectHandler, 'r'),
               webapp2.Route('/chat/', ChatPageHandler)]

app_config = {}
app_config['page_size'] = 10
app_config['webapp2_extras.sessions'] = {
    'secret_key': 'jfdfaeti78fdFfinlifjser'
}
if not debug:
    app_config['host_url'] = 'http://blog.viifly.com'

#idef host_restrict_dispatcher(router, request, response):
#    head_fly = request.headers('X-Viifly')
#    if not debug and not head_fly:
#        # how to redirect?
#        pass
#    return router.default_dispatcher(request, response)
#app.router.set_dispatcher(host_restrict_dispatcher)

app = webapp2.WSGIApplication(routes, debug=debug, config=app_config)
app.error_handlers[404] = handle_404
app.error_handlers[500] = handle_500

