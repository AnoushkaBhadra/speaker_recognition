import requests
import os
import sys

# Server URL
SERVER_URL = "http://localhost:5000"

def test_server_health():
    """Test if server is running"""
    print("\nTesting server health...")
    try:
        response = requests.get(f"{SERVER_URL}/")
        if response.status_code == 200:
            print("Server is running!")
            print(f"  Response: {response.json()}")
            return True
        else:
            print(f"Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("Cannot connect to server. Is it running?")
        print("  Run: python server.py")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_upload_audio(audio_file_path):
    """Test uploading an audio file"""
    print(f"\nTesting audio upload...")
    print(f"  File: {audio_file_path}")
    
    if not os.path.exists(audio_file_path):
        print(f"File not found: {audio_file_path}")
        return False
    
    try:
        # Prepare file for upload
        with open(audio_file_path, 'rb') as f:
            files = {'audio': (os.path.basename(audio_file_path), f, 'audio/wav')}
            
            # Send POST request
            response = requests.post(f"{SERVER_URL}/upload", files=files)
            
            if response.status_code == 200:
                print(" Upload successful!")
                data = response.json()
                
                print("\nServer Response:")
                print(f"  Status: {data['status']}")
                print(f"  Message: {data['message']}")
                
                if 'file_info' in data:
                    info = data['file_info']
                    print(f"\nFile Info:")
                    print(f"  Filename: {info['filename']}")
                    print(f"  Size: {info['size_kb']} KB")
                    print(f"  Duration: {info['duration_seconds']} seconds")
                    print(f"  Sample Rate: {info['sample_rate']} Hz")
                    print(f"  Saved at: {info['saved_path']}")
                
                return True
            else:
                print(f"✗ Upload failed with status {response.status_code}")
                print(f"  Response: {response.json()}")
                return False
                
    except Exception as e:
        print(f"Error during upload: {e}")
        return False

def test_list_uploads():
    """Test listing uploaded files"""
    print("\nTesting list uploads...")
    try:
        response = requests.get(f"{SERVER_URL}/list-uploads")
        if response.status_code == 200:
            data = response.json()
            print("List retrieved successfully!")
            print(f"  Total files: {data['count']}")
            if data['count'] > 0:
                print(f"  Files: {', '.join(data['files'][:5])}")
                if data['count'] > 5:
                    print(f"  ... and {data['count'] - 5} more")
            return True
        else:
            print(f"Failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def find_test_audio():
    """Try to find an audio file to test with"""
    # Check common locations
    possible_paths = [
        "data/processed/anoushka/anoushka_001.wav",
        "data/processed/ayushman/ayushman_001.wav",
        "data/processed/saumi/saumi_001.wav",
        "../data/processed/anoushka/anoushka_001.wav",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def main():
    print("=" * 60)
    print("FLASK SERVER TEST SUITE")
    print("=" * 60)
    
    # Test 1: Server health
    if not test_server_health():
        print("\nServer is not running. Start it with: python server.py")
        sys.exit(1)
    
    # Test 2: Upload audio
    audio_file = None
    
    # Check if audio file path provided as argument
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    else:
        # Try to find a test audio file
        audio_file = find_test_audio()
    
    if audio_file:
        test_upload_audio(audio_file)
    else:
        print("\nNo audio file found for testing")
        print("   Usage: python test_upload.py <path_to_audio.wav>")
        print("   Or place audio files in data/processed/")
    
    # Test 3: List uploads
    test_list_uploads()
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()