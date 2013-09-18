# -*- coding: utf-8 -*-

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
import webapp2
from webapp2_extras import jinja2, sessions, json

from config import *
import models

def uri_for_static(static_uri, host_url=None):
    ret = static_uri
    if static_uri.startswith('/'):
        ret = '%s%s%s'%(host_url if host_url else '', PATH_PREFIX if PATH_PREFIX else '', static_uri)
    return ret

class BaseHandler(webapp2.RequestHandler):

    def dispatch(self):
        head_fly = self.request.headers.get(UPS_HEADER_NAME)
        if CHECK_HOST and self.app.config.get('host_url') and not head_fly:
            self.redirect('%s%s'%(self.app.config.get('host_url'), self.request.path_qs))
            return
        self.session_store = sessions.get_store(request=self.request)
        try:
            webapp2.RequestHandler.dispatch(self)
            # super(BaseHandler, self).dispatch()
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

    def render_response_post_list(self, page_title, post_list, page_mode='list'):
        context = {}
        context['title'] = page_title
        context['category_list'] =  models.get_category_list()
        context['post_list'] = post_list
        context['page_mode'] = page_mode
        context['uri_for'] = webapp2.uri_for
        context['uri_for_static'] = uri_for_static

        # logging.debug('category_list {0}'.format(context))
        self.render_response('post.html', context)
        # self.response.write('a')


def create_file_upload_url(request):
    # return blobstore.create_upload_url(webapp2.get_app().router.build(request, 'upload', [], {}))
    return blobstore.create_upload_url(webapp2.uri_for('upload'))

#class UploadHandler(webapp2.RequestHandler):
#    def get(self):
#        upload_url = blobstore.create_upload_url('/upload')
#        self.response.out.write('<html><body>')
#        self.response.out.write('<form action="%s" method="POST" enctype="multipart/form-data">' % upload_url)
#        self.response.out.write("""Upload File: <input type="file" name="file"> <br><input type="submit" name="submit"
#            value="submit"></form></body></html>""")

def create_file_url(uploaded_file):
    #link = '/serv/{0}/{1}'.format(uploaded_file.key().id(), uploaded_file.file_name)
    #if PATH_PREFIX:
    #    return PATH_PREFIX + link
    #return link
    return webapp2.uri_for('serv', file_id=uploaded_file.key().id(), file_name=uploaded_file.file_name)

class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        #user = users.get_current_user()
        #if not user:
        #    self.redirect(users.create_login_url(self.request.uri))

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
        self.response.out.write(json.encode(oj))
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