# Code for the "video-processing" lambda in the tutorial
# See: https://youtu.be/zMhOwHUwe2Y
import sys
import os
import shutil
import json

import google.generativeai as genai
import cv2
import requests

GOOGLE_API_KEY=os.getenv('GOOGLE_API_KEY', None)
genai.configure(api_key=GOOGLE_API_KEY)

# Create or cleanup existing extracted image frames directory.
FRAME_EXTRACTION_DIRECTORY = "/tmp/frames"
FRAME_PREFIX = "_frame"

def create_frame_output_dir(output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        shutil.rmtree(output_dir)  # Cleanup existing directory
        os.makedirs(output_dir)  # Recreate directory

def extract_frame_from_video(video_url):
    try:
        print(f"Extracting from {video_url} at 5 frames per second with millisecond precision. This might take a bit...")
        create_frame_output_dir(FRAME_EXTRACTION_DIRECTORY)
        vidcap = cv2.VideoCapture(video_url)
        fps = vidcap.get(cv2.CAP_PROP_FPS)
        print(f'Video FPS: {fps}')

        # Calculate the interval (in frame counts) at which to grab a frame to achieve 5 fps extraction.
        frame_interval = max(1, int(fps / 5))
        
        output_file_prefix = os.path.basename(video_url).replace('.', '_')
        original_frame_number = 0

        while vidcap.isOpened():
            success, frame = vidcap.read()
            if not success:  # End of video
                break

            if original_frame_number % frame_interval == 0:
                # Calculate the timestamp in milliseconds
                time_milliseconds = (original_frame_number / fps) * 1000
                # Format the time string to include minutes, seconds, and milliseconds
                min, msec = divmod(time_milliseconds, 60000)
                sec, msec = divmod(msec, 1000)
                time_string = f"{int(min):02d}:{int(sec):02d}:{int(msec):03d}"
                
                image_name = f"{output_file_prefix}{FRAME_PREFIX}{time_string}.jpg"
                output_filename = os.path.join(FRAME_EXTRACTION_DIRECTORY, image_name)
                cv2.imwrite(output_filename, frame)
            
            original_frame_number += 1

        vidcap.release()
        return("Completed video frame extraction.")

    except Exception as e:
        print(f"Error extracting frames: {e}")
        return("Error extracting frames.")

class File:
    def __init__(self, file_path: str, display_name: str = None):
        self.file_path = file_path
        if display_name:
            self.display_name = display_name
        self.timestamp = get_timestamp(file_path)

    def set_file_response(self, response):
        self.response = response

def get_timestamp(filename):
    """Extracts the frame count (as an integer) from a filename with the format
        'output_file_prefix_frame00:00:00.jpg'.
    """
    parts = filename.split(FRAME_PREFIX)
    print(parts)
    if len(parts) != 2:
        return None  # Indicates the filename might be incorrectly formatted
    print("Timestamp:")
    print( parts[1].split('.')[0] )
    return parts[1].split('.')[0]


def prepare_files_to_upload():
    """Prepares the files to upload to the API by extracting the frame count from the filename."""
    files = os.listdir(FRAME_EXTRACTION_DIRECTORY)
    files = sorted(files)
    files_to_upload = []
    for file in files:
        files_to_upload.append(
            File(file_path=os.path.join(FRAME_EXTRACTION_DIRECTORY, file)))

    return files_to_upload


def upload_files_to_gcp(files_to_upload, count=None):
    uploaded_files = []

    count = count if count else len(files_to_upload)
    print(f'Preparing to upload {count} files...')

    for file in files_to_upload[:count]:
        print(f'Uploading: {file.file_path}...')
        response = genai.upload_file(path=file.file_path)
        file.set_file_response(response)
        uploaded_files.append(file)

    print(f"Completed file uploads!\n\nUploaded: {len(uploaded_files)} files")

    return uploaded_files

def create_content_parts(uploaded_files):
    content_parts = []
    for f in uploaded_files:

        # Extract the timestamp, uri, and mimetype from the file response
        timestamp = f.timestamp
        uri = f.response.uri
        mimetype = f.response.mime_type

        # Create the text and fileData parts for the content
        text_part = f"part {{ text = \"{timestamp}\" }}"
        file_data_part = f"part {{ fileData = fileData {{ fileUri = \"{uri}\", mimeType = \"{mimetype}\" }} }}"

        # Append the text and fileData parts to the content parts list
        content_parts.append(text_part)
        content_parts.append(file_data_part)

    return content_parts

def send_content_parts_to_bubble(video_id, bubble_url, content_parts):

    payload = {
        "contentParts": content_parts,
        "videoId": video_id
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f'Bearer {os.getenv("BUBBLE_API_KEY")}'
    }
    response = requests.post(bubble_url, json=payload, headers=headers)
    print(f"Response from Bubble: {response.text}")

    return response.text

# Example usage
def handler(event, context):

    # Extract variables from event
    video_url = event.get('video_url', None)
    count = event.get('count', None)
    bubble_url = event.get('bubble_url', None)
    bubble_video_id = event.get('video_id', None)

    # Check if video_url is provided
    if not video_url:
        return 'Missing video_url in request body'
    
    # Extract frames from video
    parsing_result = extract_frame_from_video(video_url)

    # Prepare files to upload to GCP
    files_to_upload = prepare_files_to_upload()

    # Upload specified number of files to GCP
    uploaded_files = upload_files_to_gcp(files_to_upload, count)

    # Create content parts for Bubble
    content_parts = create_content_parts(uploaded_files)
    print("Content parts:")
    print(content_parts)

    # Send content parts to Bubble
    send_content_parts_to_bubble(bubble_video_id, bubble_url, content_parts)

    return "Completed processing video."
