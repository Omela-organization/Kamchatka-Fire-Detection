import schedule

from src.fire_detection_module import fire_detection

schedule.every(6).day.do(fire_detection)
while True:
    schedule.run_pending()
