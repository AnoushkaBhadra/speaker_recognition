from resemblyzer import VoiceEncoder, preprocess_wav
import numpy as np

encoder = VoiceEncoder()

wav1 = preprocess_wav("./audio_clips/Anoushka/rec_1_2.wav")
wav2 = preprocess_wav("./audio_clips/Ayushman/recording2025-11-19 12-32-42.wav")

emb1 = encoder.embed_utterance(wav1)
emb2 = encoder.embed_utterance(wav2)

sim = np.dot(emb1, emb2)
print(sim)
