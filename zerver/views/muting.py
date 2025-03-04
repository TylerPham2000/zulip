import datetime
from typing import Optional

from django.http import HttpRequest, HttpResponse
from django.utils.timezone import now as timezone_now
from django.utils.translation import ugettext as _

from zerver.lib.actions import do_mute_topic, do_mute_user, do_unmute_topic, do_unmute_user
from zerver.lib.request import REQ, has_request_variables
from zerver.lib.response import json_error, json_success
from zerver.lib.streams import (
    access_stream_by_id,
    access_stream_by_name,
    access_stream_for_unmute_topic_by_id,
    access_stream_for_unmute_topic_by_name,
    check_for_exactly_one_stream_arg,
)
from zerver.lib.topic_mutes import topic_is_muted
from zerver.lib.user_mutes import user_is_muted
from zerver.lib.users import access_user_by_id
from zerver.lib.validator import check_int
from zerver.models import UserProfile


def mute_topic(
    user_profile: UserProfile,
    stream_id: Optional[int],
    stream_name: Optional[str],
    topic_name: str,
    date_muted: datetime.datetime,
) -> HttpResponse:
    if stream_name is not None:
        (stream, sub) = access_stream_by_name(user_profile, stream_name)
    else:
        assert stream_id is not None
        (stream, sub) = access_stream_by_id(user_profile, stream_id)

    if topic_is_muted(user_profile, stream.id, topic_name):
        return json_error(_("Topic already muted"))

    do_mute_topic(user_profile, stream, topic_name, date_muted)
    return json_success()


def unmute_topic(
    user_profile: UserProfile, stream_id: Optional[int], stream_name: Optional[str], topic_name: str
) -> HttpResponse:
    error = _("Topic is not muted")

    if stream_name is not None:
        stream = access_stream_for_unmute_topic_by_name(user_profile, stream_name, error)
    else:
        assert stream_id is not None
        stream = access_stream_for_unmute_topic_by_id(user_profile, stream_id, error)

    if not topic_is_muted(user_profile, stream.id, topic_name):
        return json_error(error)

    do_unmute_topic(user_profile, stream, topic_name)
    return json_success()


@has_request_variables
def update_muted_topic(
    request: HttpRequest,
    user_profile: UserProfile,
    stream_id: Optional[int] = REQ(validator=check_int, default=None),
    stream: Optional[str] = REQ(default=None),
    topic: str = REQ(),
    op: str = REQ(),
) -> HttpResponse:

    check_for_exactly_one_stream_arg(stream_id=stream_id, stream=stream)

    if op == "add":
        return mute_topic(
            user_profile=user_profile,
            stream_id=stream_id,
            stream_name=stream,
            topic_name=topic,
            date_muted=timezone_now(),
        )
    elif op == "remove":
        return unmute_topic(
            user_profile=user_profile,
            stream_id=stream_id,
            stream_name=stream,
            topic_name=topic,
        )


def mute_user(request: HttpRequest, user_profile: UserProfile, muted_user_id: int) -> HttpResponse:
    if user_profile.id == muted_user_id:
        return json_error(_("Cannot mute self"))

    muted_user = access_user_by_id(user_profile, muted_user_id, allow_bots=False, for_admin=False)
    date_muted = timezone_now()

    if user_is_muted(user_profile, muted_user):
        return json_error(_("User already muted"))

    do_mute_user(user_profile, muted_user, date_muted)
    return json_success()


def unmute_user(
    request: HttpRequest, user_profile: UserProfile, muted_user_id: int
) -> HttpResponse:
    muted_user = access_user_by_id(user_profile, muted_user_id, allow_bots=False, for_admin=False)

    if not user_is_muted(user_profile, muted_user):
        return json_error(_("User is not muted"))

    do_unmute_user(user_profile, muted_user)
    return json_success()
