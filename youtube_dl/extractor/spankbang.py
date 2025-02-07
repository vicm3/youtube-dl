from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    merge_dicts,
    orderedSet,
    parse_duration,
    parse_resolution,
    str_to_int,
    url_or_none,
    urlencode_postdata,
)


class SpankBangIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?spankbang\.com/(?P<id>[\da-z]+)/(?:video|play|embed)\b'
    _TESTS = [{
        'url': 'http://spankbang.com/3vvn/video/fantasy+solo',
        'md5': '1cc433e1d6aa14bc376535b8679302f7',
        'info_dict': {
            'id': '3vvn',
            'ext': 'mp4',
            'title': 'fantasy solo',
            'description': 'dillion harper masturbates on a bed',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'silly2587',
            'timestamp': 1422571989,
            'upload_date': '20150129',
            'age_limit': 18,
        }
    }, {
        # 480p only
        'url': 'http://spankbang.com/1vt0/video/solvane+gangbang',
        'only_matching': True,
    }, {
        # no uploader
        'url': 'http://spankbang.com/lklg/video/sex+with+anyone+wedding+edition+2',
        'only_matching': True,
    }, {
        # mobile page
        'url': 'http://m.spankbang.com/1o2de/video/can+t+remember+her+name',
        'only_matching': True,
    }, {
        # 4k
        'url': 'https://spankbang.com/1vwqx/video/jade+kush+solo+4k',
        'only_matching': True,
    }, {
        'url': 'https://m.spankbang.com/3vvn/play/fantasy+solo/480p/',
        'only_matching': True,
    }, {
        'url': 'https://m.spankbang.com/3vvn/play',
        'only_matching': True,
    }, {
        'url': 'https://spankbang.com/2y3td/embed/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(
            url.replace('/%s/embed' % video_id, '/%s/video' % video_id),
            video_id, headers={'Cookie': 'country=US'})

        if re.search(r'<[^>]+\bid=["\']video_removed', webpage):
            raise ExtractorError(
                'Video %s is not available' % video_id, expected=True)

        formats = []

        def extract_format(format_id, format_url):
            f_url = url_or_none(format_url)
            if not f_url:
                return
            f = parse_resolution(format_id)
            f.update({
                'url': f_url,
                'format_id': format_id,
            })
            formats.append(f)

        STREAM_URL_PREFIX = 'stream_url_'

        for mobj in re.finditer(
                r'%s(?P<id>[^\s=]+)\s*=\s*(["\'])(?P<url>(?:(?!\2).)+)\2'
                % STREAM_URL_PREFIX, webpage):
            extract_format(mobj.group('id', 'url'))

        if not formats:
            stream_key = self._search_regex(
                r'data-streamkey\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
                webpage, 'stream key', group='value')

            sb_session = self._get_cookies(
                'https://spankbang.com')['sb_session'].value

            stream = self._download_json(
                'https://spankbang.com/api/videos/stream', video_id,
                'Downloading stream JSON', data=urlencode_postdata({
                    'id': stream_key,
                    'data': 0,
                    'sb_session': sb_session,
                }), headers={
                    'Referer': url,
                    'X-Token': sb_session,
                })

            for format_id, format_url in stream.items():
                if format_id in ('240p','320p','480p','720p','1080p','4k'):
                    if format_url and isinstance(format_url, list):
                        format_url = format_url[0]
                    extract_format(
                        format_id, format_url)

        self._sort_formats(formats)

        info = self._search_json_ld(webpage, video_id, default={})

        title = self._html_search_regex(
            r'(?s)<h1[^>]*>(.+?)</h1>', webpage, 'title', default=None)
        description = self._search_regex(
            r'<div[^>]+\bclass=["\']bottom[^>]+>\s*<p>[^<]*</p>\s*<p>([^<]+)',
            webpage, 'description', default=None)
        thumbnail = self._og_search_thumbnail(webpage, default=None)
        uploader = self._html_search_regex(
            (r'(?s)<li[^>]+class=["\']profile[^>]+>(.+?)</a>',
             r'class="user"[^>]*><img[^>]+>([^<]+)'),
            webpage, 'uploader', default=None)
        duration = parse_duration(self._search_regex(
            r'<div[^>]+\bclass=["\']right_side[^>]+>\s*<span>([^<]+)',
            webpage, 'duration', default=None))
        view_count = str_to_int(self._search_regex(
            r'([\d,.]+)\s+plays', webpage, 'view count', default=None))

        age_limit = self._rta_search(webpage)

        return merge_dicts({
            'id': video_id,
            'title': title or video_id,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'duration': duration,
            'view_count': view_count,
            'formats': formats,
            'age_limit': age_limit,
        }, info
        )


class SpankBangPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?spankbang\.com/(?P<id>[\da-z]+)/playlist/[^/]+'
    _TEST = {
        'url': 'https://spankbang.com/ug0k/playlist/big+ass+titties',
        'info_dict': {
            'id': 'ug0k',
            'title': 'Big Ass Titties',
        },
        'playlist_mincount': 50,
    }

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(
            url, playlist_id, headers={'Cookie': 'country=US; mobile=on'})

        entries = [self.url_result(
            'https://spankbang.com/%s/video' % video_id,
            ie=SpankBangIE.ie_key(), video_id=video_id)
            for video_id in orderedSet(re.findall(
                r'<a[^>]+\bhref=["\']/?([\da-z]+)/play/', webpage))]

        title = self._html_search_regex(
            r'<h1>([^<]+)\s+playlist</h1>', webpage, 'playlist title',
            fatal=False)

        return self.playlist_result(entries, playlist_id, title)
