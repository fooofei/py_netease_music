# coding=utf-8


import requests
import os
import sys
import json

curpath = os.path.dirname(os.path.realpath(__file__))


class NeteaseCrypt(object):
    @staticmethod
    def encrypt_request_param(text):
        import json
        import binascii
        nonce = '0CoJUm6Qyw8W8jud'

        text = json.dumps(text)
        secret_key = binascii.hexlify(os.urandom(16))[:16]
        encrypt_text = NeteaseCrypt._aes_encrypt(NeteaseCrypt._aes_encrypt(text, nonce), secret_key)
        encrypt_sec_key = NeteaseCrypt._make_rsa_sec_key(secret_key)
        return {u'params': encrypt_text, u'encSecKey': encrypt_sec_key}

    @staticmethod
    def _aes_encrypt(text, secret_key):
        from Crypto.Cipher import AES
        import base64
        pad = 16 - len(text) % 16
        text = text + chr(pad) * pad
        encryptor = AES.new(secret_key, 2, '0102030405060708')
        ciphertext = encryptor.encrypt(text)
        ciphertext = base64.b64encode(ciphertext).decode('utf-8')
        return ciphertext

    @staticmethod
    def _make_rsa_sec_key(text):
        import binascii
        modulus = ('00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7'
                   'b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280'
                   '104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932'
                   '575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b'
                   '3ece0462db0a22b8e7')

        pub_key = '010001'
        text = text[::-1]
        rs = pow(int(binascii.hexlify(text), 16), int(pub_key, 16), int(modulus, 16))
        return format(rs, 'x').zfill(256)


def _get_chrome_cookies_files():
    '''
    使用前，先在 Chrome 中网页登陆网易云音乐
    browsercookie 中预设的 cookies 路径老了，新版的 chrome cookies 路径不是那个
    在这个函数里更新
    '''
    import glob
    fullpath_chrome_cookies = os.path.join(os.getenv('APPDATA', ''),
                                           r'..\Local\Google\Chrome\User Data\Profile 1\Cookies')
    for e in glob.glob(fullpath_chrome_cookies):
        yield e


def _get_chrome_cookies():
    import browsercookie
    from itertools import chain

    a = browsercookie.Chrome()
    files_old = a.find_cookie_files()
    files = chain(files_old, _get_chrome_cookies_files())

    return browsercookie.chrome(files)


def _cookies_curpath(cookie_jar_to_save=None):
    '''
    if is None cookie_jar_to_save, try to read _chrome_cache_cookies.txt
    if cookie_jar_to_save , save cookies to _chrome_cache_cookies.txt
    '''
    import pickle
    from requests.cookies import RequestsCookieJar

    fullpath = os.path.join(curpath, u'_chrome_cache_cookies.txt')

    if cookie_jar_to_save:
        if os.path.exists(fullpath):
            os.remove(fullpath)
        a = RequestsCookieJar()
        a.update(cookie_jar_to_save)
        with open(fullpath, 'wb') as fw:
            pickle.dump(a
                        , fw
                        )
        return cookie_jar_to_save

    if not os.path.exists(fullpath):
        return None

    with open(fullpath, 'rb') as fr:
        pc = pickle.load(fr)
        return pc


class NeteaseSession(requests.Session):
    def __init__(self):
        super(NeteaseSession, self).__init__()
        extra_headers = {
            u'Host': u'music.163.com',
            u'Referer': u'http://music.163.com/',
            u'User-Agent': u'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
        }
        self.headers.update(extra_headers)


def tick_func(name):
    sys.stdout.write(name + u' -> ')


from collections import namedtuple


# a Song(song_id,song_name,song_authors)
# cannot use field 'id', it's a keyword
# (str,str,list)
class NeteaseTrack(namedtuple('NeteaseTrack', ['track_id', 'track_name', 'track_ar'])):
    __slots__ = ()

    def format(self):
        v = self.format_track_ar
        return (u'NeteaseTrack(track_id={}, track_name={}, track_ar=[{}])').format(
            self.track_id,
            self.track_name,
            v
        )

    @property
    def format_track_ar(self):
        return u'/'.join(self.track_ar) if self.track_ar else u''

    @staticmethod
    def _from(server_back_track):
        ars = []
        for ar in server_back_track[u'ar']:
            ars.append(ar[u'name'])  # also have a id
        a = NeteaseTrack._make([
            server_back_track[u'id']
            , server_back_track[u'name']
            , ars
        ])
        return a


