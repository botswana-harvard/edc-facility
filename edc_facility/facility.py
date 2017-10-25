import arrow

from collections import OrderedDict
from datetime import datetime
from dateutil.relativedelta import relativedelta, weekday
from edc_base.utils import get_utcnow

from .holidays import Holidays


class Facility:

    holiday_cls = Holidays

    def __init__(self, name=None, days=None, slots=None, forward_only=None, **kwargs):
        self.days = []
        self.name = name
        for day in days:
            try:
                day.weekday
            except AttributeError:
                day = weekday(day)
            self.days.append(day)
        self.slots = slots or [99999 for _ in self.days]
        self.forward_only = True if forward_only is None else forward_only
        self.config = OrderedDict(zip([str(d) for d in self.days], self.slots))
        self.holidays = self.holiday_cls(**kwargs)

    def __str__(self):
        return '{} {}'.format(
            self.name.title(),
            ', '.join([str(day) + '(' + str(slot) + ' slots)' for day, slot in self.config.items()]))

    def slots_per_day(self, day):
        try:
            slots_per_day = self.config.get(str(day))
        except KeyError:
            slots_per_day = 0
        return slots_per_day

    @property
    def weekdays(self):
        return [d.weekday for d in self.days]

    def open_slot_on(self, r):
        return True

    def to_arrow_utc(self, dt):
        """Returns timezone-aware datetime as a UTC arrow object."""
        return arrow.Arrow.fromdatetime(dt, dt.tzinfo).to('utc')

    def is_holiday(self, arr_utc=None):
        """Returns the arrow object, arr_utc, of a suggested calendar date if not a holiday.
        """
        return self.holidays.is_holiday(utc_datetime=arr_utc.datetime)

    def available_datetime(self, suggested_datetime=None, forward_delta=None,
                           reverse_delta=None, taken_datetimes=None):
        """Returns a datetime closest to the suggested datetime based
        on the configuration of the facility.

        To exclude datetimes other than holidays, pass a list of
        datetimes in UTC to `taken_datetimes`."""
        available_rdate = None
        forward_delta = forward_delta or relativedelta(months=1)
        if not self.forward_only and reverse_delta:
            reverse_delta = reverse_delta
        else:
            reverse_delta = relativedelta(months=0)
        if suggested_datetime:
            suggested_rdate = arrow.Arrow.fromdatetime(suggested_datetime)
        else:
            suggested_rdate = arrow.Arrow.fromdatetime(get_utcnow())
        maximum = self.to_arrow_utc(suggested_rdate.datetime + forward_delta)
        minimum = self.to_arrow_utc(suggested_rdate.datetime + reverse_delta)
        taken = [self.to_arrow_utc(dt) for dt in taken_datetimes or []]
        for r in arrow.Arrow.span_range('day', minimum.datetime, maximum.datetime):
            # add back time to arrow object, r
            r = arrow.Arrow.fromdatetime(
                datetime.combine(r[0].date(), suggested_rdate.time()))
            # see if available
            if (r.datetime.weekday() in self.weekdays
                    and (suggested_rdate.date() <= r.date() < maximum.date())):
                if (not self.is_holiday(r)
                        and r.date() not in [d.date() for d in taken]
                        and self.open_slot_on(r)):
                    available_rdate = r
                    break
        return available_rdate
