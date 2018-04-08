from __future__ import unicode_literals

import yaml
import requests
import urllib
import sys
import curses

from rauth import OAuth1Service

class beatport(object):

    def __init__(self, keys_filename):
        self.keys_fname = keys_filename
        self.base_url = 'https://oauth-api.beatport.com/catalog/3/'

    def _setup_progress_bar(self, num_pages):
        curses.initscr()
        curses.curs_set(0)

        sentence = 'Page {} of {} complete.'.format(' '*len(str(num_pages)), str(num_pages))

        sys.stdout.write(sentence)
        sys.stdout.flush()

        sys.stdout.write('\b' * (len(sentence) - 5))

        return

    def _update_progress_bar(self, curr_page):
        pg = str(curr_page)

        sys.stdout.write(pg)
        sys.stdout.flush()
        sys.stdout.write('\b' * len(pg))

        return

    def _escape_progress_bar(self):
        sys.stdout.write('\n')
        curses.curs_set(1)
        curses.reset_shell_mode()
        return

    def _access(self, fname):
        with open(fname, 'r') as f:
            keys = yaml.load(f)

        login = keys['Beatport_Login']
        pswd = keys['Beatport_Pass']
        key = keys['Beatport_Key']
        secret = keys['Beatport_Secret']

        return(login, pswd, key, secret)

    def _container(self, key, secret):

        OAuth = OAuth1Service(name = 'beatport',
                                    consumer_key = key,
                                    consumer_secret = secret,
                                    request_token_url= 'https://oauth-api.beatport.com/identity/1/oauth/request-token',
                                    access_token_url='https://oauth-api.beatport.com/identity/1/oauth/access-token',
                                    authorize_url='https://oauth-api.beatport.com/identity/1/oauth/authorize',
                                    base_url='https://oauth-api.beatport.com/json/catalog')
        return(OAuth)

    def _req_token_secret(self, OAuth):

        req_token, req_token_secret = OAuth.get_request_token(method = 'POST',
                                                         data = {'oauth_callback': 'http://www.ritcheydnb.com'})

        return(req_token, req_token_secret)

    def _auth_url(self, OAuth, req_token):

        return(OAuth.get_authorize_url(req_token))

    def _fetch_access(self, OAuth, req_token, req_token_secret, login, pswd):
        values = {'oauth_token': req_token,
                  'username': login,
                  'password': pswd,
                  'submit': 'Login'}

        r = requests.post('https://oauth-api.beatport.com/identity/1/oauth/authorize-submit',
                          data = values)

        verifier = r.url.split('oauth_verifier=', 1)[1]

        tokens = OAuth.get_raw_access_token(req_token,
                                               req_token_secret,
                                               method = 'POST',
                                               data = {'oauth_verifier': verifier})
        token_string = tokens.content

        access_token = token_string[token_string.find('=')+1:token_string.find('&')]
        access_token_secret = token_string[token_string.find('t=')+2:token_string.rfind('&s')]

        return(access_token, access_token_secret)

    def initialize(self):
        '''
        Start API session
        '''

        login, pswd, key, secret = self._access(self.keys_fname)

        OAuth = self._container(key, secret)

        req_token, req_token_secret = self._req_token_secret(OAuth)

        auth_url = self._auth_url(OAuth, req_token)

        acc_token, acc_token_secret = self._fetch_access(OAuth,
                                                         req_token,
                                                         req_token_secret,
                                                         login,
                                                         pswd)

        self.session = OAuth.get_session((acc_token, acc_token_secret))
        print('Session created')
        return

    def artist_id(self, artist):
        '''
        Find Beatport artist ID from their name

        INPUT:
            artist - artist name, STR
        OUTPUT:
            artist_id - INT
        '''
        qry = self.session.get(base_url+'artists',
                               params = {'facets': 'artistName:' + artist}).json()

        if len(qry) == 0:
            return('Artist not found')
        elif len(qry) > 1:
            return('Multiple artists found')
        else:
            return(qry[0]['id'])

    def tracks_w_track_terms_artist_id(self, terms, artist_id):
        '''
        Search Beatport

        INPUT
            terms - track title to search, STR
            artist_id - Beatport artist ID, INT
        OUTPUT
            results - list of dictionaries with track data, LIST
        '''
        qry = self.session.get('https://oauth-api.beatport.com/catalog/3/search',
                                params = {'query': terms,
                                          'facets': 'genreId:1,artistId:' + str(artist_id),
                                          'perPage': 150}).json()

        pages = qry['metadata']['totalPages']

        results = []

        for i in xrange(pages):

            qry = self.session.get('https://oauth-api.beatport.com/catalog/3/search',
                                    params = {'query': terms,
                                              'facets': 'genreId:1,artistId:' + str(artist_id),
                                              'perPage': 150,
                                              'page': i + 1}).json()

            for q in qry['results']:

                if q['type'] == 'track':
                    results.append(q)

        return(results)

    def track_w_track_id(self, track_id):
        '''
        Find track by track ID

        INPUT:
            track_id - INT
        OUTPUT:
            trk_dict - track details DICT
        '''
        trk_dict = self.session \
                       .get(self.base_url + 'tracks',
                       params = {'id' : track_id}).json()['results']

        return(trk_dict)

    def track_url(self, track_id):
        '''
        Find Beatport track url
        '''
        trk_dict = self.track_w_track_id(track_id)

        base_url = 'http://www.beatport.com/track/'

        return(base_url
                + trk_dict[0]['slug']
                + '/'
                + str(trk_dict[0]['id']))

    def tracks_w_artist_id(self, artist_id):
        '''
        Find all tracks by an artist using ID

        INPUT:
            artist_id - INT
        OUTPUT:
            tracks - track name and track id, DICT
        '''
        trks = self.session \
                   .get(self.base_url+'tracks',
                       params = {'facets': 'artistId:' + str(artist_id),
                                 'perPage': 150}) \
                   .json()

        pages = trks['metadata']['totalPages']

        self._setup_progress_bar(pages)

        trk_dict = {}

        for i in xrange(pages):

            trks = self.session \
                       .get(self.base_url + 'tracks',
                            params = {'facets': 'artistId:' + str(artist_id),
                                      'perPage': 150,
                                      'page': i + 1}) \
                       .json()

            for trk in trks['results']:

                trk_dict[trk['name']] = trk['id']

            self._update_progress_bar(i + 1)

        self._escape_progress_bar()

        return(trk_dict)

    def tracks_w_dates(self, start, stop):
        '''
        Find all tracks released within a date range

        INPUT
            start - beginning date, STR
            stop - end date, STR
        OUTPUT
            track_ids - track data, DICT
            {track_id : (slug, bpm)}

        EXAMPLE
            beatport.tracks_w_dates('2015-01-01', '2015-12-31')
        '''

        trks = self.session \
                   .get(self.base_url+'tracks',
                        params = {'genreId': 1,
                                  'releaseDateStart': start,
                                  'releaseDateEnd': stop,
                                  'perPage': 150,
                                  'page': 1}) \
                    .json()

        pages = trks['metadata']['totalPages']

        soln = {}

        self._setup_progress_bar(pages)

        for i in xrange(pages):
            self._update_progress_bar(i + 1)

            trks = self.session \
                       .get(self.base_url+'tracks',
                            params = {'genreId': 1,
                                      'releaseDateStart': start,
                                      'releaseDateEnd': stop,
                                      'perPage': 150,
                                      'page': i + 1}) \
                        .json()

            for trk in trks['results']:
                soln[trk['id']] = trk

        self._escape_progress_bar()

        return(soln)

    def artists_w_genre_id(self, genre_id):
        '''
        Generate dictionary of artist name and id

        INPUT
            genre_id - Beatport genre id, INT
        OUTPUT
            artists - Dictionary of {artist name: artist id}, DICT
        '''
        artists = self.session \
                      .get(self.base_url+'artists',
                           params = {'facets': 'genreId:' + str(genre_id),
                                     'perPage': 150}) \
                      .json()

        pages = artists['metadata']['totalPages']

        self._setup_progress_bar(pages)

        artist_dict = {}

        for i in xrange(pages):
            artists = self.session \
                          .get(self.base_url + 'artists',
                               params = {'facets': 'genreId:' + str(genre_id),
                                         'perPage': 150,
                                         'page': i + 1}) \
                          .json()

            for art in artists['results']:

                artist_dict[art['name'].lower()] = art['id']

            self._update_progress_bar(i + 1)

        self._escape_progress_bar()

        return(artist_dict)

    def save_track_snippet(self, track_id, location):
        '''
        Download and save 2-minute track snippet from Beatport

        INPUT
            track_id - Beatport track ID, INT
            location - directory to save file, STR
        OUTPUT
            None

        EXAMPLE
            beatport.save_track_snippet(2828282, '/Users/person/samples/')
        '''
        trk = 'https://geo-samples.beatport.com/lofi/' \
               + str(track_id) \
               + '.LOFI.mp3'

        if location[-1] != '/':
            location += '/'

        fname = location \
                + str(track_id) \
                + '.mp3'

        urllib.urlretrieve(trk, fname)

        return(fname)