def sorted_tracks_by_ar(tracks):
    from operator import attrgetter
    tracks.sort(key=attrgetter('format_track_ar', 'track_name'),
                reverse=True)  # 要反序 因为插入的时候是反的
    return tracks


def sorted_tracks_by_name(tracks):
    from operator import attrgetter
    tracks.sort(key=attrgetter('track_name', 'format_track_ar'),
                reverse=True)
    return tracks


class NeteasePlaylist(namedtuple('NeteasePlaylist', ['pl_id', 'pl_name', 'pl_track_count',
                                                     'pl_tracks', 'pl_update_time',
                                                     'pl_track_update_time'])):
    __slots__ = ()

    def format(self):
        from io_in_out import io_from_timestamp

        tracks = u','.join(self.pl_tracks) if self.pl_tracks else u''
        func_time = lambda e: e.strftime(u'%Y/%m/%d %H:%M:%S')

        return (u'NeteasePlaylist(id={}, name={}, track_count={},'
                u' tracks={}, update_time={}, track_update_time={})'.format(
            self.pl_id,
            self.pl_name,
            self.pl_track_count,
            tracks,
            func_time(io_from_timestamp(self.pl_update_time)),
            func_time(io_from_timestamp(self.pl_track_update_time)),
        ))

    @staticmethod
    def _from(server_back_playlist):
        v = server_back_playlist
        return NeteasePlaylist._make(
            [v.get(u'id'),
             v.get(u'name'),
             v.get(u'trackCount'),
             v.get(u'tracks'),
             v.get(u'updateTime'),
             v.get(u'trackUpdateTime')
             ])


class NeteaseJson(dict):
    def __init__(self, r):
        super(NeteaseJson, self).__init__(json.loads(r, encoding='utf-8'))

    @property
    def code(self):
        return self.get(u'code', -1)

    @property
    def ok(self):
        return self.code == 200


