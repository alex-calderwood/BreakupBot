import credentials
import time
import sqlite3
import traceback
import datetime
import nltk
import os
import dill as pickle
from collections import defaultdict

# https://praw.readthedocs.io/en/latest/tutorials/reply_bot.html
WAIT = 10  # time to wait before restarting (after exception)


class Database:
    
    def __init__(self, sub):
        filename = sub + '.db'
        self.sql = sqlite3.connect(filename)
        self.cur = self.sql.cursor()
        self.cur.execute('CREATE TABLE IF NOT EXISTS posts(id TEXT, subreddit TEXT, title TEXT, selftext TEXT)')
        self.cur.execute('CREATE INDEX IF NOT EXISTS postindex on posts(id)')

    def add(self, submission):
        id = submission.fullname
        subreddit = submission.subreddit.display_name.lower()
        title = submission.title
        text = submission.selftext

        self.cur.execute('INSERT INTO posts VALUES(?, ?, ?, ?)', [id, subreddit, title, text])
        self.sql.commit()

    def in_database(self, submission):
        id = submission.fullname
        if '_' not in id:
            id = 't3_' + id

        self.cur.execute('SELECT * FROM posts WHERE id == ?', [id])
        item = self.cur.fetchone()
        return item is not None


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

        print(time, 'NEW SUBMISSION')
        print('Title:', submission.title)
        print('\t', submission.selftext.replace('\n', ' '))
        if self.is_interesting(submission):
            print("AND IT'S INTERESTING", end=" ")

        if cache:
            print('Caching', end="")
            if not self.db.in_database(submission):
                self.db.add(submission)
                self.stats.update()

        print()
        self.stats.show()
        self.stats.save()
        print()


class PostStats:

    def __init__(self, file):
        self.file = file
        self.stats = self.load()

    def load(self):
        if os.path.isfile(self.file):
            return pickle.load(open(self.file, 'rb'))
        else:
            return defaultdict(lambda: defaultdict(int))

    def update(self):
        now = datetime.datetime.now()
        self.stats[now.day][now.hour] += 1

    def show(self):
        # now = datetime.datetime.now()
        # hours = len(self.stats[now.day].keys())
        # for l in range(3):
        #     for i in range(hours + 2):
        #         if i == 0 or i == hours + 1:
        #             c = '|'
        #         elif l == 2:
        #             c = '-'
        #         else:
        #             c = ' '
        #         print(c, end='')
        #     print()

        print('{} posts collected today, {} this hour'.format(self.posts_this_day(), self.posts_this_hour()))

    def save(self):

        if len(self.stats) == 0:
            return

        pickle.dump(self.stats, open(self.file, 'wb'))

    def posts_this_day(self):
        now = datetime.datetime.now()
        return sum(count for (hour, count) in self.stats[now.day].items())

    def posts_this_hour(self):
        now = datetime.datetime.now()
        return self.stats[now.day][now.hour]


class BreakupBot(Bot):

    interesting = [
        'breakup',
        'break',
        'end',
        'over'
    ]

    # def is_interesting(self, submission):
    #     return True in [word in submission.selftext.lower() for word in self.interesting]

    def process(self, submission, cache=True):
        cache = cache and self.is_interesting(submission)
        super(BreakupBot, self).process(submission, cache)

        tokenized = nltk.word_tokenize(submission.selftext)


if __name__ == '__main__':

    bot = BreakupBot('relationships')

    while True:
        try:
            bot.do()
        except Exception as e:
            traceback.print_exc()
        print('Running again in %d seconds\n' % WAIT)
        time.sleep(WAIT)
