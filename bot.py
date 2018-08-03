import credentials
import sqlite3
import traceback
import datetime
import nltk
import os
import dill as pickle
from collections import defaultdict
import subprocess
import time as t
from praw.models import MoreComments
import re

# https://praw.readthedocs.io/en/latest/tutorials/reply_bot.html
WAIT = 10  # time to wait before restarting (after exception)

# Gender constants
MALE = ' ~MALE~ '
FEMALE = ' ~FEMALE~ '

# Define regex
male = re.compile('\s\[[\\\/\s0-9mM]*\]|\([\s0-9mM]*\)\s*')
female = re.compile('\s*\[[\\\/\s0-9fF]*\]|\([\s0-9fF]*\)\s*')
me = '(I|I\'ve|My|Me)'
partner = '(boyfriend|girlfriend|[bBgG][fF]|husband|wife|partner|fiance|spouse)'
generic_tag = re.compile('\[.*]\]')


def op_gender(submission):

    title = clean_title(submission)
    if re.search(re.compile(me + '\s*' + MALE), title):
        return MALE
    elif re.search(re.compile(me + '\s*' + FEMALE), title):
        return FEMALE
    else:
        return None


def say(submission):

    text = re.sub(generic_tag, '', str(submission.title))
    # text = re.sub(female, '', text)

    if op_gender(submission) == MALE:
        voice = 'Alex'
    else:
        voice = 'Victoria'

    subprocess.call(['say', '-v', voice, text])


def sub_vars(submission):
    import pprint
    pprint.pprint(vars(submission))


def clean_title(submission):
    text = re.sub(male, MALE, submission.title)
    text = re.sub(female, FEMALE, text)

    return text


class Database:
    
    def __init__(self, sub):
        db_file = sub + '.db'
        self.pickle_file = sub + '.pickle'
        self.sql = sqlite3.connect(db_file)
        self.cur = self.sql.cursor()
        self.cur.execute('CREATE TABLE IF NOT EXISTS '
                         'posts(id TEXT, subreddit TEXT, cached TEXT, title TEXT, selftext TEXT, url TEXT)')
        self.cur.execute('CREATE INDEX IF NOT EXISTS postindex on posts(id)')

        self.sub_data = self.load_pickle(self.pickle_file)

    def add(self, submission, time):
        id = submission.fullname
        subreddit = submission.subreddit.display_name.lower()
        title = submission.title
        text = submission.selftext
        url = submission.url

        # Save into db
        self.cur.execute('INSERT INTO posts VALUES(?, ?, ?, ?, ?, ?)',
                         [id, subreddit, time, title, text, url])
        self.sql.commit()

        # Save submission to pickle, to be able to get all info if needed
        self.save_into_pickle(submission)

    def get(self, id):
        return self.sub_data[id]

    def in_database(self, submission):
        id = submission.fullname
        if '_' not in id:
            id = 't3_' + id

        self.cur.execute('SELECT * FROM posts WHERE id == ?', [id])
        item = self.cur.fetchone()
        return item is not None

    def load_pickle(self, file):
        if os.path.isfile(file):
            return pickle.load(open(file, 'rb'))
        else:
            return {}

    def save_into_pickle(self, sub):
        self.sub_data[sub.fullname] = sub
        pickle.dump(self.sub_data, open(self.pickle_file, 'wb'))


class Bot:

    stat_pickle = './.stats'

    def __init__(self, subreddit):

        print('Logging in...')
        self.reddit = credentials.reddit
        self.db = Database(subreddit)
        print('Successfully logged in.')

        self.sub = subreddit

        self.stats = PostStats(Bot.stat_pickle)

    def do(self):
        print('Checking /r/' + self.sub)
        subreddit = self.reddit.subreddit(self.sub)
        submissions = subreddit.stream.submissions()
    
        for submission in submissions:
            self.process(submission)

    def is_interesting(self, submission):
        return True

    def process(self, submission, cache=True):

        time = datetime.datetime.now()
        self.print_contents(submission)

        if self.is_interesting(submission):
            print("AND IT'S INTERESTING", end=" ")
            if not self.db.in_database(submission):
                say(submission)
                if cache:
                    print('Caching', end="")
                    self.db.add(submission, time)
                    self.stats.update(time)


        print()
        self.stats.show()
        self.stats.save()
        print()

    @staticmethod
    def print_contents(submission, comments=False):
        print('----', datetime.datetime.now(), '----')
        print('Submission ID:', submission.fullname, 'Title:', clean_title(submission))
        print(submission.selftext.replace('\n', '\t'))
        print('Flair:', submission.link_flair_text, end=' ')
        gender = op_gender(submission)
        print('OP gender:', gender.strip() if gender else '~')

        if comments:
            for comment in submission.comments:
                if isinstance(comment, MoreComments):
                    continue  # Ignore nested comments
                print('\t', comment.body.replace('\n', '\t'))


class PostStats:

    def __init__(self, file):
        self.file = file
        self.stats = self.load()

    def load(self):
        if os.path.isfile(self.file):
            return pickle.load(open(self.file, 'rb'))
        else:
            return defaultdict(lambda: defaultdict(int))

    def update(self, time):
        self.stats[time.day][time.hour] += 1

    def show(self):
        now = datetime.datetime.now()
        hours = len(self.stats[now.day].keys())
        for l in range(3):
            for i in range(hours + 2):
                if i == 0 or i == hours + 1:
                    c = '|'
                elif l == 2:
                    c = '-'
                else:
                    c = ' '
                print(c, end='')
            print()

        print('{} total posts, {} posts collected today, {} this hour'.format(self.posts_total(), self.posts_this_day(), self.posts_this_hour()))

    def save(self):

        if len(self.stats) == 0:
            return

        pickle.dump(self.stats, open(self.file, 'wb'))

    def posts_total(self):
        sum = 0
        for day, daydict in self.stats.items():
            for hour, count in daydict.items():
                sum += count
        return sum

    def posts_this_day(self):
        now = datetime.datetime.now()
        return sum(count for (hour, count) in self.stats[now.day].items())

    def posts_this_hour(self):
        now = datetime.datetime.now()
        return self.stats[now.day][now.hour]


class BreakupBot(Bot):

    def is_interesting(self, submission):
        """
        Only interested in posts whose flair is [Breakups]
        """

        return submission.link_flair_text == 'Breakups'

    def process(self, submission, cache=True):
        super(BreakupBot, self).process(submission, cache)

        tokenized = nltk.word_tokenize(clean_title(submission))

        # print(tokenized)


if __name__ == '__main__':

    bot = BreakupBot('relationships')

    while True:
        try:
            bot.do()
        except Exception as e:
            traceback.print_exc()
        print('Exception occured. Running again in %d seconds\n' % WAIT)
        t.sleep(WAIT)
