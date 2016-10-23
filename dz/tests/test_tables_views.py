from django.test import tag
from django.urls import reverse
from dz import models
from . import base, views


@tag('views')
class TableViewsTests(base.BaseDzTestCase, views.ListViewTestsMixin):
    MODEL_TABLE_SIZES = {
        'news': base.MODEL_BATCH_SIZE,  # created from factory batch
        'tip': base.MODEL_BATCH_SIZE,  # created from factory batch
        'crawl': base.MODEL_BATCH_SIZE,  # created from factory batch
        'user': len(base.TEST_USERS),  # created from hardcoded list
        'schedule': 5,  # created from fixture "schedule.json"
    }

    def test_unauthorized_request_should_redirect_to_login(self):
        for model_name in ('news', 'tip', 'crawl', 'user', 'schedule'):
            list_url = reverse('dz:%s-list' % model_name)
            login_url = '%s?next=%s' % (reverse('dz-admin:login'), list_url)
            response = self.client.get(list_url)
            self.assertRedirects(response, login_url)

    def _test_table_view(self, user_name, model_name,
                         can_access=True, can_crawl=None,
                         can_use_row_actions=None):
        info = ' (user: {}, model: {})'.format(user_name, model_name)
        list_url = reverse('dz:%s-list' % model_name)
        response = self.client.get(list_url)

        if not can_access:
            self.assertEquals(response.status_code, 403)
            return

        self.assertContains(response, '>{}</p>'.format(user_name),
                            msg_prefix='user name should be in the top menu' + info)

        expected_text = 'List (%d)' % self.MODEL_TABLE_SIZES[model_name]
        self.assertContains(response, expected_text,
                            msg_prefix='table item count should be visible' + info)

        model_name_plural = model_name + ('' if model_name == 'news' else 's')
        crawl_button_text = '>Crawl %s Now</button>' % model_name_plural.title()
        if can_crawl is True:
            self.assertContains(response, crawl_button_text,
                                msg_prefix='crawl button should be present' + info)
        if can_crawl is False:
            self.assertNotContains(response, crawl_button_text,
                                   msg_prefix='crawl button should not be present' + info)

        row_selector_text = '<th class="col-row_selector">'
        row_actions_text = '<th class="col-row_actions">'
        if can_use_row_actions is True:
            self.assertContains(response, row_selector_text,
                                msg_prefix='row selector should be present' + info)
            self.assertContains(response, row_actions_text,
                                msg_prefix='row actions should be present' + info)
        if can_use_row_actions is False:
            self.assertNotContains(response, row_selector_text,
                                   msg_prefix='row selector should be hidden' + info)
            self.assertNotContains(response, row_actions_text,
                                   msg_prefix='row actions should be hidden' + info)


@tag('actions')
class RowActionFormTests(base.BaseDzTestCase):
    def test_simple_users_cannot_delete(self):
        with self.login_as('simple'):
            form_url = reverse('dz:row-action')
            for model_name in ('news', 'tip', 'crawl', 'user', 'schedule'):
                data = dict(model_name=model_name, action='delete', row_ids='1')
                response = self.client.post(form_url, data)
                self.assertEquals(response.status_code, 403)

    def test_row_action_form_can_detect_invalid_parameters(self):
        msg_base = 'Row action form should detect '
        form_url = reverse('dz:row-action')

        def assertFails(params, description):
            response = self.client.post(form_url, params)
            self.assertEquals(response.status_code, 400, msg=msg_base + description)

        with self.login_as('super'):
            self.assertEquals(self.client.get(form_url).status_code, 403,
                              msg=msg_base + 'GET request')
            assertFails({},
                        'empty post')
            assertFails(dict(model_name='trump', action='delete', row_ids='1'),
                        'invalid model')
            assertFails(dict(model_name='news', action='', row_ids='1'),
                        'empty action')
            assertFails(dict(model_name='news', action='trump', row_ids='1'),
                        'invalid action')
            assertFails(dict(model_name='news', action='delete', row_ids=''),
                        'empty ids')
            assertFails(dict(model_name='news', action='delete', row_ids='1,X'),
                        'invalid ids')

    @models.Schedule.suspend_logging
    def test_admin_users_can_delete(self):
        with self.login_as('super'):
            form_url = reverse('dz:row-action')
            for model_name in ('news', 'tip', 'crawl', 'user', 'schedule'):
                ModelClass = getattr(models, model_name.title())
                list_url = reverse('dz:%s-list' % model_name)
                count_before = ModelClass.objects.count()

                if model_name == 'user':
                    # Don't remove current user, else the current login session would break.
                    queryset = ModelClass.objects.filter(username__in=['admin', 'simple'])
                else:
                    queryset = ModelClass.objects.all()
                del_ids = sorted(queryset.values_list('pk', flat=True))[:2]

                msg = '{} action form should redirect to {}'.format(model_name, list_url)
                data = {
                    'model_name': model_name,
                    'action': 'delete',
                    'row_ids': '%d,%d' % tuple(del_ids)
                }
                response = self.client.post(form_url, data)
                self.assertRedirects(response, list_url, msg_prefix=msg)

                msg = '{:d} {} objects should be deleted'.format(len(del_ids), model_name)
                count_after = ModelClass.objects.count()
                self.assertEquals(count_after, count_before - len(del_ids), msg=msg)
