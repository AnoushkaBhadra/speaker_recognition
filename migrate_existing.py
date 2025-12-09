"""
Migrate existing audio clips to new enrollment system
Processes clips from audio_clips/ and generates embeddings
"""

import os
import shutil
import numpy as np
import json
from resemblyzer import VoiceEncoder, preprocess_wav
from datetime import datetime

# Configuration
SOURCE_FOLDER = "audio_clips" 
ENROLLMENT_FOLDER = "uploads/enrollments"
EMBEDDINGS_FOLDER = "embeddings"
REGISTRY_FILE = os.path.join(EMBEDDINGS_FOLDER, "registry.json")

# Number of clips to use per speaker (from your existing clips)
CLIPS_TO_USE = 3

# Initialize encoder
encoder = VoiceEncoder()

def extract_embedding(audio_path):
    """Extract voice embedding from audio file"""
    try:
        wav = preprocess_wav(audio_path)
        embedding = encoder.embed_utterance(wav)
        return embedding
    except Exception as e:
        print(f"Error extracting embedding: {e}")
        return None

def load_registry():
    """Load the registry of enrolled users"""
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_registry(registry):
    """Save the registry of enrolled users"""
    os.makedirs(EMBEDDINGS_FOLDER, exist_ok=True)
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2)

def migrate_speaker(speaker_name):
    """Migrate one speaker's audio clips"""
    print(f"\nProcessing {speaker_name}...")
    
    source_path = os.path.join(SOURCE_FOLDER, speaker_name)
    
    if not os.path.exists(source_path):
        print(f"Folder not found: {source_path}")
        return False
    
    # Get all audio files
    audio_files = [f for f in os.listdir(source_path) if f.endswith('.wav')]
    
    if len(audio_files) == 0:
        print(f"No audio files found")
        return False
    
    print(f"  Found {len(audio_files)} audio files")
    
    # Use first N clips
    clips_to_process = audio_files[:CLIPS_TO_USE]
    print(f"  Using first {len(clips_to_process)} clips for enrollment")
    
    # Create enrollment folder
    username = speaker_name.lower()
    user_folder = os.path.join(ENROLLMENT_FOLDER, username)
    os.makedirs(user_folder, exist_ok=True)
    
    # Copy and rename clips
    embeddings = []
    for i, filename in enumerate(clips_to_process, 1):
        src = os.path.join(source_path, filename)
        dst = os.path.join(user_folder, f"clip_{i}.wav")
        
        # Copy file
        shutil.copy2(src, dst)
        print(f"Copied: {filename} → clip_{i}.wav")
        
        # Extract embedding
        emb = extract_embedding(dst)
        if emb is not None:
            embeddings.append(emb)
    
    if len(embeddings) == 0:
        print(f"Failed to extract any embeddings")
        return False
    
    # Average embeddings
    print(f"  Computing average embedding from {len(embeddings)} clips...")
    avg_embedding = np.mean(embeddings, axis=0)
    
    # Save embedding
    embedding_path = os.path.join(EMBEDDINGS_FOLDER, f"{username}.npy")
    np.save(embedding_path, avg_embedding)
    print(f"Saved embedding: {embedding_path}")
    
    # Update registry
    registry = load_registry()
    registry[username] = {
        'enrolled_date': datetime.now().isoformat(),
        'clips_count': len(embeddings),
        'embedding_file': f"{username}.npy",
        'migrated_from': speaker_name
    }
    save_registry(registry)
    print(f"Added to registry")
    
    return True

def main():
    print("=" * 70)
    print("MIGRATING EXISTING AUDIO CLIPS")
    print("=" * 70)
    
    # Check if source folder exists
    if not os.path.exists(SOURCE_FOLDER):
        print(f"\nSource folder not found: {SOURCE_FOLDER}")
        print("   Make sure audio_clips/ folder exists with speaker folders inside")
        return
    
    # Create necessary folders
    os.makedirs(ENROLLMENT_FOLDER, exist_ok=True)
    os.makedirs(EMBEDDINGS_FOLDER, exist_ok=True)
    
    # Get all speaker folders
    speakers = [d for d in os.listdir(SOURCE_FOLDER) 
                if os.path.isdir(os.path.join(SOURCE_FOLDER, d))]
    
    if len(speakers) == 0:
        print(f"\nNo speaker folders found in {SOURCE_FOLDER}")
        return
    
    print(f"\nFound {len(speakers)} speakers: {', '.join(speakers)}")
    print(f"Will use {CLIPS_TO_USE} clips per speaker for enrollment")
    
    # Process each speaker
    successful = []
    failed = []
    
    for speaker in speakers:
        if migrate_speaker(speaker):
            successful.append(speaker)
        else:
            failed.append(speaker)
    
    # Summary
    print("\n" + "=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    
    if successful:
        print(f"\nSuccessfully migrated ({len(successful)}):")
        for speaker in successful:
            print(f"  • {speaker} → {speaker.lower()}")
    
    if failed:
        print(f"\nFailed to migrate ({len(failed)}):")
        for speaker in failed:
            print(f"  • {speaker}")
    
    # Show registry
    registry = load_registry()
    print(f"\nTotal enrolled users: {len(registry)}")
    
    print("\n" + "=" * 70)
    print("✓ MIGRATION COMPLETE!")
    print("=" * 70)
    

if __name__ == "__main__":
    main()