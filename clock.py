from apscheduler.schedulers.blocking import BlockingScheduler
import os

sched = BlockingScheduler()

@sched.scheduled_job('interval', hours=2)
def timed_job():
	os.system('genrebot.py')
    print('This job is run every two hours.')

sched.start()