class sqlport(object):

    def __init__(self, name):
        self.user = name

    def launch(self):
        self.conn = pg2.connect('dbname=beatport user=' + self.user)
        self.cur = self.conn.cursor()
        return

    def shutdown(self):
        self.cur.close()
        self.conn.close()
        return

    def _setup_progress_bar(self, num_iters):
        '''
        '''
        curses.initscr()
        curses.curs_set(0)

        sentence = 'Iteration {} of {} complete.'.format(' '*len(str(num_iters)), str(num_iters))

        sys.stdout.write(sentence)
        sys.stdout.flush()

        sys.stdout.write('\b' * (len(sentence) - 10))

        return

    def _update_progress_bar(self, curr_iter):
        pg = str(curr_iter)

        sys.stdout.write(pg)
        sys.stdout.flush()
        sys.stdout.write('\b' * len(pg))

        return

    def _escape_progress_bar(self):
        sys.stdout.write('\n')
        curses.curs_set(1)
        curses.reset_shell_mode()
        return

    def build_artist_table(self, artists):
        '''
        Insert artist name and id into Postgres
        '''
        self.launch()

        self.cur.execute('DROP TABLE IF EXISTS bprt_artist')
        self.cur.execute('''CREATE TABLE bprt_artist (id INTEGER PRIMARY KEY,
                                                      name TEXT)''')
        self.conn.commit()

        self._setup_progress_bar(len(artists.keys()))

        i = 1
        for name, id in artists.iteritems():
            self._update_progress_bar(i)
            self.cur.execute('INSERT INTO bprt_artist (id, name) VALUES (%s, %s)', (id, name))
            i += 1

        self._escape_progress_bar()
        self.conn.commit()
        return
