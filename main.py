import os
from moviepy.config import change_settings
from TTSGen import generate_tts_files
from videoManager import get_random_file, overlay_image_to_video, burn_subtitles_ffmpeg, trim_video_to_audio, set_audio_to_video
import whisper
import json
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import AudioFileClip, concatenate_audioclips
from datetime import timedelta
import time

"""
TODO:
Consider implementing Capcut TTS rather than Azure

Use ass file instead of srt

Steal many reddit stories from popular channels.

"""

# Load the Reddit stories from a JSON file
def load_reddit_stories(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        data = json.load(file)
        return data["reddit_stories"]

# Path configurations
change_settings({"IMAGEMAGICK_BINARY": r"C:/Program Files/ImageMagick-7.1.1-Q16-HDRI/magick.exe"})
output_directory = r"D:/TTVG/finalized_videos/"
ffmpeg_dir = r"D:/TTVG/temp_vids/"
image_dir = r"D:/TTVG/images/"
tts_dir = r"D:/TTVG/output_audio/"
srt_dir = r"D:/TTVG/srt_files/"
stories = load_reddit_stories('stories.json')

# Ensure output directories exist
os.makedirs(output_directory, exist_ok=True)
os.makedirs(tts_dir, exist_ok=True)
os.makedirs(srt_dir, exist_ok=True)


def main():
    iterator = 0
    video_times = []
    for story in stories:
        start= time.time()
        story_text=story["story"] + "Like, comment, and follow for more!"
        summary_text=story["summary"]
        gender=story["gender"]
        story_text=story_text.replace("\n","").replace("\*","").replace("\"","'")
        iterator += 1
        story_audio_file = os.path.join(tts_dir, f"story_tts_audio_{iterator}.mp3")
        whole_audio_file = os.path.join(tts_dir, f"whole_tts_audio_{iterator}.mp3")
        summary_tts_audio = os.path.join(tts_dir, f"image_tts_audio_{iterator}.mp3")
        
        print(f"Generating TTS for story & summary {iterator}")
        generate_tts_files(iterator, summary_text, story_text, gender)

        print(f"Generating whole audio...")
        generate_whole_audio(iterator, summary_tts_audio,story_audio_file)
        
        video_path = get_random_file(whole_audio_file)
        print(f"Selected background video")

        video_path = set_audio_to_video(video_path, whole_audio_file)
        
        srt_file = os.path.join(srt_dir, f"story_tts_audio_{iterator}.srt")
        print(f"Generating subtitles for story {iterator}")
        generate_subtitles(story_audio_file, summary_tts_audio)

        print(f"Trimming video to audio... {iterator}")
        temp_path = os.path.join(ffmpeg_dir, f"trimmed_selected_video_{iterator}.mp4")
        trim_video_to_audio(video_path, 0, AudioFileClip(whole_audio_file).duration, temp_path) # temp_path is output file

        print(f"Generating summary image for story {iterator}...")
        add_text_to_image(summary_text,iterator)

        print(f"Adding image to center of video for story {iterator}...")
        image_path=os.path.join(image_dir, f"generated_image{iterator}.png")
        video_path = overlay_image_to_video(temp_path, image_path, summary_tts_audio, whole_audio_file)

        # Optional: Burn subtitles into the final video using FFmpeg
        final_video = os.path.join(output_directory, f"final_video_{iterator}.mp4")
        print(f"Burning subtitles into the video for story {iterator}")
        burn_subtitles_ffmpeg(video_path, srt_file, final_video)

        print(f"Video generation complete for story {iterator}")
        print(f"Final video saved at: {final_video}")
        print("Deleting temporary files...")
        files=os.listdir(ffmpeg_dir)
        for file in files:
            path = os.path.join(ffmpeg_dir,file)
            if os.path.exists(path):
                os.remove(path)
        end = time.time()
        print(f"Time it took for {final_video}: {start-end}")
        video_times.append(((start-end),final_video))
    for t, video in  video_times:
        print(t,video)

def generate_whole_audio(id, summary_audio, story_audio):
    output_file=f"D:/TTVG/output_audio/whole_tts_audio_{id}.mp3"
    summary = AudioFileClip(summary_audio)
    story = AudioFileClip(story_audio)

    concatenated_audio = concatenate_audioclips([summary, story])

    concatenated_audio.write_audiofile(output_file, codec="mp3")

# Directory for saving the SRT file
output_srt_dir = r"D:/TTVG/srt_files/"

def convert_seconds_to_srt_format(seconds):
    """
    Convert a time in seconds to the hh:mm:ss,ms format required by .srt files.
    """
    delta = timedelta(seconds=seconds)
    hours, remainder = divmod(delta.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}.{milliseconds:03}"

def split_text_by_length(text, max_chars=18):
    """
    Split the text into chunks of a maximum number of characters per line.
    """
    words = text.split(' ')
    lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= max_chars:  # Add word if it fits
            if current_line:
                current_line += " " + word
            else:
                current_line = word
        else:
            lines.append(current_line)  # Add the current line and start a new one
            current_line = word  # Start a new line with the current word

    if current_line:  # Add any remaining words
        lines.append(current_line)

    return lines

def generate_subtitles(audio_file, summary_file):
    # Load the Whisper model (use the base model for now)
    model = whisper.load_model("base")
    
    # Transcribe the audio using Whisper
    result = model.transcribe(audio_file)
    
    # Ensure the output directory exists
    os.makedirs(output_srt_dir, exist_ok=True)

    # Calculate the duration of the image overlay or summary TTS
    duration = AudioFileClip(summary_file).duration

    # Define the SRT file name based on the audio file name
    srt_file_name = os.path.basename(audio_file).replace('.mp3', '.srt')
    output_srt_file = os.path.join(output_srt_dir, srt_file_name)

    # Write the result to an SRT file in the correct hh:mm:ss,ms format
    with open(output_srt_file, 'w', encoding='utf-8') as f:
        srt_index = 1
        for segment in result['segments']:
            start_time = segment['start'] + duration
            end_time = segment['end'] + duration
            original_duration = end_time - start_time
            text = segment['text']

            # Split text into lines of 18 characters max
            lines = split_text_by_length(text, max_chars=18)

            # Calculate duration for each line chunk
            chunk_duration = original_duration / len(lines)

            # Write each line as a separate subtitle block with proportional timing
            for i, line in enumerate(lines):
                chunk_start_time = start_time + (i * chunk_duration)
                chunk_end_time = chunk_start_time + chunk_duration

                # Convert start and end times to the required SRT format
                start_srt = convert_seconds_to_srt_format(chunk_start_time)
                end_srt = convert_seconds_to_srt_format(chunk_end_time)

                # Write the subtitle block in the standard SRT format
                f.write(f"{srt_index}\n{start_srt} --> {end_srt}\n{line.strip()}\n\n")
                srt_index += 1

    print(f"Subtitles saved at: {output_srt_file}")




def add_text_to_image(text, iterator, font_size=35, text_color='black', max_width=860, image_size=(1080, 1920)):
    image_path = r"D:/TTVG/images/base_image.png"
    output_path = f"D:/TTVG/images/generated_image{iterator}.png"
    font_path = "C:/Users/isyro/Downloads/ArchivoBlack-Regular.ttf"

    #927 x 327
    position = (110, 925)  # Adjust as needed

    #char a is 24 pixels

    # Open the base image
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    # Function to wrap text to fit within the specified width
    def wrap_text(text, font, max_width):
        lines = []
        words = text.split(' ')
        line = ''
        for word in words:
            test_line = f"{line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)  # Get bounding box of the text
            width = bbox[2] - bbox[0]
            if width <= max_width:
                line = test_line
            else:
                lines.append(line)
                line = word
        lines.append(line)  # Add the last line
        return lines

    # Function to calculate total height of the text block
    def calculate_text_height(lines, font):
        total_height = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_height = bbox[3] - bbox[1] + 6  # Add some padding between lines
            total_height += line_height
        return total_height

    # Start with an initial font size and keep reducing it until the text fits the image height
    while True:
        font = ImageFont.truetype(font_path, font_size)
        lines = wrap_text(text, font, max_width)

        # Calculate the total height of the text block
        text_height = calculate_text_height(lines, font)

        if text_height <= image_size[1] - position[1]:  # Check if text fits within the image height
            break
        else:
            font_size -= 1  # Reduce font size if text doesn't fit
            if font_size < 10:  # Ensure a minimum font size
                print("Text too large to fit in the image!")
                break

    # Draw each line on the image
    y_offset = 0
    for line in lines:
        draw.text((position[0], position[1] + y_offset), line, font=font, fill=text_color)
        bbox = draw.textbbox((0, 0), line, font=font)
        line_height = bbox[3] - bbox[1] + 6  # Adjust padding
        y_offset += line_height  # Move to the next line vertically

    # Save the modified image
    img.save(output_path)


if __name__ == "__main__":
    main()
