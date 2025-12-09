from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import numpy as np
from datetime import datetime
from werkzeug.utils import secure_filename
import logging
import json
from resemblyzer import VoiceEncoder, preprocess_wav
import subprocess
import tempfile
import shutil

app = Flask(__name__)
CORS(app)  

# Configuration
UPLOAD_FOLDER = 'uploads'
ENROLLMENT_FOLDER = 'uploads/enrollments'
PREDICTION_FOLDER = 'uploads/predictions'
EMBEDDINGS_FOLDER = 'embeddings'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'webm', 'm4a'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
REQUIRED_CLIPS = 4  # Number of clips needed for enrollment
SIMILARITY_THRESHOLD = 0.75  # Threshold for speaker recognition

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize voice encoder
encoder = VoiceEncoder()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/server.log'),
        logging.StreamHandler()
    ]
)

# Registry file to track enrolled users
REGISTRY_FILE = os.path.join(EMBEDDINGS_FOLDER, 'registry.json')

def load_registry():
    """Load the registry of enrolled users"""
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_registry(registry):
    """Save the registry of enrolled users"""
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_embedding(audio_path):
    """Extract voice embedding from audio file"""
    try:
        wav = preprocess_wav(audio_path)
        embedding = encoder.embed_utterance(wav)
        return embedding
    except Exception as e:
        logging.error(f"Error extracting embedding: {e}")
        return None


def convert_to_wav(input_path, output_path, sample_rate=16000):
    """Convert an audio file (webm/ogg/mp3/...) to a single-channel PCM WAV using ffmpeg.
    Returns True on success, False on failure.
    Requires `ffmpeg` to be installed and available in PATH.
    """
    try:
        cmd = [
            'ffmpeg',
            '-y',
            '-i', input_path,
            '-ar', str(sample_rate),
            '-ac', '1',
            '-sample_fmt', 's16',
            output_path
        ]
        logging.info(f"Converting {input_path} -> {output_path} using ffmpeg")
        completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if completed.returncode != 0:
            logging.error(f"ffmpeg conversion failed: {completed.stderr.decode('utf-8', errors='ignore')}")
            return False
        return True
    except FileNotFoundError:
        logging.error('ffmpeg not found. Please install ffmpeg and ensure it is in PATH.')
        return False
    except Exception as e:
        logging.error(f"Unexpected error during conversion: {e}")
        return False


def save_uploaded_and_convert(file_storage, target_wav_path):
    """Save the uploaded file preserving extension, convert to WAV and write to target_wav_path.
    If the file is already .wav, copy it directly without conversion.
    Returns True on success, False on failure.
    """
    # Save uploaded to a temporary file with its original extension
    orig_filename = secure_filename(file_storage.filename or 'upload')
    ext = ''
    if '.' in orig_filename:
        ext = '.' + orig_filename.rsplit('.', 1)[1].lower()
    
    # Check if already WAV format
    if ext == '.wav':
        try:
            file_storage.save(target_wav_path)
            logging.info(f"Saved WAV file directly (no conversion needed): {target_wav_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving WAV file directly: {e}")
            return False
    
    # Not WAV, so convert
    try:
        fd, temp_path = tempfile.mkstemp(suffix=ext)
        os.close(fd)
        file_storage.save(temp_path)
        logging.info(f"Saved temporary upload to {temp_path}")

        # Convert to WAV at target path
        success = convert_to_wav(temp_path, target_wav_path)
        try:
            os.remove(temp_path)
        except Exception:
            pass
        return success
    except Exception as e:
        logging.error(f"Error saving/converting upload: {e}")
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        return False

def compute_similarity(embedding1, embedding2):
    """Compute cosine similarity between two embeddings"""
    return np.dot(embedding1, embedding2)

@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    registry = load_registry()
    return jsonify({
        'status': 'running',
        'message': 'Speaker Recognition Server',
        'enrolled_users': len(registry),
        'endpoints': {
            'health': '/ (GET)',
            'enroll': '/enroll (POST)',
            'predict': '/predict (POST)',
            'enrolled_users': '/enrolled-users (GET)',
            'delete_user': '/delete-user/<username> (DELETE)'
        }
    }), 200

