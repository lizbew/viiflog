# -*- coding: utf-8 -*-
import datetime
from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.api import memcache
import logging
import utils
import math
# import urllib

# fix for UnicodeDecodeError: 'ascii' codec can't decode byte 0xe4 in position 13: ordinal not in range(128)
import sys
default_encoding = 'utf-8'
if sys.getdefaultencoding() != default_encoding:
    reload(sys)
    sys.setdefaultencoding(default_encoding)

class UploadedFile(db.Model):
    file_name = db.StringProperty()
    title = db.StringProperty()
    content_type = db.StringProperty()
    size = db.IntegerProperty()
    store_key = blobstore.BlobReferenceProperty()
    created_date = db.DateTimeProperty(auto_now_add=True)

    def is_img(self):
        return ['image/png'].count(self.content_type) > 0

class Account(db.Model):
    nick_name = db.StringProperty(required=True)
    email = db.EmailProperty(required=True)
    active = db.BooleanProperty(default = True)
    role = db.StringProperty(choices=set(['admin', 'author', 'editor']))
    created_date = db.DateTimeProperty(auto_now_add=True)

class PostCategory(db.Model):
    name = db.StringProperty(required=True)
    label = db.StringProperty()
    # display_seq = db.IntegerProperty()

class PostTag(db.Model):
    name = db.CategoryProperty()
    post_count = db.IntegerProperty()

class Post(db.Model):
    title = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    abstract = db.TextProperty()
    attached_docs = db.ListProperty(int)
    category = db.ReferenceProperty(PostCategory)
    created_date = db.DateTimeProperty(auto_now_add=True)
    updated_date = db.DateTimeProperty(auto_now=True)
    published = db.BooleanProperty(default=False, required=True)
    published_date = db.DateTimeProperty()
    author = db.ReferenceProperty(Account)
    tags = db.StringListProperty()
    archive = db.CategoryProperty()
    _html_content = None
    _html_abstract = None

    def get_id(self):
        if self.key().has_id_or_name():
            return self.key().id_or_name()
        return None

    def get_html_content(self):
        if not self._html_content:
            self._html_content = utils.convert_markdown_text(self.content)
        return self._html_content

    def get_html_abstract(self):
        if not self._html_abstract and self.abstract:
            self._html_abstract = utils.convert_markdown_text(self.abstract)
        if not self._html_abstract:
            self._html_abstract = ""
        return self._html_abstract

    def get_published_date_str(self):
        return self.fmt_date_str(self.published_date)

    def get_updated_date_str(self):
        return self.fmt_date_str(self.updated_date)

    def fmt_date_str(self, some_date):
        if some_date:
            return (some_date+ datetime.timedelta(hours = 8)).strftime('%Y-%m-%d %H:%M')
        return None

    def get_tags_str(self):
        if self.tags:
            return ','.join(self.tags)
        return ''

    #def get_urlencoded_tags(self):
    #    ec_tags = []
    #    for t in self.tags:
    #        ec_tags.append(urllib.quote_plus(t))
    #    return ec_tags

    def has_tags(self):
        return self.tags and len(self.tags) > 0

    def set_published(self, published):
        self.published = published
        if published:
            if not self.published_date:
                self.published_date = datetime.datetime.today()
        else:
            self.published_date = None

class PostViewCount(db.Model):
    post = db.ReferenceProperty(Post)
    view_count = db.IntegerProperty()

class Pager(object):
    def __init__(self, page, page_size):
        self.page_size = page_size if page_size > 0 else 10
        self.current_page = page if page > 0 else 1
        self.total_pages = 1
        self.prev_page = 1
        self.next_page = 1
        #self.total_pages = math.ceil(total_records * 1.0 / self.current_page)
        #self.prev_page = self.current_page - 1 if self.current_page > 1 else 1
        #self.next_page = self.current_page + 1 if self.current_page < self.total_pages else self.total_pages
    def set_total_records(self, total_records):
        self.total_records = total_records
        self.total_pages = int(math.ceil(total_records * 1.0 / self.page_size))
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        self.prev_page = self.current_page - 1 if self.current_page > 1 else 1
        self.next_page = self.current_page + 1 if self.current_page < self.total_pages else self.total_pages

    def get_start_record(self):
        return (self.current_page - 1) * self.page_size
    def set_page(self, page):
        if page > 0:
            self.current_page = page
    def get_prev_page(self):
        if self.current_page > 1:
            return self.current_page - 1
        return None
    def get_next_page(self):
        if self.current_page < self.total_pages:
            return self.current_page + 1
        return None


def save_post_lon(user, post_id, post_data):
    saved_post = get_post_from_datastore_by_id(post_id)
    account = get_account(user)
    category = find_category(post_data['category'])
    if saved_post is None:
        saved_post = Post(title=post_data['title'], content=post_data['content'])
        saved_post.archive = db.Category(datetime.datetime.today().strftime('%Y-%m'))
        if account:
            saved_post.author = account
    else:
        saved_post.title = post_data['title']
        saved_post.content = post_data['content']
        
    if post_data['tags']:
        tags = []
        tag_list = post_data['tags'].strip().split(',')
        for t in tag_list:
            if len(t.strip()) > 0:
                ts = t.strip().split()
                for tt in ts:
                    tags.append(tt)
        if len(tags) > 0:
            saved_post.tags = tags

    saved_post.set_published(post_data['published'])

    saved_post.abstract = post_data['abstract']
    saved_post.category = category
    saved_post.put()
    cache_post(saved_post)
    return saved_post


