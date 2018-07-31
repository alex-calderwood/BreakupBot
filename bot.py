import credentials
import time
import sqlite3
import traceback
import datetime

# https://praw.readthedocs.io/en/latest/tutorials/reply_bot.html
WAIT = 10
SUBREDDIT = 'relationships'


class Database:
    
    def __init__(self, file):
        self.sql = sqlite3.connect(file)
        self.cur = self.sql.cursor()
        self.cur.execute('CREATE TABLE IF NOT EXISTS posts(id TEXT, subreddit TEXT)')
        self.cur.execute('CREATE INDEX IF NOT EXISTS postindex on posts(id)')

    def add(self, submission):
        subreddit = submission.subreddit.display_name.lower()
        submission = submission.fullname

        self.cur.execute('INSERT INTO posts VALUES(?, ?)', [submission, subreddit])
        self.sql.commit()

    def in_database(self, submission):
        submission = submission.fullname
        if '_' not in submission:
            submission = 't3_' + submission

        self.cur.execute('SELECT * FROM posts WHERE id == ?', [submission])
        item = self.cur.fetchone()
        return item is not None


class Bot():

    def __init__(self):

        print('Logging in...')
        self.reddit = credentials.reddit
        self.db = Database('relationships.db')
        print('Successfully logged in.')

    def do(self):
        print('Checking /r/' + SUBREDDIT)
        subreddit = self.reddit.subreddit(SUBREDDIT)
        submissions = subreddit.stream.submissions()
    
        for submission in submissions:
            if self.db.in_database(submission):
                continue

            print(datetime.datetime.now(), 'NEW SUBMISSION')
            print('Title:', submission.title)
            print('\t', submission.selftext.replace('\n', ' '))
            print()

            self.db.add(submission)


if __name__ == '__main__':

    bot = Bot()

    while True:
        try:
            bot.do()
        except Exception as e:
            traceback.print_exc()
        print('Running again in %d seconds\n' % WAIT)
        time.sleep(WAIT)
