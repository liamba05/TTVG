from moviepy.editor import AudioFileClip
import random
import os
import subprocess
import pysrt

ffmpeg_dir=r"D:/TTVG/temp_vids/"

def escape_text(text):
    return text.replace("'", "’")

def split_text(text, max_chars_per_line=18):
    # Split the text into words
    words = text.split(' ')
    
    # Initialize variables for building lines
    lines = []
    current_line = []
    
    # Loop through each word and build lines that don't exceed max_chars_per_line
    for word in words:
        # Check if adding the word would exceed the max width
        if len(' '.join(current_line + [word])) > max_chars_per_line:
            # If so, join the current line and start a new one
            lines.append(' '.join(current_line))
            current_line = [word]
        else:
            current_line.append(word)
    
    # Add the last line
    lines.append(' '.join(current_line))
    
    # Return the text with newlines
    return '\n'.join(lines)



def burn_subtitles_ffmpeg(video_file, srt_file, output_video, font_size=80, font_color="white", outline_color="black", outline_width=2):
    print("----------- BURNING STYLED SRT SUBTITLES TO VIDEO ----------")
    batch_size = 50
    #10 lines of subtitles per batch
    # command prompt has a line limit of 8200
    # There are 101 lines for video 1 rn

    font="Archivo Black"
    
    # Read the subtitles
    subs = pysrt.open(srt_file)
    
    # Prepare the drawtext filter commands for each subtitle line
    total_batches = (len(subs) + batch_size - 1) // batch_size  # Calculate the number of batches
    video_parts=[]
    for batch_num in range(total_batches):
        drawtext_commands = []
        start = batch_num * batch_size
        end = min((batch_num + 1) * batch_size, len(subs))

        batch_start_time = 0 if batch_num==0 else subs[start].start.ordinal / 1000
        batch_end_time = subs[end - 1].end.ordinal / 1000

        # Trim the video for the current batch
        trimmed_video_path = os.path.join(ffmpeg_dir, f"temp_trim_{batch_num}.mp4")
        trim_video_to_audio(video_file, batch_start_time, batch_end_time, trimmed_video_path)



        for i in range(start, end):
            sub = subs[i]
            start_time = sub.start.ordinal / 1000 - batch_start_time # Convert to seconds
            end_time = sub.end.ordinal / 1000  - batch_start_time # Convert to seconds

            wrapped_text=sub.text

            num_lines = len(wrapped_text.split('\n'))
            line_duration = (end_time - start_time) / num_lines

            # Create the drawtext commands for each chunk of 4 words
            for j, line in enumerate(wrapped_text.split('\n')):
                line_start = start_time + j * line_duration
                line_end = line_start + line_duration
                line = escape_text(line)

                drawtext_commands.append(f"drawtext=fontfile={font}:fontsize={font_size}:fontcolor={font_color}:borderw={outline_width}:bordercolor={outline_color}:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{line_start:.3f},{line_end:.3f})':text='{line}'")

    # Join all drawtext commands with commas
        drawtext_filter = ",".join(drawtext_commands)
        fname=os.path.basename(output_video).replace(".mp4","")
        output_batch=os.path.join(ffmpeg_dir, f"{fname}_batch_{batch_num}.mp4")
        video_parts.append(output_batch)

    # Use FFmpeg to burn the styled subtitles with the drawtext filter
        command = [
            'ffmpeg', '-i', trimmed_video_path,
            '-vf', drawtext_filter,
            '-c:a', 'copy',  # Copy audio as is
            '-c:v', 'h264_nvenc',  # Use GPU NVENC encoder for video
            '-preset', 'slow',  # Use 'slow' preset for better quality, or 'hq' for highest
            '-b:v', '15M',  # Set bitrate for quality (adjust as needed, 10M to 20M is typical)
            '-maxrate', '20M',  # Maximum rate
            '-bufsize', '30M',  # Buffer size
            output_batch
        ]
        subprocess.run(command, check=True)
        os.remove(trimmed_video_path)

    concat_videos_ffmpeg(video_parts, output_video)
    # Run the FFmpeg command
    print(f"Styled SRT Subtitles successfully burned to {output_video}")




