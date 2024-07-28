import cv2
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch
import os
import numpy as np
import time
import logging
from sklearn.metrics.pairwise import cosine_similarity
from concurrent.futures import ThreadPoolExecutor
import imgaug.augmenters as iaa
from torchvision import transforms
from PIL import Image


# URL ESP32 CAM
# Konfigurasi logging
# handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
# handler.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
# handler.setFormatter(formatter)
# app.logger.addHandler(handler)

# Inisialisasi model MTCNN untuk deteksi wajah
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(keep_all=False, device=device, thresholds=[0.7, 0.8, 0.9])

# Initialize YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'yolov5s').to('cuda' if torch.cuda.is_available() else 'cpu')
model.eval()

# Inisialisasi model InceptionResnetV1 untuk ekstraksi fitur
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

data_dir = 'C:/Users/randi/Downloads/SKRIPSI/data_set'
asli_dir = os.path.join(data_dir, 'asli')
fake_dir = os.path.join(data_dir, 'fake')

augmenter = iaa.Sequential([
    iaa.Fliplr(0.5),  # Flip horizontal
    iaa.GaussianBlur(sigma=(0.0, 3.0)),  # Gaussian blur
    iaa.AdditiveGaussianNoise(scale=(0, 0.1*255)),  # Gaussian noise
    iaa.Multiply((0.5, 1.5), per_channel=0.5),  # Brightness change
    iaa.ContrastNormalization((0.5, 2.0), per_channel=0.5),  # Contrast change
    iaa.Affine(
        rotate=(-20, 20),  # Rotate
        shear=(-16, 16)    # Shear
    ),
    iaa.PiecewiseAffine(scale=(0.01, 0.05)),  # Piecewise affine transformations
    iaa.Cutout(nb_iterations=2, size=0.2, squared=False),  # Cutout
])

features = []
known_labels = []
fake_features = []

def preprocess_image(image):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (160, 160))
    image = (image - 127.5) / 128.0  # Normalization
    return torch.tensor(image).permute(2, 0, 1).unsqueeze(0).float().to(device)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  # Ubah sesuai dengan password database Anda
        database="datasiswa"
    )

def extract_features(image_path, label=None, is_fake=False):
    image = cv2.imread(image_path)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    boxes, _ = mtcnn.detect(rgb_image)
    
    if boxes is not None:
        for box in boxes:
            x, y, w, h = box.astype(int)
            face = image[y:h, x:w]
            face_tensor = preprocess_image(face)
            embedding = resnet(face_tensor).detach().cpu().numpy().flatten()
            
            if is_fake:
                fake_features.append(embedding)
                augmented_image = augmenter(image=face)  # Do augmentation once
                augmented_embedding = resnet(preprocess_image(augmented_image)).detach().cpu().numpy().flatten()
                fake_features.append(augmented_embedding)
            else:
                features.append(embedding)
                known_labels.append(label)


def process_all_images():
    with ThreadPoolExecutor() as executor:
        for root, dirs, files in os.walk(asli_dir):
            for filename in files:
                image_path = os.path.join(root, filename)
                label = os.path.basename(root)
                executor.submit(extract_features, image_path, label=label, is_fake=False)
        
        for root, dirs, files in os.walk(fake_dir):
            for filename in files:
                image_path = os.path.join(root, filename)
                executor.submit(extract_features, image_path, label='Fake', is_fake=True)

process_all_images()

def adaptive_threshold(frame, base_threshold=0.3):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = np.mean(gray)
    adjusted_threshold = base_threshold

    if brightness < 50:
        adjusted_threshold = base_threshold + 0.2  # Tambah threshold jika gelap
    elif brightness > 200:
        adjusted_threshold = base_threshold - 0.2  # Kurangi threshold jika terang

    return adjusted_threshold

recognized_labels = {}

def is_fake_face(embedding, threshold=0.9 ):
    for fake_embedding in fake_features:
        similarity = cosine_similarity([embedding], [fake_embedding])[0][0]
        if similarity > threshold:
            return True
    return False

last_detection_time = time.time()
detection_interval = 0

# Global variables
last_detection_time = 0
last_cellphone_detection_time = time.time()  # Initialize last detection time for cell phone
cell_phone_boxes = []

