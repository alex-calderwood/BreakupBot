from bot import Bot, PostStats, Database
import datetime
from dateutil import rrule
import matplotlib.pyplot as plt


class Plotter:

    def __init__(self):
        # Initialize
        # style.use('seaborn-notebook	')
        fig, ax = plt.subplots()
        self.xdata, self.ydata = [], []
        stats = PostStats(Bot.stat_pickle)
        now = datetime.datetime.now()

        # get the iterator for each hour on record with the number of posts
        post_hours = stats.stats.items()

        # a list of each hour elapsed since the earliest hour in the collected stats
        each_hour = rrule.rrule(rrule.HOURLY, dtstart=self.earliest_hour(post_hours), until=now)

        for cur_time in each_hour:
            post_count = stats.stats[cur_time.day][cur_time.hour]
            self.xdata.append(cur_time)
            self.ydata.append(post_count)

        # setup plot
        plt.xticks(rotation=45)
        plt.style.use('bmh')

    def update(self):
        # Update the plot from the stats pickle
        try:
            stats = PostStats(Bot.stat_pickle)
            self.xdata.append(datetime.datetime.now())
            self.ydata.append(stats.posts_this_hour())
            plt.xlim(xmin=min(self.xdata), xmax=max(self.xdata))
            plt.ylim(ymin=min(self.ydata), ymax=max(self.ydata))
        except Exception:
            print('Could not update.')

    def run(self):
        # Continually plot the data
        while True:
            self.update()
            plt.plot(self.xdata, self.ydata, c='black')
            self.update()
            plt.pause(.5)

    @staticmethod
    def earliest_hour(post_hours):
        now = datetime.datetime.now()

        earliest_day, earliest_day_hours = min([(day, daydict) for (day, daydict) in post_hours])
        earliest_hour, earliest_hour_count = min([(hour, count) for (hour, count) in earliest_day_hours.items()])

        return datetime.datetime(year=now.year, month=now.month, day=earliest_day, hour=earliest_hour)

if __name__ == '__main__':
    Plotter().run()