def get_post_from_datastore_by_id(post_id):
    if post_id is None or post_id == '':
        return None
    return Post.get_by_id(int(post_id))

def get_post_by_id(post_id):
    logging.debug('get post_id: %s'%post_id)
    if post_id is None or post_id == '':
        return None
    post = memcache.get(mc_key_post(post_id))
    if post is not None:
        return post
    else:
        k = db.Key.from_path(Post.kind(), int(post_id))
        post = Post.get(k)
        if post is not None:
            cache_post(post)

        return post

def mc_key_post(post_id):
    return 'post-%s'%post_id

def delete_post_by_id(post_id):
    if not post_id:
        return
    post_k = db.Key.from_path(Post.kind(), int(post_id))
    db.delete(post_k)
    memcache.delete(mc_key_post(post_id))

def cache_post(post):
    post._html_content = utils.convert_markdown_text(post.content)
    if not memcache.add('post-%d'%post.get_id(), post, 10):
        logging.error('Memcache set failed')

class PostCriteria:
    published_status = 'published' # published, unpublished, all
    category = None
    tag = None
    pager = None

    @classmethod
    def new_criteria(cls, category = None, tag = None):
        criteria = PostCriteria()
        criteria.category = category
        criteria.tag = tag
        #if tag is not None:
            # criteria.tag = unicode(tag,'utf-8')
            #criteria.tag = tag.encode('utf-8')
        criteria.pager = Pager(1, 10)
        criteria.published_status = 'published'
        return criteria

def query_post(query_criteria = None):
    if query_criteria is None:
        query_criteria = PostCriteria.new_criteria()
    q = Post.all()

    # publish status
    if query_criteria.published_status == 'published':
        q.filter('published =', True)
        q.order('-published_date')
    elif query_criteria.published_status == 'unpublished':
        q.filter('published =', False)
        q.order('-created_date')
    elif query_criteria.published_status != 'all':
        q.filter('published =', True)
        q.order('-published_date')

    # category
    if query_criteria.category:
        category = find_category(query_criteria.category)
        if not category:
            return None
        else:
            q.filter('category =', category)
    # tag
    if query_criteria.tag:
        q.filter('tags =', query_criteria.tag)

    query_criteria.pager.set_total_records(int(q.count()))
    return q.run(offset=query_criteria.pager.get_start_record(), limit=query_criteria.pager.page_size)

def find_post_by_category(name, result_limit=10):
    c = PostCriteria.new_criteria(category=name)
    return query_post(c)

def find_post_by_tag(name, result_limit=10):
    c = PostCriteria.new_criteria(tag=name)
    return query_post(c)

def get_user_list():
    q = Account.all()
    return q.run()

def get_account(user):
    if not user:
        return None
    q = Account.all().filter('email =', user) # user.email())
    return q.get()

def get_user_by_id(uid):
    if uid:
        u_k = db.Key.from_path(Account.kind(), int(uid))
        return db.get(u_k)
    return None

def save_user(uid, nick_name, email, role, active):
    a = None
    if uid:
        u_k = db.Key.from_path(Account.kind(), int(uid))
        a = db.get(u_k)
    if a:
        a.nick_name = nick_name
        a.email = email
        a.role = role
        a.active = active
    else:
        a = Account(nick_name=nick_name, email=email, role=role, active=active)
    a.put()
    return a

def delete_user(uid):
    a = get_user_by_id(uid)
    if a:
        a.delete()

def get_category_by_id(cid):
    if cid:
        category_k = db.Key.from_path(PostCategory.kind(), int(cid))
        return db.get(category_k)
    return None

def save_category(cid, name, label):
    category = None
    if cid and len(cid) > 0:
        category_k = db.Key.from_path(PostCategory.kind(), int(cid))
        category = db.get(category_k)
    if not category:
        category = PostCategory(name=name, label=label)
    else:
        category.name = name
        category.label = label
    category.put()
    return category

def delete_category(cid):
    if cid:
        c_k = db.key.from_path(PostCategory.kind(), int(cid))
        db.delete(c_k)

def get_category_list():
    q = PostCategory.all()
    ret = []
    for r in q.run():
        ret.append(r)
    return ret

def find_category(name):
    if not name:
        return None
    q = PostCategory.all().filter('name =', name)
    return q.get()

def get_uploaded_file_list():
    q = UploadedFile.all()
    return q.run()

def save_file(blob_info, title):
    uploaded_file = UploadedFile(title=title, store_key=blob_info.key())
    uploaded_file.file_name = blob_info.filename
    uploaded_file.content_type = blob_info.content_type
    uploaded_file.size = blob_info.size
    uploaded_file.put()
    return uploaded_file

def get_file(file_id):
    if file_id:
        file_k = db.Key.from_path(UploadedFile.kind(), int(file_id))
        return db.get(file_k)
    return None

