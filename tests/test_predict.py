"""
Test prediction endpoint with audio files
"""

import requests
import os
import sys

SERVER_URL = "http://localhost:5000"

def test_health():
    """Test if server is running"""
    print("\n🔍 Checking server health...")
    try:
        response = requests.get(f"{SERVER_URL}/")
        if response.status_code == 200:
            data = response.json()
            print("✓ Server is running!")
            print(f"  Enrolled users: {data.get('enrolled_users', 0)}")
            return True
        else:
            print(f"✗ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server. Is it running?")
        print("  Run: python server.py")
        return False

def test_prediction(audio_path):
    """Test speaker prediction"""
    print(f"\nTesting prediction...")
    print(f"  File: {audio_path}")
    
    if not os.path.exists(audio_path):
        print(f"✗ File not found: {audio_path}")
        return False
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'audio': (os.path.basename(audio_path), f, 'audio/wav')}
            response = requests.post(f"{SERVER_URL}/predict", files=files)
            
            if response.status_code == 200:
                data = response.json()
                
                print("\nPrediction successful!")
                print("\nResults:")
                print(f"  Predicted: {data['prediction']}")
                print(f"  Confidence: {data['confidence']:.3f}")
                print(f"  Threshold: {data['threshold']}")
                print(f"  Message: {data['message']}")
                
                if 'all_similarities' in data:
                    print("\nSimilarities with all enrolled users:")
                    for user, sim in data['all_similarities'].items():
                        bar = "█" * int(sim * 50)
                        status = "✓" if sim >= data['threshold'] else "✗"
                        print(f"  {status} {user:15s}: {bar} {sim:.3f}")
                
                return True
            else:
                print(f"✗ Prediction failed with status {response.status_code}")
                print(f"  Response: {response.json()}")
                return False
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def get_enrolled_users():
    """Get list of enrolled users"""
    print("\nFetching enrolled users...")
    try:
        response = requests.get(f"{SERVER_URL}/enrolled-users")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Found {data['count']} enrolled users:")
            for user in data['users']:
                print(f"  • {user['username']} (enrolled: {user['enrolled_date'][:10]})")
            return data['users']
        else:
            print(f"✗ Failed to get users")
            return []
    except Exception as e:
        print(f"✗ Error: {e}")
        return []

def find_test_audio(username=None):
    """Find test audio file"""
    # If username specified, try to find their clips
    if username:
        paths = [
            f"test_clips/{username.capitalize()}/",
            f"uploads/enrollments/{username.lower()}/",
        ]
        
        for path in paths:
            if os.path.exists(path):
                files = [f for f in os.listdir(path) if f.endswith('.wav')]
                if files:
                    return os.path.join(path, files[0])
    
    # Otherwise, search common locations
    search_paths = [
        "test_clips/",
        "uploads/enrollments/",
        "data/processed/"
    ]
    
    for base_path in search_paths:
        if os.path.exists(base_path):
            for root, dirs, files in os.walk(base_path):
                wav_files = [f for f in files if f.endswith('.wav')]
                if wav_files:
                    return os.path.join(root, wav_files[0])
    
    return None

def main():
    print("=" * 70)
    print("SPEAKER PREDICTION TEST")
    print("=" * 70)
    
    # Check server
    if not test_health():
        sys.exit(1)
    
    # Get enrolled users
    users = get_enrolled_users()
    
    if len(users) == 0:
        print("\nNo enrolled users found!")
        print("   Run migration first: python migrate_existing.py")
        sys.exit(1)
    
    # Get test audio file
    audio_file = None
    
    if len(sys.argv) > 1:
        # Use provided file
        audio_file = sys.argv[1]
    else:
        # Try to find a test file
        print("\nSearching for test audio...")
        audio_file = find_test_audio()
    
    if not audio_file:
        print("\nNo audio file found for testing")
        print("\nUsage:")
        print("  python test_predict.py <path_to_audio.wav>")
        print("\nOr place audio files in:")
        print("  • audio_clips/")
        print("  • uploads/enrollments/")
        sys.exit(1)
    
    # Test prediction
    test_prediction(audio_file)
    
    print("\n" + "=" * 70)
    print("✓ TEST COMPLETE")
    print("=" * 70)
    print("\n💡 Tips:")

    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()