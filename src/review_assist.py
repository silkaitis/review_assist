import yaml, sys, xmltodict, random

from time import sleep
from selenium import webdriver
from beatport_api import beatport

class release_review(object):

    def __init__(self, beatport, keys):
        self.url = 'https://www.beatport.com/account/login'
        self.user = keys['user']
        self.password = keys['password']
        self.bprt = beatport

    def launch(self):
        '''
        Launch Chrome webdriver
        '''
        self.driver = webdriver \
                        .Chrome('./chromedriver')

        self.driver.get(self.url)

        return

    def login(self):
        '''
        Login
        '''
        self.driver \
            .find_element_by_xpath("//input[@id='username']") \
            .send_keys(self.user)

        self.driver \
            .find_element_by_xpath("//input[@id='password']") \
            .send_keys(self.password)

        self.driver \
            .find_element_by_xpath("//button[@type='submit']") \
            .click()

        return

    def goto_track(self, trk_url):
        '''
        Go to track page
        '''
        self.driver \
            .get(trk_url)

        return

    def play_track(self, trk_id):
        '''
        Start playing track
        '''
        self.driver \
            .find_element_by_xpath("//button[@data-track=" + str(trk_id) + "]") \
            .click()

        return

    def add_track(self):
        self.driver \
            .find_element_by_xpath("//button[@class='add-to-default']") \
            .click()

        sleep(1)
        return

    def shutdown(self):
        '''
        Close driver
        '''
        self.driver.close()

        return

def track_url(trk_dict):
    base_url = 'http://www.beatport.com/track/'

    return(base_url
            + trk_dict['slug']
            + '/'
            + str(trk_dict['id']))

if __name__ == '__main__':
    '''
    Read log
    '''
    with open('data/reviewed.log', 'r') as f:
        reviewed = f.read().split(',')

    reviewed = set([int(val) for val in reviewed[:-1]])

    '''
    Collect current artists and labels
    '''
    with open('data/dnb.xml', 'r') as f:
        doc = xmltodict.parse(f.read())

    doc = doc['DJ_PLAYLISTS']['COLLECTION']['TRACK']

    labels = set()
    artists = set()

    skip_labels = set(['LW Recordings',
                       'Nothing But',
                       'Infidel Bassline Squad Records',
                       'Drumroom'])

    for d in doc:
        if d['@Genre'].find('Drum & Bass') != -1:
            if d['@Label'] not in skip_labels:
                labels.add(d['@Label'])
            artists.add(d['@Artist'])

    bprt = beatport('data/mykeys.yaml')
    bprt.initialize()

    trk_data = bprt.tracks_w_dates(sys.argv[1], sys.argv[2])

    with open('data/login.yaml', 'r') as f:
        keys = yaml.load(f)


    review = release_review(bprt, keys)

    review.launch()
    review.login()

    '''
    Select tracks to review
    '''
    to_review = set()
    for id in set(trk_data.keys()) - reviewed:
        trk = trk_data[id]

        if (trk['label']['name'] in labels):
            to_review.add(id)

        for artist in trk['artists']:
            if artist['name'] in artists:
                to_review.add(id)

        for sub_genre in trk['subGenres']:
            if sub_genre['slug'] == 'liquid':
                to_review.add(id)

    '''
    Randomly add a few tracks for variety
    '''
    sub_set = set(trk_data.keys()) - reviewed - to_review

    print('{} tracks to review\n'.format(len(to_review)))

    print('{} random tracks available\n'.format(len(sub_set)))

    num_to_sample = raw_input('Random tracks to add: ')

    for val in random.sample(sub_set, int(num_to_sample)):
        to_review.add(val)

    to_review = list(to_review)
    random.shuffle(to_review)

    for i, id in enumerate(to_review):
        print('{} of {}'.format(i + 1, len(to_review)))

        review.goto_track(track_url(trk_data[id]))

        review.play_track(id)

        with open('data/reviewed.log', 'a') as f:
            f.write(str(id) + ','.rstrip('\n'))

        val = raw_input('Add Track (y/[n]): ')

        if val == 'y':
            review.add_track()

        elif val == 'q':
            review.shutdown()

            break

    if val != 'q':
        review.shutdown()
