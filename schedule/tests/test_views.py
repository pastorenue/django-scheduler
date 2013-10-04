import datetime
from django.test.utils import override_settings
import pytz
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.test import Client
from schedule.models.calendars import Calendar
from schedule.models.events import Event
from schedule.models.rules import Rule

from schedule.views import check_next_url, coerce_date_dict


class TestViews(TestCase):
    def setUp(self):
        self.rule = Rule.objects.create(frequency="DAILY")
        self.calendar = Calendar.objects.create(name="MyCal", slug='MyCalSlug')
        data = {
            'title': 'Recent Event',
            'start': datetime.datetime(2008, 1, 5, 8, 0, tzinfo=pytz.utc),
            'end': datetime.datetime(2008, 1, 5, 9, 0, tzinfo=pytz.utc),
            'end_recurring_period': datetime.datetime(2008, 5, 5, 0, 0, tzinfo=pytz.utc),
            'rule': self.rule,
            'calendar': self.calendar
        }
        self.event = Event.objects.create(**data)

    @override_settings(USE_TZ=False)
    def test_timezone_off(self):
        url = reverse('day_calendar', kwargs={'calendar_slug': self.calendar.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class TestViewUtils(TestCase):
    def test_check_next_url(self):
        url = "http://thauber.com"
        self.assertTrue(check_next_url(url) is None)
        url = "/hello/world/"
        self.assertEqual(url, check_next_url(url))

    def test_coerce_date_dict(self):
        self.assertEqual(
            coerce_date_dict({'year': '2008', 'month': '4', 'day': '2', 'hour': '4', 'minute': '4', 'second': '4'}),
            {'year': 2008, 'month': 4, 'day': 2, 'hour': 4, 'minute': 4, 'second': 4}
        )

    def test_coerce_date_dict_partial(self):
        self.assertEqual(
            coerce_date_dict({'year': '2008', 'month': '4', 'day': '2'}),
            {'year': 2008, 'month': 4, 'day': 2, 'hour': 0, 'minute': 0, 'second': 0}
        )

    def test_coerce_date_dict_empty(self):
        self.assertEqual(
            coerce_date_dict({}),
            {}
        )

    def test_coerce_date_dict_missing_values(self):
        self.assertEqual(
            coerce_date_dict({'year': '2008', 'month': '4', 'hours': '3'}),
            {'year': 2008, 'month': 4, 'day': 1, 'hour': 0, 'minute': 0, 'second': 0}
        )


c = Client()


class TestUrls(TestCase):
    fixtures = ['schedule.json']
    highest_event_id = 7

    def test_calendar_view(self):
        self.response = c.get(
            reverse("year_calendar", kwargs={"calendar_slug": 'example'}), {})
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.context[0]["calendar"].name,
                         "Example Calendar")

    def test_calendar_month_view(self):
        self.response = c.get(reverse("month_calendar",
                                      kwargs={"calendar_slug": 'example'}),
                              {'year': 2000, 'month': 11})
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.context[0]["calendar"].name,
                         "Example Calendar")
        month = self.response.context[0]["periods"]['month']
        self.assertEqual((month.start, month.end),
                         (datetime.datetime(2000, 11, 1, 0, 0, tzinfo=pytz.utc),
                          datetime.datetime(2000, 12, 1, 0, 0, tzinfo=pytz.utc)))

    def test_event_creation_anonymous_user(self):
        self.response = c.get(reverse("calendar_create_event",
                                      kwargs={"calendar_slug": 'example'}),
            {})
        self.assertEqual(self.response.status_code, 302)

    def test_event_creation_authenticated_user(self):
        c.login(username="admin", password="admin")
        self.response = c.get(reverse("calendar_create_event",
                                      kwargs={"calendar_slug": 'example'}),
            {})
        self.assertEqual(self.response.status_code, 200)

        self.response = c.post(reverse("calendar_create_event",
                                       kwargs={"calendar_slug": 'example'}),
                               {'description': 'description',
                                'title': 'title',
                                'end_recurring_period_1': '10:22:00', 'end_recurring_period_0': '2008-10-30',
                                'end_recurring_period_2': 'AM',
                                'end_1': '10:22:00', 'end_0': '2008-10-30', 'end_2': 'AM',
                                'start_0': '2008-10-30', 'start_1': '09:21:57', 'start_2': 'AM'
                               })
        self.assertEqual(self.response.status_code, 302)

        highest_event_id = self.highest_event_id
        highest_event_id += 1
        self.response = c.get(reverse("event",
                                      kwargs={"event_id": highest_event_id}), {})
        self.assertEqual(self.response.status_code, 200)
        c.logout()

    def test_view_event(self):
        self.response = c.get(reverse("event", kwargs={"event_id": 1}), {})
        self.assertEqual(self.response.status_code, 200)

    def test_delete_event_anonymous_user(self):
        # Only logged-in users should be able to delete, so we're redirected
        self.response = c.get(reverse("delete_event", kwargs={"event_id": 1}), {})
        self.assertEqual(self.response.status_code, 302)

    def test_delete_event_authenticated_user(self):
        c.login(username="admin", password="admin")

        # Load the deletion page
        self.response = c.get(reverse("delete_event", kwargs={"event_id": 1}), {})
        self.assertEqual(self.response.status_code, 200)

        # Delete the event
        self.response = c.post(reverse("delete_event", kwargs={"event_id": 1}), {})
        self.assertEqual(self.response.status_code, 302)

        # Since the event is now deleted, we get a 404
        self.response = c.get(reverse("delete_event", kwargs={"event_id": 1}), {})
        self.assertEqual(self.response.status_code, 404)
        c.logout()

