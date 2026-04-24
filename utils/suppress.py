"""
SENTINEL - Warnings & Noise Suppression
This module handles all the messy library-level noise (TensorFlow, DeepFace, OpenCV, etc.)
to ensure a clean console output during execution.
"""

import os
import sys
import logging
import warnings

def silence_the_beasts():
    """
    Applies various suppression techniques to silence common noisy libraries.
    Should be called at the very beginning of the application entry point.
    """
    
    # 1. Silence TensorFlow (0=all, 1=no info, 2=no info/warn, 3=no info/warn/error)
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    os.environ['AUTOGRAPH_VERBOSITY'] = '0'
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    
    # 2. Silence Python warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    
    # 3. Silence specific library loggers
    loggers_to_silence = [
        "tensorflow",
        "keras",
        "deepface",
        "matplotlib",
        "PIL",
        "google.protobuf",
        "absl"
    ]
    
    for logger_name in loggers_to_silence:
        l = logging.getLogger(logger_name)
        l.setLevel(logging.ERROR)
        l.propagate = False

    # 4. Silence standard DeepFace stdout noise
    # We can't easily silence print() globally, but DeepFace specifically 
    # uses it for loading bars and progress info. 

    # 5. Silence OpenCV stderr noise
    os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
    os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'

    print("[SAFE] Sentinel: Noise suppression active. (Clean execution mode)")

if __name__ == "__main__":
    silence_the_beasts()