@app.route('/enroll', methods=['POST'])
def enroll_speaker():
    """
    Enroll a new speaker with audio clips
    Requires: username, clip_number, audio file
    """
    try:
        # Get username and clip number
        username = request.form.get('username', '').strip().lower()
        clip_number = request.form.get('clip_number', '')
        
        if not username:
            return jsonify({
                'status': 'error',
                'message': 'Username is required'
            }), 400
        
        if not clip_number or not clip_number.isdigit():
            return jsonify({
                'status': 'error',
                'message': 'Valid clip_number (1-5) is required'
            }), 400
        
        clip_number = int(clip_number)
        if clip_number < 1 or clip_number > REQUIRED_CLIPS:
            return jsonify({
                'status': 'error',
                'message': f'clip_number must be between 1 and {REQUIRED_CLIPS}'
            }), 400
        
        # Check audio file
        if 'audio' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No audio file provided'
            }), 400
        
        file = request.files['audio']
        
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400
        
        # Create user enrollment folder
        user_folder = os.path.join(ENROLLMENT_FOLDER, username)
        os.makedirs(user_folder, exist_ok=True)
        
        # Save audio file to a temp file and convert to WAV
        filename = f"clip_{clip_number}.wav"
        filepath = os.path.join(user_folder, filename)
        success = save_uploaded_and_convert(file, filepath)
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Failed to convert uploaded audio to WAV. Ensure ffmpeg is installed and file format is supported.'
            }), 400
        logging.info(f"Saved enrollment clip (converted): {filepath}")

        # Count how many clips user has
        existing_clips = len([f for f in os.listdir(user_folder) if f.startswith('clip_')])
        
        # If all clips received, generate embedding
        if existing_clips >= REQUIRED_CLIPS:
            logging.info(f"Generating embedding for {username}...")
            
            # Extract embeddings from all clips
            embeddings = []
            for i in range(1, REQUIRED_CLIPS + 1):
                clip_path = os.path.join(user_folder, f"clip_{i}.wav")
                if os.path.exists(clip_path):
                    emb = extract_embedding(clip_path)
                    if emb is not None:
                        embeddings.append(emb)
            
            if len(embeddings) == 0:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to extract embeddings from audio clips'
                }), 500
            
            # Average embeddings for robustness
            avg_embedding = np.mean(embeddings, axis=0)
            
            # Save embedding
            embedding_path = os.path.join(EMBEDDINGS_FOLDER, f"{username}.npy")
            np.save(embedding_path, avg_embedding)
            logging.info(f"Saved embedding: {embedding_path}")
            
            # Update registry
            registry = load_registry()
            registry[username] = {
                'enrolled_date': datetime.now().isoformat(),
                'clips_count': len(embeddings),
                'embedding_file': f"{username}.npy"
            }
            save_registry(registry)
            
            return jsonify({
                'status': 'success',
                'message': f'Enrollment complete for {username}!',
                'username': username,
                'clips_received': existing_clips,
                'required_clips': REQUIRED_CLIPS,
                'enrollment_complete': True
            }), 200
        
        else:
            return jsonify({
                'status': 'success',
                'message': f'Clip {clip_number}/{REQUIRED_CLIPS} received',
                'username': username,
                'clips_received': existing_clips,
                'required_clips': REQUIRED_CLIPS,
                'enrollment_complete': False
            }), 200
        
    except Exception as e:
        logging.error(f"Error in enrollment: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/predict', methods=['POST'])
def predict_speaker():
    """
    Predict speaker from audio clip
    Compares against all enrolled speakers
    """
    try:
        # Check audio file
        if 'audio' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No audio file provided'
            }), 400
        
        file = request.files['audio']
        
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400
        
        os.makedirs(PREDICTION_FOLDER, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"prediction_{timestamp}.wav"
        filepath = os.path.join(PREDICTION_FOLDER, filename)

        # Save uploaded to temp and convert to WAV in prediction folder
        success = save_uploaded_and_convert(file, filepath)
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Failed to convert uploaded audio to WAV. Ensure ffmpeg is installed and file format is supported.'
            }), 400
        logging.info(f"Saved prediction file (converted): {filepath}")

        test_embedding = extract_embedding(filepath)

        if test_embedding is None:
            try:
                os.remove(filepath)
            except:
                pass
            return jsonify({
                'status': 'error',
                'message': 'Failed to process audio'
            }), 500
        
        # Load registry
        registry = load_registry()
        
        if len(registry) == 0:
            return jsonify({
                'status': 'success',
                'prediction': 'Unknown',
                'confidence': 0.0,
                'message': 'No enrolled users in system'
            }), 200
        
        # Compare with all enrolled speakers
        best_match = None
        best_similarity = -1
        similarities = {}
        
        for username in registry.keys():
            embedding_path = os.path.join(EMBEDDINGS_FOLDER, f"{username}.npy")
            
            if os.path.exists(embedding_path):
                stored_embedding = np.load(embedding_path)
                similarity = compute_similarity(test_embedding, stored_embedding)
                similarities[username] = float(similarity)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = username
        
        # Check if best match exceeds threshold
        if best_similarity >= SIMILARITY_THRESHOLD:
            prediction = best_match
            message = f"Matched with {best_match}"
        else:
            prediction = "Unknown"
            message = "No match found above threshold"
        
        logging.info(f"Prediction: {prediction} (confidence: {best_similarity:.3f})")
        
        # Clean up temp file
        try:
            os.remove(filepath)
        except:
            pass
        
        return jsonify({
            'status': 'success',
            'prediction': prediction,
            'confidence': float(best_similarity),
            'threshold': SIMILARITY_THRESHOLD,
            'all_similarities': similarities,
            'message': message
        }), 200
        
    except Exception as e:
        logging.error(f"Error in prediction: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/enrolled-users', methods=['GET'])
def get_enrolled_users():
    """Get list of all enrolled users"""
    try:
        registry = load_registry()
        
        users_list = []
        for username, info in registry.items():
            users_list.append({
                'username': username,
                'enrolled_date': info.get('enrolled_date', 'Unknown'),
                'clips_count': info.get('clips_count', 0)
            })
        
        return jsonify({
            'status': 'success',
            'count': len(users_list),
            'users': users_list
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting enrolled users: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/delete-user/<username>', methods=['DELETE'])
def delete_user(username):
    """Delete an enrolled user"""
    try:
        username = username.strip().lower()
        registry = load_registry()
        
        if username not in registry:
            return jsonify({
                'status': 'error',
                'message': f'User {username} not found'
            }), 404

        embedding_path = os.path.join(EMBEDDINGS_FOLDER, f"{username}.npy")
        if os.path.exists(embedding_path):
            os.remove(embedding_path)

        user_folder = os.path.join(ENROLLMENT_FOLDER, username)
        if os.path.exists(user_folder):
            import shutil
            shutil.rmtree(user_folder)

        del registry[username]
        save_registry(registry)
        
        logging.info(f"Deleted user: {username}")
        
        return jsonify({
            'status': 'success',
            'message': f'User {username} deleted successfully'
        }), 200
        
    except Exception as e:
        logging.error(f"Error deleting user: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({
        'status': 'error',
        'message': 'File too large. Maximum size is 10MB'
    }), 413

if __name__ == '__main__':
    # Ensure folders exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(ENROLLMENT_FOLDER, exist_ok=True)
    os.makedirs(PREDICTION_FOLDER, exist_ok=True)
    os.makedirs(EMBEDDINGS_FOLDER, exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    if not os.path.exists(REGISTRY_FILE):
        save_registry({})
    
    print("\n" + "=" * 70)
    print("SPEAKER RECOGNITION SERVER")
    print("=" * 70)
    print(f"\nServer URL: http://localhost:5000")
    print(f"\nAPI Endpoints:")
    print(f"  • GET    /                    - Health check")
    print(f"  • POST   /enroll              - Enroll new speaker (5 clips)")
    print(f"  • POST   /predict             - Predict speaker from audio")
    print(f"  • GET    /enrolled-users      - List all enrolled users")
    print(f"  • DELETE /delete-user/<name>  - Delete enrolled user")
    print(f"\nConfiguration:")
    print(f"  • Clips required: {REQUIRED_CLIPS} per user")
    print(f"  • Similarity threshold: {SIMILARITY_THRESHOLD}")
    print(f"  • Max file size: {MAX_FILE_SIZE / (1024*1024):.0f}MB")
    
    # Show enrolled users
    registry = load_registry()
    print(f"\n👥 Enrolled Users: {len(registry)}")
    if registry:
        for username in registry.keys():
            print(f"  • {username}")
    
    print("\n" + "=" * 70)
    print("✓ Server Ready!")
    print("=" * 70 + "\n")
    
    # Run server
    app.run(debug=True, host='0.0.0.0', port=5000)