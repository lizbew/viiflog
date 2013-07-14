import datetime
from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.api import memcache
import logging
import utils
import datetime

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
            return some_date.strftime('%Y-%m-%d %H:%M')
        return None

    def get_tags_str(self):
        if self.tags:
            return ' '.join(self.tags)
        return ''

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
        tag_list = post_data['tags'].strip().split()
        if len(tag_list) > 0:
            saved_post.tags = tag_list

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
    published_status = 'all' # published, unpublished, all
    page = 0
    page_size = 10
    category = None
    tag = None

    def select_published(self):
        self.published_status = 'published'
    def select_unpublished(self):
        self.published_status = 'unpublished'


def create_post_criteria(category = None, tag = None):
    criteria = PostCriteria()
    criteria.category = category
    criteria.tag = tag
    if tag or category:
        criteria.select_published()
    return criteria

def query_post(query_criteria):
    q = Post.all()
    page_size = 10
    if query_criteria:
        if query_criteria.published_status == 'published':
            q.filter('published =', True)
            q.order('-published_date')
        elif query_criteria.published_status == 'unpublished':
            q.filter('published =', False)
            q.order('-created_date')

        if query_criteria.category:
            category = find_category(query_criteria.category)
            if not category:
                return None
            else:
                q.filter('category =', category)
        if query_criteria.tag:
            q.filter('tags =', query_criteria.tag)
        page_size = query_criteria.page_size
    else:
        q.order('-created_date')
    return q.run(limit=page_size)

def find_post_by_category(name, result_limit=10):
    c = create_post_criteria(category=name)
    return query_post(c)

def find_post_by_tag(name, result_limit=10):
    c = create_post_criteria(tag=name)
    return query_post(c)

def get_user_list():
    q = Account.all()
    return q.run()

def get_account(user):
    if not user:
        return None
    q = Account.all().filter('email =', user.email())
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
    return q.run()

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

