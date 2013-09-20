# -*- coding: utf-8 -*-

import webapp2
from google.appengine.api import users

from handlers import *
import models


class BaseAdminHandler(BaseHandler):
    pass

class AdminHandler(BaseAdminHandler):
    #@admin_required
    def get(self):
        home_url = webapp2.uri_for('home')
        if self.app.config.get('host_url'):
            home_url = '%s%s'%(self.app.config.get('host_url'), home_url)
        logout_url = users.create_logout_url(home_url)
        self.render_response('admin_base.html', {'uri_for': webapp2.uri_for, 'logout_url':logout_url, 'uri_for_static':uri_for_static})


class AdminUserHandler(BaseAdminHandler):
    #@admin_required
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
        ctx['uri_for_static'] = uri_for_static
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
    #@admin_required
    def get(self):
        cid = self.request.get('cid')
        category = models.get_category_by_id(cid)
        action = self.request.get('action')
        if action == 'delete' and category:
            category.delete()
            category = None
        self.render_page(category)
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
        self.render_page()

    def render_page(self, category=None):
        ctx = {}
        ctx['category'] = category
        ctx['category_list'] = models.get_category_list()
        ctx['uri_for'] = webapp2.uri_for
        ctx['uri_for_static'] = uri_for_static
        self.render_response('admin_category.html',ctx)

class AdminPostListHandler(BaseAdminHandler):
    #@admin_required
    def get(self):
        # user = users.get_current_user()
        # user = self.request.headers.get(UPS_HEADER_NAME)
        #if not user:
        #    self.redirect(self.uri_for('home'))
        #    return

        post_criteria = models.PostCriteria.new_criteria()
        page = self.request.get('page')
        if page and page.isdigit():
            post_criteria.pager.set_page(int(page))
        post_criteria.published_status = 'all'
        post_list = models.query_post(post_criteria)
        self.render_response('admin_post_list.html', {'post_list':post_list, 
            'pager': post_criteria.pager,
            'uri_for':webapp2.uri_for, 
            'uri_for_static':uri_for_static})

class AdminPostHandler(BaseAdminHandler):
    #@admin_required
    def get(self):
        post_id = self.request.get('id')
        if post_id != None:
            post = models.get_post_by_id(post_id)

        ctx = {'post': post, 'category_list':models.get_category_list(), 'uri_for':webapp2.uri_for, 'uri_for_static':uri_for_static}
        ctx['upload_url'] = create_file_upload_url(self.request)
        self.render_response('admin_post.html', ctx)
    def post(self):
        #user = users.get_current_user()
        #if not user:
        #    self.redirect(users.create_login_url(self.request.uri))
        user = 'my12time@gmail.com'
        account = models.get_account(user)
        if not account:
            self.redirect(self.uri_for('admin-user'))
            return
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
        else:
            post_data['published'] = False

        post_data['tags'] = self.request.get('tags')
        # logging.warn('get tags: %s'%post_tags)
        post = models.save_post_lon(user, post_id, post_data)
        ctx = {'post': post, 'category_list':models.get_category_list(), 'uri_for':webapp2.uri_for, 'uri_for_static':uri_for_static}
        ctx['upload_url'] = create_file_upload_url(self.request)
        self.render_response('admin_post.html',ctx)

class AdminDeletePostHandler(BaseAdminHandler):
    #@admin_required
    def get(self):
        post_id = self.request.get('id')
        models.delete_post_by_id(post_id)
        self.redirect(self.uri_for('admin-post-list'))

class AdminFileHandler(BaseAdminHandler):
    #@admin_required
    def get(self):
        ctx = {'file_list':models.get_uploaded_file_list(), 'uri_for':webapp2.uri_for, 'uri_for_static':uri_for_static}
        ctx['upload_url'] = create_file_upload_url(self.request)
        self.render_response('admin_file.html', ctx)

class AdminFileDeleteHandler(BaseAdminHandler):
    #@admin_required
    def get(self, file_id):
        uploadedFile = models.get_file(file_id)
        if uploadedFile:
            blobInfo = uploadedFile.store_key
            if blobInfo:
                #blobstore.delete(blob_key)
                blobInfo.delete()
            uploadedFile.delete()
        self.redirect(self.uri_for('admin-file'))