class NeteaseMusic(object):
    '''
    通过 wireshark 抓包 网易云 Windows 客户端 发现 歌单内歌曲排序及歌单排序用的是 TCP TLSv1.2 协议 不是 HTTP
    抓包过程 先用 Windows 命令 netstat -b 找到网易云的挂载 ip ，对每一个 ip 去 wireshark 过滤 ip.dst == 59.111.160.195
        接着操作 网易云 Windows 客户端 查看 Wireshark 结果列表有没有刷新
    '''
    url_base = u'http://music.163.com/weapi'

    def __init__(self):
        self._session = requests.Session()

        c = _cookies_curpath(None)
        cookie_jar = c if c else _get_chrome_cookies()
        if not c:
            _cookies_curpath(cookie_jar)

        csrf = self._find_csrf_in_cookie_jar(cookie_jar)
        if not csrf:
            raise ValueError('must have csrf(login can not have)')
        self._csrf_token = csrf
        self._cookies = cookie_jar

    @staticmethod
    def _find_csrf_in_cookie_jar(cookie_jar):

        f = lambda c: -1 != c.domain.find(u'music.163.com') and c.name.endswith(u'csrf')
        c = filter(f, cookie_jar)
        if c:
            return c[0].value
        return None

    def _post(self, path, params, enc_params):
        url = self.url_base + path
        a = NeteaseCrypt.encrypt_request_param(enc_params)
        params.update({u'csrf_token': self._csrf_token})
        res = self._session.post(url, params=params, data=a
                                 , cookies=self._cookies
                                 )
        return res

    def _netease_try_api_framework(self, func_to_try, *args, **kwargs):
        '''
        20170621 受版权保护的音乐 无法播放 无法添加收藏 比如 http://music.163.com/#/song?id=390657
        这样的音乐无法被添加到歌单 返回错误 code=401
        :return:
        '''
        import time
        from io_in_out import io_stderr_print

        # 每次操作 休眠 2s 网易云的 API 限制严重 ( 1s 不够
        # important, use this no more timeout
        time.sleep(2)

        for loop in range(1000):
            try:
                a = func_to_try(*args, **kwargs)
            except requests.exceptions.RequestException as er:
                io_stderr_print(u'exception:{}'.format(er))
                continue
            # 502 已经存在
            # 400 失败
            # 401 无法操作，原因可能是受版权保护
            if a and (a.ok or a.code == 502 or a.code == 401):
                return a
            if a and a.code == 400:
                io_stderr_print(u'错误是 {}'.format(json.dumps(a, ensure_ascii=False)))
                return None

            # code:405 操作太频繁
            #
            if (a and a.code == 405) or (loop % 10 == 0):
                # 标准休眠时间是 80s
                io_stderr_print(u'重试 {} 次, 遇到错误，休眠 40s , 错误是 {}'.format(loop, json.dumps(a, ensure_ascii=False)))
                time.sleep(40)
        return None

    def _user_playlists(self, uid):
        # tick_func(self.my_playlist.__name__)

        enc_params = {u'offset': u'0',
                      u'uid': uid,
                      u'limit': 3000,
                      # u'id':u'', # not use
                      }

        res = self._post(path=u'/user/playlist'
                         , params={}
                         , enc_params=enc_params)

        if (res.status_code == 200
            and res.content):
            back = NeteaseJson(res.content)
            return back
        return None

    def try_user_playlists(self, uid):

        back = self._netease_try_api_framework(self._user_playlists, uid)
        if back and back.ok:
            assert (back.get(u'more', True) == False)
            playlists = back.get(u'playlist')
            r = []
            for pl in playlists:
                a = NeteasePlaylist._from(pl)
                r.append(a)
            return r
        return None

    def _playlist_detail(self, playlist_id):
        # tick_func(self._playlist_detail.__name__)

        p = {u'id': playlist_id,
             u'offset': 0,
             u'total': True,
             u'limit': 1000,
             u'n': 1000}

        res = self._post(path=u'/v3/playlist/detail'
                         , params={}
                         , enc_params=p)

        if (res.status_code == 200
            and res.content):
            back = NeteaseJson(res.content)
            return back
        return None

    def try_playlist_detail(self, playlist_id):
        back = self._netease_try_api_framework(
            self._playlist_detail,
            playlist_id
        )
        if back and back.ok:
            tracks = back.get(u'playlist').get(u'tracks')
            r = []
            for track in tracks:
                a = NeteaseTrack._from(track)
                r.append(a)
            return r
        return None

    def _manipulate_tracks(self, op, playlist_id, song_id):
        '''
        第二次添加同一个 song ,返回 code=502

        这个 song id=5043818 有非常大的几率失败

        '''
        # tick_func(self._manipulate_tracks.__name__)

        p = {
            u'op': op,
            u'pid': playlist_id,
            u'trackIds': json.dumps([song_id]),
            u'tracks': song_id,
        }

        res = self._post(path=u'/playlist/manipulate/tracks'
                         , params={}
                         , enc_params=p)

        if res.status_code == 200 and res.content:
            return NeteaseJson(res.content)
        return None

    def try_manipulate_tracks(self, op, playlist_id, song_id):

        a = self._netease_try_api_framework(self._manipulate_tracks,
                                            op, playlist_id, song_id)

        # 添加已经存在的音乐 返回 code=502， 这里应该返回 a 实例，复合预期
        if a and (a.ok or a.code == 502):
            return a
        return None

    def _create_playlist(self, name):
        '''
        即使同名也能创建成功  一定能创建成功
        如果遇到无效名字，比如 1989.6.4 那么会有默认名字代替
        '''
        # tick_func(self._create_playlist.__name__)

        p = {u'name': name}
        res = self._post(path=u'/playlist/create'
                         , params={}
                         , enc_params=p)

        if res.status_code == 200 and res.content:
            a = NeteaseJson(res.content)
            return a
        return None

    def try_create_playlist(self, name):

        a = self._netease_try_api_framework(self._create_playlist, name)
        if a and a.ok:
            return NeteasePlaylist._from(
                a.get(u'playlist')
            )
        return None

    def _delete_playlist(self, playlist_id):
        '''
        json such as :
            '{"code":200,"id":745231153}'

        多次删除同一个 playlist_id ，都一直删除成功
        查看自己歌单列表没有这个歌单 但是通过拼凑 url 是可以看到这个歌单的
        '''
        # tick_func(self._delete_playlist.__name__)
        p = {u'pid': playlist_id}
        res = self._post(path=u'/playlist/delete'
                         , params={}
                         , enc_params=p)

        if res.status_code == 200 and res.content:
            return NeteaseJson(res.content)
        return None

    def try_delete_playlist(self, playlist_id):

        a = self._netease_try_api_framework(
            self._delete_playlist,
            playlist_id
        )
        if a and a.ok:
            return a
        return None


