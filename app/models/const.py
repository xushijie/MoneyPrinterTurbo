PUNCTUATIONS = [
    "?", ",", ".", "、", ";", ":", "!", "…",
    "？", "，", "。", "、", "；", "：", "！", "...",
]

TASK_STATE_FAILED = -1
TASK_COMPLETE=0    # 上传到 oss 完成
TASK_QUEUING=1    # 队列中
TASK_STATE_PROCESSING = 2
TASK_STATE_COMPLETE = 3   #视频生成完成

FILE_TYPE_VIDEOS = ['mp4', 'mov', 'mkv', 'webm']
FILE_TYPE_IMAGES = ['jpg', 'jpeg', 'png', 'bmp']

REDIS_TTL = 3600*2
