import credentials
import time
import sqlite3
import traceback
import datetime
import nltk

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

    def __init__(self, subreddit):

        print('Logging in...')
        self.reddit = credentials.reddit
        self.db = Database(subreddit)
        print('Successfully logged in.')

        self.sub = subreddit

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
            print("AND IT'S INTERESTING", end="")

        if cache:
            print('Caching', end="")
            self.db.add(submission)

        print('\n')


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
        cache = cache and not self.db.in_database(submission) and self.is_interesting(submission)
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
