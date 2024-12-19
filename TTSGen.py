import requests
import random
import os
import json

# Azure Speech Service credentials
AZURE_API_KEY = "fdfd85b0513d4fc7b0a895f471fc5ec9"
AZURE_REGION = "eastus"
AZURE_TTS_URL = f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"

# Voice options (replace with actual Azure TTS voice names)
def get_voice_id(gender):
    voices = [
        
        "en-US-AnaNeural",
        "en-US-AshleyNeural",
        "en-US-CoraNeural",
        "en-US-ElizabethNeural",
        "en-US-MichelleNeural",
        "en-US-MonicaNeural",
        "en-US-RogerNeural",
        "en-US-LunaNeural",
        "en-US-AmberNeural",
        "en-US-NancyNeural",
        "en-US-JaneNeural",
        "en-US-SaraNeural",
        "en-US-AriaNeural",
        "en-US-EmmaNeural",
        "en-US-JennyNeural"
    ]
    male_voices = [
        "en-US-GuyNeural",
        "en-US-GuyNeural",
        "en-US-GuyNeural",
        "en-US-SteffanNeural",
        "en-US-ChristopherNeural",
        "en-US-BrandonNeural",
        "en-US-EricNeural",
        "en-US-JacobNeural",
        "en-US-TonyNeural",
        "en-US-KaiNeural",
        "en-US-BrianNeural",
        "en-US-AndrewNeural",
        "en-US-DavisNeural"
    ]
    
    choice = random.choice(voices) if gender == 'f' else random.choice(male_voices)
    print(f"Chose voice: {choice} for gender {gender}")
    return choice

# Function to generate TTS using Azure AI Speech Service
def generate_tts_files(id, summary, story, gender):
    story_output_file = f"D:/TTVG/output_audio/story_tts_audio_{id}.mp3"
    summary_output_file = f"D:/TTVG/output_audio/image_tts_audio_{id}.mp3"
    voice_id = get_voice_id(gender)

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_API_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-48khz-192kbitrate-mono-mp3"  # MP3 output
    }

    # SSML (Speech Synthesis Markup Language) payload for summary and story
    def create_ssml(text):
        break_time="x-weak"
        adjusted_text = text.replace('.', f'.<break strength="{break_time}"/>')


        return f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
            <voice name='{voice_id}'>
                <prosody rate='1.325'>{adjusted_text}</prosody>
            </voice>
        </speak>
        """

    # Create SSML payloads
    summary_ssml = create_ssml(summary)
    story_ssml = create_ssml(story)

    # Make the requests for summary and story TTS generation
    summary_response = requests.post(AZURE_TTS_URL, headers=headers, data=summary_ssml.encode('utf-8'))
    story_response = requests.post(AZURE_TTS_URL, headers=headers, data=story_ssml.encode('utf-8'))

    # Check if both requests were successful
    if summary_response.status_code == 200 and story_response.status_code == 200:
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(summary_output_file), exist_ok=True)
        os.makedirs(os.path.dirname(story_output_file), exist_ok=True)

        # Save the audio files
        with open(summary_output_file, 'wb') as audio_file:
            audio_file.write(summary_response.content)
        with open(story_output_file, 'wb') as audio_file:
            audio_file.write(story_response.content)

        print(f"TTS audio files saved.")
    else:
        # Error handling
        print(f"Error: {summary_response.status_code} - {summary_response.text}")
        print(f"Error: {story_response.status_code} - {story_response.text}")

    return summary_output_file
