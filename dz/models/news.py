from __future__ import unicode_literals
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html, strip_tags
from .common import ARCHIVED_CHOICES
from .common import cut_str


class NewsManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self, *args, **kw):
        qs = super(NewsManager, self).get_queryset(*args, **kw)
        return qs.defer('content', 'subtable')


@python_2_unicode_compatible
class News(models.Model):
    id = models.IntegerField(_('news id'), db_column='pk', primary_key=True)
    url = models.URLField(_('news link'))
    title = models.CharField(_('news title'), max_length=150)
    short_title = models.CharField(_('participants'), max_length=80)
    section = models.CharField(_('sport'), max_length=20)
    subsection = models.CharField(_('liga'), max_length=80)
    published = models.DateTimeField(_('published'))
    updated = models.DateTimeField(_('updated'))
    crawled = models.DateTimeField(_('fetched'))
    archived = models.CharField(_('archived'), max_length=9, choices=ARCHIVED_CHOICES)
    preamble = models.CharField(_('news preamble'), max_length=500, null=True)
    content = models.TextField(_('full news content'))
    subtable = models.TextField(_('news subtable'))

    def col_content(self):
        return format_html(
            u'<div class="dz_pre">{pre}</div> <div class="dz_body"><span>'
            u'{text}</span> <a href="{url}" target="_blank">(more...)</a></div>',
            pre=cut_str(strip_tags(self.preamble), 60),
            text=cut_str(strip_tags(self.content), 100),
            url='/show_stub?id=%s' % self.id)
    col_content.short_description = _('short news content')
    col_content.admin_order_field = 'preamble'

    def __str__(self):
        return u'{} ({})'.format(self.title, self.id)

    objects = NewsManager()

    class Meta:
        verbose_name = _('news')
        verbose_name_plural = _('newss')
        index_together = [
            ['published', 'archived']
        ]
        permissions = [
            ('crawl_news', _('Can crawl news')),
            ('view_news', _('Can only view news')),
        ]
