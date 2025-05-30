

from loguru import logger

from app.models.schema import VideoParams
from app.utils import utils
from app.services.chanaVideo import video


class Chana_AI_Video_Process:     
    n_threads = 4
    async def __call__(self, task_id: str, path:str, download_videos:list[str], audio_file:str, max_clip_duration:int, subtitle_path:str, params: VideoParams) -> str:
        combined_video_path = "/".join([path, "combined-video.mp4"])
        logger.info(f"\n\n## combining video: => {combined_video_path}")
        video.combine_videos(combined_video_path=combined_video_path,
                             video_paths=download_videos,
                             audio_file=audio_file,
                             video_aspect=params.video_aspect,
                             video_concat_mode=params.video_concat_mode,
                             max_clip_duration=max_clip_duration,
                             threads=self.n_threads)

        final_video_path = "/".join([path, "final-video.mp4"])
        if not audio_file:
            return combined_video_path
        
        logger.info(f"\n\n## generating video: => {final_video_path}")
        # Put everything together
        return video.generate_video(video_path=combined_video_path,
                             audio_path=audio_file,
                             subtitle_path=subtitle_path,
                             output_file=final_video_path,
                             params=params,
                             )