def overlay_image_to_video(video_path, image_path, summary_tts_path, whole_tts_path):
    print(" --------------- OVERLAYING IMAGE TO VIDEO ------------")
    output_path=os.path.join(ffmpeg_dir,"temp_image_video.mp4")
    # Get the duration of the audio to match the duration of the image overlay
    audio_clip = AudioFileClip(summary_tts_path)
    duration = audio_clip.duration

    # FFmpeg command to overlay the image onto the video
    # overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2 centers the image
    command = [
        'ffmpeg', '-i', video_path, '-i', image_path, '-i', whole_tts_path,
        '-filter_complex', f"[0:v][1:v]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:enable='between(t,0,{duration})'",
        '-c:a', 'copy', # keep audio as is
        '-c:v', 'h264_nvenc',  # Use GPU NVENC encoder for video
        '-preset', 'slow',  # Use 'slow' preset for better quality, or 'hq' for highest
        '-b:v', '15M',  # Set bitrate for quality (adjust as needed, 10M to 20M is typical)
        '-maxrate', '20M',  # Maximum rate
        '-bufsize', '30M',  # Buffer size
        output_path
    ]

    # Run the command
    subprocess.run(command, check=True)
    print(f"Image successfully overlaid on video and saved to {output_path}")
    return output_path

def set_audio_to_video(video_path, audio_path):
    print("--------------- SETTING AUDIO TO VIDEO ------------")
    
    output_video = os.path.join(ffmpeg_dir,"audio_video.mp4")
    # FFmpeg command to add/replace the audio of the video
    command = [
        'ffmpeg', '-y', '-i', video_path, '-i', audio_path,
        '-map', '0:v',  # Map video stream from the first input
        '-map', '1:a',  # Map audio stream from the second input (audio file)
        '-c:v', 'copy',  # Copy video without re-encoding
        '-c:a', 'aac',   # Re-encode audio to AAC
        '-shortest',     # Stop when the shortest stream ends
        '-preset', 'slow',  # Use 'slow' preset for better quality, or 'hq' for highest
        '-b:v', '15M',  # Set bitrate for quality (adjust as needed, 10M to 20M is typical)
        '-maxrate', '20M',  # Maximum rate
        '-bufsize', '30M',  # Buffer size
        output_video
    ]

    # Run the FFmpeg command
    subprocess.run(command, check=True)
    print(f"Audio from {audio_path} successfully added to {output_video}")
    return output_video

def trim_video_to_audio(input_video, start_time, end_time, output_video):
    print("------------- TRIMMING VIDEO -----------")
    if end_time - start_time < 0.1:  # If the duration is less than 0.1 seconds, skip trimming
        print(f"Skipping trimming due to too short duration: start_time={start_time}, end_time={end_time}")
        return input_video  # Return the original video instead of trimming

    command = [
        'ffmpeg', '-i', input_video,
        '-ss', str(start_time), '-to', str(end_time),
        '-c:a', 'copy',  # Disable audio
        '-c:v', 'h264_nvenc',  # Use GPU NVENC encoder for video
        '-preset', 'slow',  # Use 'slow' preset for better quality, or 'hq' for highest
        '-b:v', '15M',  # Set bitrate for quality (adjust as needed, 10M to 20M is typical)
        '-maxrate', '20M',  # Maximum rate
        '-bufsize', '30M',  # Buffer size

        output_video
    ]
    subprocess.run(command, check=True)
    return output_video