def unit_find_csrf():
    a = _get_chrome_cookies()
    b = NeteaseMusic._find_csrf_in_cookie_jar(a)
    assert (b is not None)


def result_show(r):
    from io_in_out import io_print
    print ('')
    for i, e in enumerate(r):
        v = e.format()
        io_print(u'\t<{}> {}'.format(i + 1, v))


class PlaylistWrapper(NeteaseMusic):
    '''
    all methods return True/False  None/object_instance
    '''

    def _sorted_tracks(self, method_sort, pl_id):
        '''
        sort tracks(songs) in pl_id playlist
        '''
        tracks = self.try_playlist_detail(pl_id)
        if tracks is None: return False
        if tracks:
            backup = self.try_create_playlist(u'python_backup')
            if backup is None: return False
            tracks = method_sort(tracks)
            tracks_success = []
            for track in tracks:
                b = self.try_manipulate_tracks(u'add', backup.pl_id, track.track_id)
                if b is not None:  tracks_success.append(track)
                else : print('fail manipulate track, track_id={0} play_list={1}'
                             .format(track.track_id, backup.pl_id))

            # 还好这里没用 clear()，因为不能直接 clear()，可能存在转移失败的音乐，
            # 失败的音乐就继续存在原歌单，不要移动
            tracks = tracks_success
            for track in tracks:
                b = self.try_manipulate_tracks(u'del', pl_id, track.track_id)
                if not b: return False

            for track in tracks:
                b = self.try_manipulate_tracks(u'add', pl_id, track.track_id)
                if not b: return False
            self.drop(backup.pl_id)
        return True

    def sorted_by_tracks_ar(self, pl_id):
        '''
        sort first by songs artists, second by songs name
        '''
        return self._sorted_tracks(sorted_tracks_by_ar, pl_id)

    def sorted_by_tracks_name(self, pl_id):
        '''
        sort first by songs name, second by songs artists
        '''
        return self._sorted_tracks(sorted_tracks_by_name, pl_id)

    def append(self, pl_id_src, pl_id_dst):
        '''
        append all tracks in pl_id_src to pl_id_dst
        '''
        tracks = self.try_playlist_detail(pl_id_src)
        if tracks is None: return False
        return self.append_tracks(tracks, pl_id_dst)

    def append_tracks(self, tracks, pl_id_dst):
        tracks = sorted_tracks_by_ar(tracks)
        for track in tracks:
            b = self.try_manipulate_tracks(u'add', pl_id_dst, track.track_id)
            if not b: return False
        return True

    def copy(self, pl_id_src, pl_id_dst):
        '''
        make the pl_id_dst same with pl_id_src

        1 clear the dst
        2 copy the src to dst
        '''
        b = self.clear(pl_id_dst)
        if not b: return False
        return self.append(pl_id_src, pl_id_dst)

    def clear(self, pl_id):
        '''
        drop all tracks in pl_id playlist, and save the playlist name
        '''
        tracks = self.try_playlist_detail(pl_id)
        if tracks is None: return False
        if tracks:
            for track in tracks:
                b = self.try_manipulate_tracks(u'del', pl_id, track.track_id)
                if not b: return False
        return True

    def drop(self, pl_id):
        '''
        drop the playlist
        '''
        a = self.try_delete_playlist(pl_id)
        if a is None: return False
        return a.ok

    def classify_tracks(self, uid, tracks):
        '''
        push tracks to playlist named with track_ar
        '''

        def _rebuild(_uid):
            pls = self.try_user_playlists(_uid)
            ss = {e.pl_name: e for e in pls}
            return ss

        default_pl_id = u'745614822'

        ss = _rebuild(uid)

        for track in tracks:

            v = ss.get(track.format_track_ar, None)

            if not v:
                self.try_create_playlist(track.format_track_ar)
                ss = _rebuild(uid)
                v = ss.get(track.format_track_ar, None)
                # named fail, some name cannot be playlist_name
                if not v:
                    self.try_manipulate_tracks(u'add', default_pl_id, track.track_id)

            if v:
                self.try_manipulate_tracks(u'add',
                                           v.pl_id,
                                           track.track_id
                                           )

    def create_zero_width_name_playlist(self):
        '''
        create playlist with no name, just like in http://music.163.com/#/playlist?id=748829802
        '''
        n = u'&#8205;'  # or  u'&zwj;'
        return self.try_create_playlist(n)


def entry():
    from io_in_out import io_print

    ins = PlaylistWrapper()


if __name__ == '__main__':
    entry()
