import os
from pathlib import Path

DIRS_TO_CREATE = [
    "uploads",      #Audio files from browser
    "temp",         #Temporary files for processing
    "logs",         #server logs
    "static",       #static files
    "tests"         #test scripts
]

def create_directories():
    """Create server directory structure"""
    print("\n Creating directory structure...")
    for dir_path in DIRS_TO_CREATE:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print("Created: {dir_path}/")

def create_gitignore():
    """Files to be excluded"""

    gitignore_content = """# Python
    __pycache__/
    *.py[cod]
    *$py.class
    *.so
    .Python
    env/
    venv/
    *.egg-info/

    # Server files
    uploads/*.wav
    temp/*.wav
    logs/*.log

    # IDE
    .vscode/
    .idea/
    *.swp
    *.swo

    # OS
    .DS_Store
    Thumbs.db
    """
    with open('.gitignore', 'w') as f:
        f.write(gitignore_content)

    print("Created: .gitignore")

def create_readme():
    """Create basic README for server"""
    readme_content = """# Speaker Recognition - Flask Server

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run server:
   ```bash
   python server.py
   ```

3. Server runs at: `http://localhost:5000`

## API Endpoints

### POST /upload
Upload audio file for processing

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: audio file (WAV format)

**Response:**
```json
{
  "status": "success",
  "message": "Audio received successfully",
  "file_info": {
    "filename": "recording_123.wav",
    "size_bytes": 128000,
    "duration_seconds": 8.0,
    "sample_rate": 16000,
    "saved_path": "uploads/recording_123.wav"
  }
}
```

## Testing

Run test script to verify server works:
```bash
python tests/test_upload.py
```

## Directory Structure

```
project/
├── server.py              # Main Flask server
├── uploads/              # Received audio files
├── temp/                 # Temporary processing
├── logs/                 # Server logs
├── tests/                # Test scripts
└── requirements.txt      # Dependencies
```
"""
    
    with open('README_SERVER.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("Created: README_SERVER.md")

def print_summary():
    """Print setup summary and next steps"""
    print("\n" + "=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)
    
    print("\nDirectory structure created:")
    for dir_path in DIRS_TO_CREATE:
        print(f"  • {dir_path}/")
    
    print("\nFiles created:")
    print("  • requirements.txt")
    print("  • .gitignore")
    print("  • README_SERVER.md")
    
    print("\nNext Steps:")
    print("\n1. Install dependencies:")
    print("   pip install -r requirements.txt")
    print("\n2. Run server:")
    print("   python server.py")
    print("\n3. Test server:")
    print("   python tests/test_upload.py")
    
    print("\nServer will run at: http://localhost:5000")
    print("   API endpoint: POST http://localhost:5000/upload")
    
    print("\n" + "=" * 60)
    print("Ready to start server development!")
    print("=" * 60 + "\n")

def main():
    create_directories()
    create_gitignore()
    create_readme()
    print_summary()

if __name__ == "__main__":
    main()