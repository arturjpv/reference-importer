from __future__ import annotations
import re
import shutil
import subprocess
import platform
from pathlib import Path

TIMECODE_REGEX = r"Duration: (\d{2}:\d{2}:\d{2}.\d)"
DIMENSIONS_SIZE_REGEX = r"Video.*[ ,](\d+)x(\d+)(,| \[)"
DIMENSIONS_SAR_REGEX = r"Video.*SAR (\d+):(\d+)"
DIMENSIONS_DAR_REGEX = r"Video.*DAR (\d+):(\d+)"
ROTATION_90_REGEX = r"displaymatrix.*90.*degrees"

class FfmpegError(Exception):
    ...

class MissingFfmpeg(FfmpegError):
    ...

class Dimensions:
    w: int
    h: int
    sar_w: int
    sar_h: int
    dar_w: int
    dar_h: int

class ImageSequencer:
    def __init__(
        self,
        video_file: str = "",
        output_name: str = "",
        padding: str = "%03d",
        output_frame_rate: int = 24,
    ) -> None:
        self.output_frame_rate = output_frame_rate
        self.video_file = video_file
        self.output_name = output_name
        self.padding = padding
        self.trim_start = 0
        self.trim_end = 0
        self.ffmpeg_path = self.get_ffmpeg_path()

    @classmethod
    def get_ffmpeg_path(cls) -> Path:
        """Resolves the path to ffmpeg.

        The script first attempts to use the ffmpeg available in the bin folder,
        otherwise it fallbacks to the first match of ffmpeg avaiable in Path.

        Raises:
            MissingFfmpeg: If no ffmpeg binaries are available.

        """
        _ffmpeg_binary = f"ffmpeg{'.exe' if platform.system() == 'Windows' else ''}"
        ffmpeg_executable = Path(__file__).parent.parent.resolve() / "bin" / _ffmpeg_binary 
        if not ffmpeg_executable.exists():
            ffmpeg_executable = shutil.which("ffmpeg")

        if not ffmpeg_executable:
            raise MissingFfmpeg()
        return Path(ffmpeg_executable)

    def get_duration(self, video_file: str) -> str:
        """Gets the duration of the video from the output of ffmpeg -i.

        Args:
            video_file: Video file.

        Raises:
            FfmpegError: If ffmpeg errors out and does not yield an output.
            ValueError: If there is no match for the duration in ffmpeg's output.

        Returns:
            Duration of the video in timecode.
        """
        command = f'"{self.ffmpeg_path}" -i "{video_file}"'
        try:
            output = str(
                subprocess.run(
                    command,
                    shell=True,
                    stderr=subprocess.STDOUT,
                    stdout=subprocess.PIPE,
                    check=False,
                ),
            )

        except subprocess.CalledProcessError as e:
            _except_msg: str = "Unable to get ffmpeg output"
            raise FfmpegError(_except_msg) from e

        # re.search searches across the whole string (multiline output).
        match: re.Match | None = re.search(TIMECODE_REGEX, output)

        if not match:
            _except_msg: str = f"Unable to find Duration for video {video_file}"
            raise ValueError(_except_msg)

        # the timecode is the first group of the match.
        duration: str = str(match.groups(0)[0])
        return duration

    def get_dimensions(self, video_file: str) -> Dimensions:
        """Gets the dimensions of the video from the output of ffmpeg -i.

        Args:
            video_file: Video file.

        Raises:
            FfmpegError: If ffmpeg errors out and does not yield an output.
            ValueError: If there is no match for the dimensions in ffmpeg's output.

        Returns:
            Dimensions of the video.
        """
        command = f'"{self.ffmpeg_path}" -i "{video_file}"'
        try:
            output = str(
                subprocess.run(
                    command,
                    shell=True,
                    stderr=subprocess.STDOUT,
                    stdout=subprocess.PIPE,
                    check=False,
                ),
            )

        except subprocess.CalledProcessError as e:
            _except_msg: str = "Unable to get ffmpeg output"
            raise FfmpegError(_except_msg) from e

        # re.search searches across the whole string (multiline output).
        match: re.Match | None = re.search(DIMENSIONS_SIZE_REGEX, output)

        if not match:
            _except_msg: str = f"Unable to find Dimensions for video {video_file}"
            raise ValueError(_except_msg)

        dimensions = Dimensions()
        dimensions.w = int(match.groups(0)[0])
        dimensions.h = int(match.groups(0)[1])

        match: re.Match | None = re.search(DIMENSIONS_SAR_REGEX, output)
        dimensions.sar_w = int(match.groups(0)[0]) if match else 1
        dimensions.sar_h = int(match.groups(0)[1]) if match else 1

        match: re.Match | None = re.search(DIMENSIONS_DAR_REGEX, output)
        dimensions.dar_w = int(match.groups(0)[0]) if match else 1
        dimensions.dar_h = int(match.groups(0)[1]) if match else 1

        # Swap w and h if we find rotation information
        match: re.Match | None = re.search(ROTATION_90_REGEX, output)
        if match:
            dimensions.w, dimensions.h = dimensions.h, dimensions.w

        return dimensions

    def create_sequence(
        self,
        input_file: str,
        frame_rate: int,
        start_trim: str,
        end_trim: str,
        output_file: str,
    ):
        dimensions = self.get_dimensions(input_file)
        scale_x = dimensions.w
        scale_y = round(dimensions.h * (float(dimensions.sar_h) / float(dimensions.sar_w)))
        command = (
            f'"{self.ffmpeg_path}" -i "{input_file}" -r {frame_rate}'
            f" -vf scale={scale_x}:{scale_y} -q:v 3 -ss {start_trim} -to {end_trim} "
            f'"{output_file}"'
        )
        try:
            subprocess.run(command, shell=True, check=False)
        except subprocess.CalledProcessError as e:
            raise FfmpegError from e


if __name__ == "__main__":
    pass
