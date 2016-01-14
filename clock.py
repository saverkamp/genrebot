from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler()

@sched.scheduled_job('interval', hours=2)
def timed_job():
    print('This job is run every two hours.')

sched.start()