def recognize_faces(frame):
    global last_detection_time, cell_phone_boxes, last_cellphone_detection_time
    current_time = time.time()
    
    if current_time - last_detection_time < detection_interval:
        return frame, []

    last_detection_time = current_time

    labels = []

    # Check if cell phone is detected
    cell_phone_detected = False

    # Perform object detection using YOLO
    pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    results = model(pil_image, size=416)

    for detection in results.xyxy[0]:
        x1, y1, x2, y2, conf, cls = detection.tolist()

        # Filter based on confidence level
        if conf < 0.5:
            continue

        # Filter based on object type (e.g., "cell phone" index 67)
        if int(cls) == 67:
            # Calculate object width and height in pixels
            obj_width = x2 - x1
            obj_height = y2 - y1

            # Set minimum distance in pixels
            min_distance_pixels = 10  # Adjust according to camera conditions and object scale

            if obj_width >= min_distance_pixels and obj_height >= min_distance_pixels:
                # Save cell phone box
                cell_phone_boxes.append((x1, y1, x2, y2))

                # Draw box and label for cell phone (red color)
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
                cv2.putText(frame, "Fake", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                # Update last cell phone detection time
                last_cellphone_detection_time = current_time

                # Set cell phone detected flag to true
                cell_phone_detected = True

    # If cell phone is detected, reset the face detection counter
    if cell_phone_detected:
        last_face_detection_time = current_time  # Reset face detection time
        return frame, []

    # Check if it's been 3 seconds since last cell phone detection
    if current_time - last_cellphone_detection_time > 3.0:
        # Perform face detection only if no cell phone is detected and enough time has passed

        # Convert frame to RGB (required for MTCNN)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Perform face detection using MTCNN
        boxes, _ = mtcnn.detect(rgb_frame)

        if boxes is not None:
            for box in boxes:
                x, y, w, h = box.astype(int)

                # Filter out detections based on geometric properties
                # Ensure the box dimensions meet certain criteria (e.g., aspect ratio)
                min_aspect_ratio = 0.5
                max_aspect_ratio = 1.5

                aspect_ratio = (w - x) / (h - y)

                if aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
                    continue  # Skip this box as it does not meet aspect ratio criteria

                # Calculate face distance from camera (assuming 24 pixel per meter scale)
                face_distance = 24 / (h - y)  # distance in meters

                if face_distance > 0.5:
                    labels.append({'label': 'Unknown', 'distance': float('inf'), 'threshold_met': False})
                    cv2.putText(frame, "Unknown", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                    cv2.rectangle(frame, (x, y), (w, h), (255, 0, 0), 2)
                    continue

                # Check brightness level within the face region
                brightness = np.mean(rgb_frame[y:h, x:w])
                if brightness < 50:
                    continue  # Skip this box as brightness is too low

                # Check if the detected face is within any cell phone box
                face_in_phone_box = False
                for phone_box in cell_phone_boxes:
                    phone_x1, phone_y1, phone_x2, phone_y2 = phone_box
                    if x >= phone_x1 and y >= phone_y1 and w <= phone_x2 and h <= phone_y2:
                        face_in_phone_box = True
                        break

                if face_in_phone_box:
                    continue  # Skip this face detection as it is inside a cell phone box

                # Extract face region
                face = frame[max(0, y):min(frame.shape[0], h), max(0, x):min(frame.shape[1], w)]
                if face.shape[0] > 0 and face.shape[1] > 0:
                    # Preprocess face image
                    face_tensor = preprocess_image(face)

                    # Compute embedding using ResNet
                    embedding = resnet(face_tensor).detach().cpu().numpy().flatten()

                    # Check if the face is fake
                    if is_fake_face(embedding):
                        labels.append({'label': 'Fake', 'distance': 0, 'threshold_met': True})
                        cv2.putText(frame, "Fake", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                        cv2.rectangle(frame, (x, y), (w, h), (0, 0, 255), 2)
                        continue

                    # Calculate minimum distance to known embeddings
                    min_distance = float('inf')
                    min_index = None
                    found_match = False

                    current_threshold = adaptive_threshold(frame)

                    for i, known_embedding in enumerate(features):
                        distance = np.linalg.norm(embedding - known_embedding)
                        similarity = cosine_similarity([embedding], [known_embedding])[0][0]
                        if distance < min_distance:
                            min_distance = distance
                            min_index = i
                            if similarity > (1 - current_threshold):
                                found_match = True

                    # Assign label based on recognition result
                    if found_match:
                        label = known_labels[min_index]

                        if label in recognized_labels:
                            verified_label = recognized_labels[label]
                        else:
                            recognized_labels[label] = label
                            verified_label = label

                        labels.append({'label': verified_label, 'distance': min_distance, 'threshold_met': True})
                        cv2.putText(frame, verified_label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                        cv2.rectangle(frame, (x, y), (w, h), (255, 0, 0), 2)
                    else:
                        labels.append({'label': 'Unknown', 'distance': min_distance, 'threshold_met': False})
                        cv2.putText(frame, "Unknown", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                        cv2.rectangle(frame, (x, y), (w, h), (255, 0, 0), 2)
                else:
                    cv2.putText(frame, "Unknown", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                    cv2.rectangle(frame, (x, y), (w, h), (255, 0, 0), 2)
        else:
            cv2.putText(frame, "Unknown", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    return frame, labels