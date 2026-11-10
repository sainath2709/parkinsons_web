import os
import secrets
import uuid
import matplotlib.cm as cm
from functools import wraps
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, User, ScanHistory

import numpy as np
from PIL import Image
import tensorflow as tf
from openai import OpenAI

# Automatically load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as _env_f:
        for _line in _env_f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
CORS(app)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parkinsons.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create uploads directory
os.makedirs(os.path.join(app.static_folder, 'uploads'), exist_ok=True)

# Grad-CAM Helpers
def get_last_conv_layer(model):
    for layer in reversed(model.layers):
        try:
            if hasattr(layer, 'output') and layer.output is not None:
                if hasattr(layer.output, 'shape') and len(layer.output.shape) == 4:
                    return layer.name
        except Exception:
            pass
    return None

def make_gradcam_heatmap(img_array, model, last_conv_layer_name, pred_index=None):
    grad_model = tf.keras.models.Model(
        [model.inputs], [model.get_layer(last_conv_layer_name).output, model.output]
    )
    with tf.GradientTape() as tape:
        last_conv_layer_output, preds = grad_model(img_array)
        
        # Unpack nested elements safely to prevent indexing tuples
        if isinstance(last_conv_layer_output, (list, tuple)):
            last_conv_layer_output = last_conv_layer_output[0]
        if isinstance(preds, (list, tuple)):
            preds = preds[0]
            
        if pred_index is None:
            pred_index = tf.argmax(preds[0])
            
        class_channel = preds[:, int(pred_index)]
    grads = tape.gradient(class_channel, last_conv_layer_output)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    last_conv_layer_output = last_conv_layer_output[0]
    heatmap = last_conv_layer_output @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)
    return heatmap.numpy()

def save_and_display_gradcam(img_path, heatmap, cam_path, alpha=0.4):
    # Use PIL to load the image
    img = Image.open(img_path).convert('RGB')
    img_array = np.array(img)
    
    # Rescale heatmap
    heatmap = np.uint8(255 * heatmap)
    jet = cm.get_cmap("jet")
    jet_colors = jet(np.arange(256))[:, :3]
    jet_heatmap = jet_colors[heatmap]
    
    # Create an image with RGB colorized heatmap
    jet_heatmap = Image.fromarray(np.uint8(jet_heatmap * 255))
    jet_heatmap = jet_heatmap.resize((img_array.shape[1], img_array.shape[0]))
    jet_heatmap_array = np.array(jet_heatmap)
    
    # Superimpose the heatmap on original image
    superimposed_img = jet_heatmap_array * alpha + img_array
    superimposed_img = Image.fromarray(np.clip(superimposed_img, 0, 255).astype(np.uint8))
    superimposed_img.save(cam_path)

# Load Model
MODEL_PATH = 'CP_DenseNet121_Final.h5'
model = None
try:
    if os.path.exists(MODEL_PATH):
        model = tf.keras.models.load_model(MODEL_PATH)
        print(f"Model {MODEL_PATH} loaded successfully.")
    else:
        print(f"Warning: Model file {MODEL_PATH} not found.")
except Exception as e:
    print(f"Error loading model {MODEL_PATH}: {e}")

# DeepSeek / OpenRouter API Configuration
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

SYSTEM_PROMPT = """You are a medical assistant specializing in Parkinson's disease. Help users understand 
their diagnosis, explain the disease, causes, symptoms, precautions, treatment options. 
When asked about nearby hospitals, ask for their city and suggest neurology hospitals there."""

# Autodetect OpenRouter vs DeepSeek direct
if DEEPSEEK_API_KEY.startswith("sk-or-"):
    BASE_URL = "https://openrouter.ai/api/v1"
    CHAT_MODEL = "deepseek/deepseek-chat"
else:
    BASE_URL = "https://api.deepseek.com/v1"
    CHAT_MODEL = "deepseek-chat"

# Initialize OpenAI client pointing to the correct base URL
deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY or "dummy_key", base_url=BASE_URL)

with app.app_context():
    db.create_all()

