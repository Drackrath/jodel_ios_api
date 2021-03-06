# -*- coding: utf-8 -*-

from __future__ import (absolute_import, print_function, unicode_literals)
from builtins import input
from future.standard_library import install_aliases
install_aliases()
from collections import OrderedDict

import base64
import datetime
from hashlib import sha1, sha256
import hmac
import simplejson as json
import random
import requests
from urllib.parse import urlparse
import uuid
import time
import decimal

s = requests.Session()

class JodelAccount:
    post_colors = ['9EC41C', 'FF9908', 'DD5F5F', '8ABDB0', '06A3CB', 'FFBA00']

    api_url = "https://api.go-tellm.com/api{}"
    client_id = 'cd871f92-a23f-4afc-8fff-51ff9dc9184e'
    secret = 'ENTER_KEY_HERE'.encode('ascii')
    version = '4.39'


    access_token = None
    device_uid = None

    def __init__(self, lat, lng, city, country=None, name=None, update_location=True,
                 access_token=None, device_uid=None, refresh_token=None, distinct_id=None, expiration_date=None, **kwargs):

        self.lat, self.lng, self.location_dict = lat, lng, self._get_location_dict(lat, lng, city, country, name)

        if device_uid:
            self.device_uid = device_uid

        if access_token and device_uid and refresh_token and distinct_id and expiration_date:
            self.expiration_date = expiration_date
            self.distinct_id = distinct_id
            self.refresh_token = refresh_token
            self.access_token = access_token
            if update_location:
                r = self.set_location(lat, lng, city, country, name, **kwargs)
                if r[0] != 204:
                    raise Exception("Error updating location: " + str(r))

        else:
            r = self.refresh_all_tokens(**kwargs)
            if r[0] != 200:
                raise Exception("Error creating new account: " + str(r))

    def _send_request(self, method, endpoint, params=None, payload=None, **kwargs):
        url = self.api_url.format(endpoint)
        short_lat = round(self.lat, 4)
        short_lng = round(self.lng, 4)
        headers = {'User-Agent': 'Jodel/{} (iPhone; iOS 12.1.1;Scale/3.00)'.format(self.version),
                   'Accept-Encoding': 'br, gzip, deflate',
                   'Accept-Language': 'it-IT;q=1, en-US;q=0.9',
                   'X-Location': '{};{}'.format(short_lat, short_lng),
                   'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + self.access_token if self.access_token else None}

        for _ in range(3):
            self._sign_request(method, url, headers, params, payload)
            data = json.dumps(payload, use_decimal=True).replace(": ", ":").replace(", ", ",") if payload is not None else None
            resp = s.request(method=method, url=url, params=params, data=data, headers=headers, **kwargs)
            if resp.status_code != 502:  # Retry on error 502 "Bad Gateway"
                break

        try:
            resp_text = resp.json(encoding="utf-8")
        except:
            resp_text = resp.text

        return resp.status_code, resp_text

    def _sign_request(self, method, url, headers, params=None, payload=None):
        timestamp = datetime.datetime.utcnow().isoformat()[:-7] + "Z"
        short_lat = round(self.lat, 4)
        short_lng = round(self.lng, 4)

        req = [method,
               urlparse(url).netloc,
               "443",
               urlparse(url).path,
               self.access_token if self.access_token else "",
               '{};{}'.format(short_lat, short_lng),
               timestamp,
               "%".join(sorted("{}%{}".format(key, value) for key, value in (params if params else {}).items())),
               json.dumps(payload, use_decimal=True).replace(": ", ":").replace(", ", ",") if payload else ""]

        secret, version = self.secret, self.version

        signature = hmac.new(secret, "%".join(req).encode("utf-8"), sha1).hexdigest().upper()

        headers['X-Authorization'] = 'HMAC ' + signature
        headers['X-Client-Type'] = 'ios_{}'.format(version)
        headers['X-Timestamp'] = timestamp
        headers['X-Api-Version'] = '0.2'

    @staticmethod
    def _get_location_dict(lat, lng, city, country=None, name=None):    
        return OrderedDict([("loc_coordinates", {"lat": lat, "lng": lng}),
                ("loc_accuracy", 65),
                ("country", country if country else "IT"),
                ("city", city)
        ])

    def get_account_data(self):
        return {'expiration_date': self.expiration_date, 'distinct_id': self.distinct_id,
                'refresh_token': self.refresh_token, 'device_uid': self.device_uid, 'access_token': self.access_token}

    def refresh_all_tokens(self, **kwargs):
        """ Creates a new account with random ID if self.device_uid is not set. Otherwise renews all tokens of the
        account with ID = self.device_uid. """
        if not self.device_uid:
            print("Creating new account.")
            randomUUID = str(uuid.uuid4())
            device_uid_raw = '45C2B096-DFDA-4B1A-A404-26FB4328F358' + randomUUID.replace("-", "") + '0984FC52-FF93-44EB-BD44-3A5C521BAC5E'
            self.device_uid = base64.b64encode(sha256(device_uid_raw.encode()).digest())

        payload = OrderedDict([
            ("language", "it-IT"),
            ("client_id", self.client_id),
            ("location", self.location_dict),
            ("device_uid", self.device_uid)
        ])
        
        resp = self._send_request("POST", "/v2/users", payload=payload, **kwargs)
        if resp[0] == 200:
            self.access_token = resp[1]['access_token']
            self.expiration_date = resp[1]['expiration_date']
            self.refresh_token = resp[1]['refresh_token']
            self.distinct_id = resp[1]['distinct_id']
        else:
            raise Exception(resp)
        return resp

    def refresh_access_token(self, **kwargs):
        payload = {"client_id": self.client_id,
                   "distinct_id": self.distinct_id,
                   "refresh_token": self.refresh_token}

        resp = self._send_request("POST", "/v2/users/refreshToken", payload=payload, **kwargs)
        if resp[0] == 200:
            self.access_token = resp[1]['access_token']
            self.expiration_date = resp[1]['expiration_date']
        return resp

    def send_push_token(self, push_token, **kwargs):
        payload={"client_id": self.client_id, "push_token": push_token}
        return self._send_request("PUT", "/v2/users/pushToken", payload=payload, **kwargs)

    def verify_push(self, server_time, verification_code, **kwargs):
        payload={"server_time": server_time, "verification_code": verification_code}
        return self._send_request("POST", "/v3/user/verification/push", payload=payload, **kwargs)

    def verify(self, android_account=None, **kwargs):
        pass

    def _read_verificiation(self, android_account):
        pass

    # ################# #
    # GET POSTS METHODS #
    # ################# #

    def _get_posts(self, post_types="", skip=0, limit=60, after=None, mine=False, hashtag=None, channel=None, pictures=False, **kwargs):
        category = "mine" if mine else "hashtag" if hashtag else "channel" if channel else "location"
        url_params = {"api_version": "v2" if not (hashtag or channel or pictures) else "v3",
                      "pictures_posts": "pictures" if pictures else "posts",
                      "category": category,
                      "post_types": post_types}
        params = {"lat": self.lat,
                  "lng": self.lng,
                  "skip": skip,
                  "limit": limit,
                  "hashtag": hashtag,
                  "channel": channel,
                  "after": after}

        url = "/{api_version}/{pictures_posts}/{category}/{post_types}".format(**url_params)
        return self._send_request("GET", url, params=params, **kwargs)

    def get_posts_recent(self, skip=0, limit=60, after=None, mine=False, hashtag=None, channel=None, **kwargs):
        return self._get_posts('', skip, limit, after, mine, hashtag, channel, **kwargs)

    def get_posts_popular(self, skip=0, limit=60, after=None, mine=False, hashtag=None, channel=None, **kwargs):
        return self._get_posts('popular', skip, limit, after, mine, hashtag, channel, **kwargs)

    def get_posts_discussed(self, skip=0, limit=60, after=None, mine=False, hashtag=None, channel=None, **kwargs):
        return self._get_posts('discussed', skip, limit, after, mine, hashtag, channel, **kwargs)

    def get_pictures_recent(self, skip=0, limit=60, after=None, **kwargs):
        return self._get_posts('', skip, limit, after, pictures=True, **kwargs)

    def get_pictures_popular(self, skip=0, limit=60, after=None, **kwargs):
        return self._get_posts('popular', skip, limit, after, pictures=True, **kwargs)

    def get_pictures_discussed(self, skip=0, limit=60, after=None, **kwargs):
        return self._get_posts('discussed', skip, limit, after, pictures=True, **kwargs)

    def get_my_pinned_posts(self, skip=0, limit=60, after=None, **kwargs):
        return self._get_posts('pinned', skip, limit, after, True, **kwargs)

    def get_my_replied_posts(self, skip=0, limit=60, after=None, **kwargs):
        return self._get_posts('replies', skip, limit, after, True, **kwargs)

    def get_my_voted_posts(self, skip=0, limit=60, after=None, **kwargs):
        return self._get_posts('votes', skip, limit, after, True, **kwargs)

    def post_search(self, message, skip=0, limit=60, **kwargs):
        params = {"skip": skip, "limit": limit}
        payload = {"message": message}
        return self._send_request("POST", "/v3/posts/search", params=params, payload=payload, **kwargs)

    # ################### #
    # SINGLE POST METHODS #
    # ################### #

    def create_post(self, message=None, imgpath=None, b64img=None, color=None, ancestor=None, channel="", **kwargs):
        if not imgpath and not message and not b64img:
            raise ValueError("One of message or imgpath must not be null.")

        payload = {"color": color if color else random.choice(self.post_colors),
                   "location": self.location_dict,
                   "ancestor": ancestor,
                   "message": message,
                   "channel": channel}
        if imgpath:
            with open(imgpath, "rb") as f:
                imgdata = base64.b64encode(f.read()).decode("utf-8")
                payload["image"] = imgdata
        elif b64img:
            payload["image"] = b64img

        return self._send_request("POST", '/v3/posts/', payload=payload, **kwargs)

    def get_post_details(self, post_id, **kwargs):
        return self._send_request("GET", '/v2/posts/{}/'.format(post_id), **kwargs)

    def get_post_details_v3(self, post_id, skip=0, **kwargs):
        return self._send_request("GET", '/v3/posts/{}/details'.format(post_id),
                                  params={'details': 'true', 'reply': skip}, **kwargs)

    def upvote(self, post_id, **kwargs):
        return self._send_request("PUT", '/v2/posts/{}/upvote/'.format(post_id), **kwargs)

    def downvote(self, post_id, **kwargs):
        return self._send_request("PUT", '/v2/posts/{}/downvote/'.format(post_id), **kwargs)

    def give_thanks(self, post_id, **kwargs):
        return self._send_request("POST", '/v3/posts/{}/giveThanks'.format(post_id), **kwargs)

    def get_share_url(self, post_id, **kwargs):
        return self._send_request("POST", "/v3/posts/{}/share".format(post_id), **kwargs)

    def pin(self, post_id, **kwargs):
        return self._send_request("PUT", "/v2/posts/{}/pin".format(post_id), **kwargs)

    def unpin(self, post_id, **kwargs):
        return self._send_request("PUT", "/v2/posts/{}/unpin".format(post_id), **kwargs)

    def enable_notifications(self, post_id, **kwargs):
        return self._send_request("PUT", "/v2/posts/{}/notifications/enable".format(post_id), **kwargs)

    def disable_notifications(self, post_id, **kwargs):
        return self._send_request("PUT", "/v2/posts/{}/notifications/disable".format(post_id), **kwargs)

    def delete_post(self, post_id, **kwargs):
        return self._send_request("DELETE", "/v2/posts/{}".format(post_id), **kwargs)

    # ################### #
    # STICKY POST METHODS #
    # ################### #

    def upvote_sticky_post(self, post_id, **kwargs):
        return self._send_request("PUT", "/v3/stickyposts/{}/up".format(post_id), **kwargs)

    def downvote_sticky_post(self, post_id, **kwargs):
        return self._send_request("PUT", "/v3/stickyposts/{}/down".format(post_id), **kwargs)

    def dismiss_sticky_post(self, post_id, **kwargs):
        return self._send_request("PUT", "/v3/stickyposts/{}/dismiss".format(post_id), **kwargs)

    # #################### #
    # NOTIFICATION METHODS #
    # #################### #

    def get_notifications(self, **kwargs):
        return self._send_request("PUT", "/v3/user/notifications", **kwargs)

    def get_notifications_new(self, **kwargs):
        return self._send_request("GET", "/v3/user/notifications/new", **kwargs)

    def notification_read(self, post_id=None, notification_id=None, **kwargs):
        if post_id:
            return self._send_request("PUT", "/v3/user/notifications/post/{}/read".format(post_id), **kwargs)
        elif notification_id:
            return self._send_request("PUT", "/v3/user/notifications/{}/read".format(notification_id), **kwargs)
        else:
            raise ValueError("One of post_id or notification_id must not be null.")

    # ############### #
    # CHANNEL METHODS #
    # ############### #

    def get_recommended_channels(self, **kwargs):
        return self._send_request("GET", "/v3/user/recommendedChannels", **kwargs)

    def get_channel_meta(self, channel, **kwargs):
        return self._send_request("GET", "/v3/user/channelMeta", params={"channel": channel}, **kwargs)

    def follow_channel(self, channel, **kwargs):
        return self._send_request("PUT", "/v3/user/followChannel", params={"channel": channel}, **kwargs)

    def unfollow_channel(self, channel, **kwargs):
        return self._send_request("PUT", "/v3/user/unfollowChannel", params={"channel": channel}, **kwargs)

    # ############ #
    # USER METHODS #
    # ############ #

    def set_location(self, lat, lng, city, country=None, name=None, **kwargs):
        self.lat, self.lng, self.location_dict = lat, lng, self._get_location_dict(lat, lng, city, country, name)
        return self._send_request("PUT", "/v2/users/location", payload={"location": self.location_dict}, **kwargs)

    def set_user_profile(self, user_type=None, gender=None, age=None, **kwargs):
        allowed_user_types = ["high_school", "high_school_graduate", "student", "apprentice", "employee", "other", None]
        if user_type and user_type not in allowed_user_types:
            raise ValueError("user_type must be one of {}.".format(allowed_user_types))

        if gender not in ["m", "f", None]:
            raise ValueError("gender must be either m or f.")

        return self._send_request("PUT", "/v3/user/profile", payload={"user_type": user_type, "gender": gender, "age": age}, **kwargs)

    def get_karma(self, **kwargs):
        return self._send_request("GET", "/v2/users/karma", **kwargs)

    def get_user_config(self, **kwargs):
        return self._send_request("GET", "/v3/user/config", **kwargs)


# helper function to mock input
def obtain_input(text):
    return input(text)
