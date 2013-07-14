# -*- coding: utf-8 -*-
import webapp2
#import jinja2
import os.path
import markdown
import StringIO
import models
import urllib
import logging
import json
from google.appengine.api import users
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import images
import webapp2_extras.routes
from webapp2_extras import jinja2
from webapp2_extras import sessions
from oauth2client.appengine import OAuth2Decorator

#sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

#JINJA_ENVIRONMENT = jinja2.Environment(
#    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
#    extensions=['jinja2.ext.autoescape'])

#def render_template(template_name, template_values={}):
#    template = JINJA_ENVIRONMENT.get_template(template_name)
#    return template.render(template_values)

PATH_PREFIX = '/blog'

def uri_for_static(static_uri):
    if PATH_PREFIX and static_uri.startswith('/'):
        return PATH_PREFIX + static_uri

def create_file_upload_url(request):
    # return blobstore.create_upload_url(webapp2.get_app().router.build(request, 'upload', [], {}))
    return blobstore.create_upload_url(webapp2.uri_for('upload'))

def create_file_url(uploaded_file):
    #link = '/serv/{0}/{1}'.format(uploaded_file.key().id(), uploaded_file.file_name)
    #if PATH_PREFIX:
    #    return PATH_PREFIX + link
    #return link
    return webapp2.uri_for('serv', file_id=uploaded_file.key().id(), file_name=uploaded_file.file_name)

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

class BaseHandler(webapp2.RequestHandler):

    def dispatch(self):
        self.session_store = sessions.get_store(request=self.request)
        try:
            webapp2.RequestHandler.dispatch(self)
        finally:
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        return self.session_store.get_session()

    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)

    def get_page_size(self):
        page_size = self.app.config.get('page_size')
        if not page_size:
            page_size = 10
        return page_size

    def render_response(self, template_file, context):
        #self.response.write(render_template(template_file, context))
        self.response.write(self.jinja2.render_template(template_file, **context))

    def render_response_post_list(self, post_list, page_mode='list'):
        context = {}
        context['category_list'] =  models.get_category_list()
        context['post_list'] = post_list
        context['page_mode'] = page_mode
        context['uri_for'] = webapp2.uri_for
        self.render_response('post.html', context)

class BaseAdminHandler(BaseHandler):
    pass

class MainHandler(BaseHandler):
    def get(self):
        #self.response.headers['Content-Type'] = 'text/plain'
        post_list = models.query_post(None)
        #category_list = models.get_category_list()
        #self.response.write(render_template('post.html', {'post_list':post_list, 'category_list':category_list}))
        self.render_response_post_list(post_list)

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
            self.render_response_post_list([post], 'single')
        else:
            self.redirect(self.uri_for('home'))

class CategoryHandler(BaseHandler):
    def get(self, name):
        post_list = models.find_post_by_category(name, self.get_page_size())
        self.render_response_post_list(post_list)

class TagHandler(BaseHandler):
    def get(self, name):
        post_list = models.find_post_by_tag(name, self.get_page_size()) 
        self.render_response_post_list(post_list)

class AdminHandler(BaseAdminHandler):
    @decorator.oauth_required
    def get(self):
        self.render_response('admin_base.html', {'uri_for': webapp2.uri_for})


class AdminUserHandler(BaseAdminHandler):
    @decorator.oauth_required
    def get(self):
        uid = self.request.get('uid')
        a = models.get_user_by_id(uid)
        if a and self.request.get('action') == 'delete':
            a.delete()
            a = None
        ctx = {}
        ctx['account'] = a
        ctx['user_list'] = models.get_user_list()
        ctx['uri_for'] = webapp2.uri_for
        self.render_response('admin_user.html', ctx)
    def post(self):
        uid = self.request.get('uid')
        nick_name = self.request.get('nickname')
        email = self.request.get('email')
        role = self.request.get('role')
        check_active = self.request.get('active')
        active = False
        if check_active == 'on':
            active = True
        models.save_user(uid, nick_name, email, role, active)
        self.redirect(self.uri_for('admin-user'))
        #self.response.write(render_template('admin_user.html',{'user_list':models.get_user_list()}))

class AdminCategoryHandler(BaseAdminHandler):
    @decorator.oauth_required
    def get(self):
        cid = self.request.get('cid')
        category = models.get_category_by_id(cid)
        action = self.request.get('action')
        if action == 'delete' and category:
            category.delete()
            category = None
        ctx = {}
        ctx['category'] = category
        ctx['category_list'] = models.get_category_list()
        ctx['uri_for'] = webapp2.uri_for
        self.render_response('admin_category.html',ctx)
    def post(self):
        action = self.request.get('action')
        if action == 'edit':
            cid = self.request.get('cid')
            name = self.request.get('name')
            label = self.request.get('label')
            models.save_category(cid, name, label)
        elif action == 'delete':
            cid = self.request.get('cid')
            models.delete_category(cid)
        self.redirect(self.uri_for('admin-category'))

class AdminPostListHandler(BaseAdminHandler):
    @decorator.oauth_required
    def get(self):
        user = users.get_current_user()
        if user:
            post_criteria = models.PostCriteria()
            post_list = models.query_post(post_criteria)
            self.render_response('admin_post_list.html', {'post_list':post_list, 'uri_for':webapp2.uri_for})
        else:
            self.redirect(users.create_login_url(self.request.uri))