def concat_videos_ffmpeg(video_list, output_video):
    print("-------- CONCATENATING VIDEOS WITH COMPLEX FILTER ---------")

    # Prepare input options and build the filter string
    input_videos = []
    concat_filter = ""
    
    # Build the input options and concat filter
    for i, video in enumerate(video_list):
        input_videos.append("-i")
        input_videos.append(video)
        concat_filter += f"[{i}:v:0][{i}:a:0]"

    # Add the concat command at the end of the filter
    concat_filter += f"concat=n={len(video_list)}:v=1:a=1[outv][outa]"

    # FFmpeg command with complex filter for concatenation
    command = [
        'ffmpeg',
        *input_videos,
        '-filter_complex', concat_filter,
        '-map', '[outv]',
        '-map', '[outa]',
        '-c:v', 'h264_nvenc',  # Re-encode the video using GPU NVENC
        '-c:a', 'aac',  # Re-encode the audio to AAC
        '-preset', 'slow',  # Use 'slow' preset for better quality
        '-b:v', '15M',  # Set bitrate for video
        '-maxrate', '20M',  # Set maximum bitrate for video
        '-bufsize', '30M',  # Set buffer size for video
        '-y',  # Overwrite output file if it exists
        output_video
    ]

    # Run FFmpeg command
    print("Running FFmpeg command:", " ".join(command))
    subprocess.run(command, check=True)

    return output_video

def concat_no_audio_video(video_list, output_video):
    print("-------- CONCATENATING VIDEOS ---------")
    concat_list_path = os.path.join(ffmpeg_dir, "concat_list.txt")
    
    with open(concat_list_path, "w", encoding='utf-8') as f:
        for video in video_list:
            f.write(f"file '{video}'\n")
    
    # Run FFmpeg concat with re-encoding using NVENC for GPU acceleration
    command = [
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_list_path,
        '-c:a', 'copy',  # Disable audio
        '-c:v', 'h264_nvenc',  # Use GPU NVENC encoder
        '-preset', 'slow',  # Use 'slow' or 'hq' preset for best quality
        '-b:v', '15M',  # Set target bitrate for high quality (adjust as needed)
        '-maxrate', '20M',  # Set maximum bitrate
        '-bufsize', '30M',  # Set buffer size for smooth bitrate control
        output_video
    ]
    
    subprocess.run(command, check=True)
    os.remove(concat_list_path)  # Clean up the temporary file
    return output_video

def get_random_file(tts_path):
    bgdirectory = "D:/BackgroundVideos/"
    dir1="Bike/"
    dir2="Parkour/"
    dir3="Parkour/"
    dir4="GTA/"
    dir1r=os.path.join(bgdirectory,dir1)
    dir2r=os.path.join(bgdirectory,dir2)
    dir3r=os.path.join(bgdirectory,dir3)
    dir4r=os.path.join(bgdirectory,dir4)
    directories=[dir1r,dir2r,dir3r,dir4r]
    directory=random.choice(directories)

    print("Choosing file from directory: "+ directory)

    # List all files in the directory
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    
    tts_audio = AudioFileClip(tts_path)
    required_duration = tts_audio.duration

    total_duration = 0
    video_parts = []
    used_files = set()

    while total_duration < required_duration:
        print("---------- ITERATING THROUGH GET_RANDOM_FILE ----------")
        random_video = random.choice([f for f in files if f not in used_files])  # Get a random video file (only file name not full path)
        used_files.add(random_video)
        path = os.path.join(directory, random_video)

        # Get video duration using FFmpeg
        command = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=duration', '-of', 'csv=p=0', path
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        video_duration = float(result.stdout.strip())

        remaining_duration = required_duration - total_duration

        # Handle videos shorter than required duration properly
        if video_duration > remaining_duration:
            max_start = video_duration - remaining_duration
            random_start = random.uniform(0, max_start)
            trimmed_video_path = os.path.join(ffmpeg_dir, f"trimmed_{random_video}")
            trim_video_to_audio(path, random_start, random_start + remaining_duration, trimmed_video_path)
            video_parts.append(trimmed_video_path)
            total_duration += remaining_duration
        else:
            trimmed_video_path=path
            video_parts.append(path)
            total_duration += video_duration

    # Concatenate all the video parts using FFmpeg
    video_path = os.path.join(ffmpeg_dir, "selected_video.mp4")
    concat_no_audio_video(video_parts, video_path)
    
    for part in video_parts:
        path = os.path.join(ffmpeg_dir, os.path.basename(part))
        if os.path.exists(path):
            os.remove(path)

    return video_path