# Authentication Decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            # Expected header format: "Bearer <token>"
            parts = request.headers['Authorization'].split()
            if len(parts) == 2:
                token = parts[1]
            else:
                token = parts[0]
                
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401
        
        current_user = User.query.filter_by(token=token).first()
        if not current_user:
            return jsonify({'error': 'Token is invalid!'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields (username, email, password)'}), 400
        
    if User.query.filter_by(username=data['username']).first() or User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'User with that username or email already exists'}), 400
        
    hashed_password = generate_password_hash(data['password'])
    new_user = User(username=data['username'], email=data['email'], password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'User created successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing username or password'}), 400
        
    user = User.query.filter_by(username=data['username']).first()
    
    if user and check_password_hash(user.password_hash, data['password']):
        # Generate a simple session token
        token = secrets.token_hex(32)
        user.token = token
        db.session.commit()
        return jsonify({'token': token, 'username': user.username}), 200
        
    return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/predict', methods=['POST'])
@token_required
def predict(current_user):
    if model is None:
        return jsonify({'error': 'Model is not loaded or not available'}), 500
        
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided in request'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Empty image field'}), 400
        
    try:
        # Preprocessing: load, resize to 224x224 RGB, normalize to 0-1
        image = Image.open(file).convert('RGB')
        
        # Save original file
        upload_id = str(uuid.uuid4())
        orig_filename = f"{upload_id}_orig.jpg"
        cam_filename = f"{upload_id}_cam.jpg"
        orig_path = os.path.join(app.static_folder, 'uploads', orig_filename)
        cam_path = os.path.join(app.static_folder, 'uploads', cam_filename)
        
        image.save(orig_path)
        
        image_resized = image.resize((224, 224))
        img_array = np.array(image_resized)
        img_array = img_array / 255.0
        
        # Add batch dimension
        img_array = np.expand_dims(img_array, axis=0)
        
        # Predict using DenseNet121 model
        prediction = model.predict(img_array)
        prob = float(prediction[0][0])
        
        # Grad-CAM
        last_conv = get_last_conv_layer(model)
        if last_conv:
            heatmap = make_gradcam_heatmap(img_array, model, last_conv)
            save_and_display_gradcam(orig_path, heatmap, cam_path)
        else:
            # Fallback if no conv layer found (should not happen on DenseNet)
            image.save(cam_path)

        # Interpretation: Class 0 = Healthy, Class 1 = Parkinson's (sigmoid output)
        if prob > 0.5:
            result = "Parkinson's"
            confidence = prob
        else:
            result = "Healthy"
            confidence = 1.0 - prob
            
        # Save history into DB with image URLs
        orig_url = f"/static/uploads/{orig_filename}"
        cam_url = f"/static/uploads/{cam_filename}"
        
        new_scan = ScanHistory(user_id=current_user.id, result=result, confidence=confidence, image_path=orig_url, heatmap_path=cam_url)
        db.session.add(new_scan)
        db.session.commit()
        
        return jsonify({
            'result': result,
            'confidence': confidence,
            'probability': prob,
            'image_path': orig_url,
            'heatmap_path': cam_url
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to process image and predict: {str(e)}'}), 500

@app.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "YOUR_DEEPSEEK_API_KEY_HERE":
        return jsonify({'error': 'DeepSeek API is not configured. Please paste your API key inside app.py.'}), 500
        
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({'error': 'No message provided'}), 400
        
    try:
        response = deepseek_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": data['message']}
            ],
            stream=False
        )
        return jsonify({'response': response.choices[0].message.content}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history', methods=['GET'])
@token_required
def history(current_user):
    try:
        scans = ScanHistory.query.filter_by(user_id=current_user.id).order_by(ScanHistory.timestamp.desc()).all()
        history_data = []
        for scan in scans:
            history_data.append({
                'id': scan.id,
                'result': scan.result,
                'confidence': scan.confidence,
                'image_path': scan.image_path,
                'heatmap_path': scan.heatmap_path,
                'timestamp': scan.timestamp.isoformat()
            })
        return jsonify({'history': history_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