class AdminPostHandler(BaseAdminHandler):
    @decorator.oauth_required
    def get(self):
        post_id = self.request.get('id')
        if post_id != None:
            post = models.get_post_by_id(post_id)

        ctx = {'post': post, 'category_list':models.get_category_list(), 'uri_for':webapp2.uri_for}
        ctx['upload_url'] = create_file_upload_url(self.request)
        self.render_response('admin_post.html', ctx)
    def post(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
        post_data = {}
        post_id = self.request.get('id')
        post_data['title'] = self.request.get('title')
        post_data['content'] = self.request.get('content')
        post_data['abstract'] = self.request.get('abstract')
        post_data['category'] = self.request.get('category')
        post_published = False
        # logging.warn('fdf%s'%(self.request.get('publish'),))
        if self.request.get('publish') == 'on':
            post_data['published'] = True
        post_data['tags'] = self.request.get('tags')
        # logging.warn('get tags: %s'%post_tags)
        post = models.save_post_lon(user, post_id, post_data)
        ctx = {'post': post, 'category_list':models.get_category_list(), 'uri_for':webapp2.uri_for}
        ctx['upload_url'] = create_file_upload_url(self.request)
        self.render_response('admin_post.html',ctx)

class AdminDeletePostHandler(BaseAdminHandler):
    def get(self):
        post_id = self.request.get('id')
        models.delete_post_by_id(post_id)
        self.redirect(self.uri_for('admin-post-list'))

class AdminFileHandler(BaseAdminHandler):
    def get(self):
        ctx = {'file_list':models.get_uploaded_file_list(), 'uri_for':webapp2.uri_for}
        ctx['upload_url'] = create_file_upload_url(self.request)
        self.render_response('admin_file.html', ctx)

class AdminFileDeleteHandler(BaseAdminHandler):
    def get(self, file_id):
        uploadedFile = models.get_file(file_id)
        if uploadedFile:
            blobInfo = uploadedFile.store_key
            if blobInfo:
                #blobstore.delete(blob_key)
                blobInfo.delete()
            uploadedFile.delete()
        self.redirect(self.uri_for('admin-file'))

#class UploadHandler(webapp2.RequestHandler):
#    def get(self):
#        upload_url = blobstore.create_upload_url('/upload')
#        self.response.out.write('<html><body>')
#        self.response.out.write('<form action="%s" method="POST" enctype="multipart/form-data">' % upload_url)
#        self.response.out.write("""Upload File: <input type="file" name="file"> <br><input type="submit" name="submit"
#            value="submit"></form></body></html>""")

class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))

        upload_files = self.get_uploads('file')
        blob_info = upload_files[0]
        # self.redirect('/serv/%s'%blob_info.key())
        title = self.request.get('file_title')
        uploaded_file = models.save_file(blob_info, title)
        oj = {}
        oj['id'] = uploaded_file.key().id_or_name()
        oj['file_name'] = uploaded_file.file_name
        oj['upload_url'] = create_file_upload_url(self.request)
        oj['download_url'] = create_file_url(uploaded_file)
        #oj['img_url'] = create_img_url(uploaded_file)
        self.response.out.write(json.dumps(oj))
        # self.redirect('/admin/file')

class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, file_id, file_name):
        uploadedFile = models.get_file(file_id)
        if uploadedFile:
            blob_info = blobstore.BlobInfo.get(uploadedFile.store_key.key())
            self.send_blob(blob_info)
            return
        self.abort(404)
#    def get(self, resource):
#        resource = str(urllib.unquote(resource))
#        blob_info = blobstore.BlobInfo.get(resource)
#        self.send_blob(blob_info)

class PageHandler(BaseHandler):
    def get(self, page):
        page_file = self.resolvePagePath(page)
        if not page_file:
            self.abort(404)
            return
        context = {}
        context['content'] = convert_markdown_file(page_file)
        context['uri_for'] = webapp2.uri_for
        self.render_response('page.html', context) 

    def resolvePagePath(self, page):
        if not page or len(page.strip()) == 0:
            return None
        page_path = os.path.join(os.path.dirname(__name__), '_page', page) + '.md'
        if os.path.exists(page_path):
            return page_path
        else:
            return None

def convert_markdown_file(md_file):
    outBuf= StringIO.StringIO()
    markdown.markdownFromFile(input=md_file, output=outBuf)
    return outBuf.getvalue()

def convert_markdown_text(md_text):
    return markdown.markdown(md_text)

def handle_404(request, response, exception):
    logging.exception(exception)
    response.write('Oops! Page not found!')
    response.set_status(404)

def handle_500(request, response, exception):
    logging.exception(exception)
    response.write('A server error occurred!')
    response.set_status(500)

debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')
if debug:
    logging.info('Running in Debug mode!')

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
           webapp2.Route(decorator.callback_path, decorator.callback_handler(), 'oauth2callback')]

if PATH_PREFIX:
    routes = [ webapp2_extras.routes.PathPrefixRoute(PATH_PREFIX, routes),
               webapp2.Route('/', RedirectHandler, 'r')]

config = {}
config['page_size'] = 10
config['webapp2_extras.sessions'] = {
    'secret_key': 'jfdfaeti78fdFfinlifjser'
}

app = webapp2.WSGIApplication(routes, debug=debug, config=config)
app.error_handlers[404] = handle_404
app.error_handlers[500] = handle_500

