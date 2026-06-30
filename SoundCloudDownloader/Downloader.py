import os
import yt_dlp

def download_soundcloud_as_wav(url, output_folder="downloads"):
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    # Configuration options for yt-dlp
    ydl_opts = {
        # Format code to extract the best quality audio
        'format': 'bestaudio/best',
        
        # Where to save the file and what to name it
        'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
        
        # Post-processor options to convert the file to WAV
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '0',  # 0 means best quality
        }],
        
        # Optional: Suppress a lot of terminal noise
        'quiet': False,
    }

    try:
        print(True, f"Starting download for: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("Success! Your WAV file is ready in the 'downloads' folder.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Replace with your target SoundCloud URL (track, playlist, or artist page)
    soundcloud_url = input("Enter the SoundCloud URL: ")
    download_soundcloud_as_wav(soundcloud_url)