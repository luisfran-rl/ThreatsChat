import os
import yt_dlp

def download_soundcloud_as_wav(url, output_folder="downloads"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    # UPDATE HERE: Added 'orig/bestaudio/best' to the format key
    ydl_opts = {
        # This tells yt-dlp to grab the original un-transcoded file if available
        'format': 'orig/bestaudio/best',
        
        'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
        
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '0',
        }],
        
        'quiet': False,
    }

    try:
        print(f"Starting download for: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("Success! Your WAV file is ready in the 'downloads' folder.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    soundcloud_url = input("Enter the SoundCloud URL: ")
    download_soundcloud_as_wav(soundcloud_url)