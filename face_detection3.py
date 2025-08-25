import streamlit as st
import face_recognition
import numpy as np
import os
import json
import base64
from datetime import datetime
from PIL import Image
import io
import random
import context2  # Import our separate context file

# Create storage directory if it doesn't exist
STORAGE_DIR = "user_storage_2"
os.makedirs(STORAGE_DIR, exist_ok=True)

# Helper function to convert image to base64
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Helper function to save base64 as image
def base64_to_image(base64_str, output_path):
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as image_file:
        image_file.write(base64.b64decode(base64_str))

# Load all user data from storage
def load_all_users():
    users = {}
    if os.path.exists(STORAGE_DIR):
        for filename in os.listdir(STORAGE_DIR):
            if filename.endswith('.json'):
                user_id = filename[:-5]  # Remove .json extension
                try:
                    with open(os.path.join(STORAGE_DIR, filename), 'r') as f:
                        users[user_id] = json.load(f)
                except json.JSONDecodeError:
                    st.error(f"Error decoding {filename}. Skipping.")
    return users

# Save user data to storage
def save_user(user_id, name, embedding, image_path=None):
    # Convert embedding to list for JSON serialization
    embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else embedding
    
    user_data = {
        'user_id': user_id,
        'name': name,
        'embedding': embedding_list,
        'created_at': datetime.now().isoformat(),
        'conversations': []
    }
    
    # If image path is provided, convert image to base64 and store it
    if image_path and os.path.exists(image_path):
        user_data['image_base64'] = image_to_base64(image_path)
    
    # Save user data to JSON file
    with open(os.path.join(STORAGE_DIR, f'{user_id}.json'), 'w') as f:
        json.dump(user_data, f, indent=4)
    
    return user_data

# Add conversation to user's history
def add_conversation(user_id, messages):
    user_file = os.path.join(STORAGE_DIR, f'{user_id}.json')
    if os.path.exists(user_file):
        with open(user_file, 'r') as f:
            user_data = json.load(f)
        
        # Ensure conversations key exists
        if 'conversations' not in user_data:
            user_data['conversations'] = []
        
        user_data['conversations'].append({
            'timestamp': datetime.now().isoformat(),
            'messages': messages
        })
        
        with open(user_file, 'w') as f:
            json.dump(user_data, f, indent=4)
        return True
    return False

# Extract face embedding from uploaded image
def get_embedding(uploaded_image):
    # Save the uploaded image temporarily
    temp_path = os.path.join(STORAGE_DIR, 'temp_image.jpg')
    try:
        with open(temp_path, "wb") as f:
            f.write(uploaded_image.getbuffer())
        
        image = face_recognition.load_image_file(temp_path)
        encodings = face_recognition.face_encodings(image)
        
        if encodings:
            return encodings[0], temp_path
        else:
            return None, temp_path
            
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None, temp_path

# Compare embeddings for face recognition
def recognize_user(embedding, users_db):
    known_embeddings = []
    user_ids = []
    
    for user_id, user_data in users_db.items():
        if 'embedding' in user_data:
            try:
                known_embeddings.append(np.array(user_data['embedding']))
                user_ids.append(user_id)
            except Exception as e:
                st.error(f"Error loading embedding for user {user_id}: {e}")
                continue

    if not known_embeddings:
        return None

    try:
        # Compare the face embedding with all known embeddings
        matches = face_recognition.compare_faces(known_embeddings, embedding)
        face_distances = face_recognition.face_distance(known_embeddings, embedding)
        
        # Find the best match (lowest distance)
        if True in matches:
            best_match_index = np.argmin(face_distances)
            if face_distances[best_match_index] < 0.6:  # Threshold for face recognition
                return user_ids[best_match_index]
        
        return None
        
    except Exception as e:
        st.error(f"Error in face recognition: {str(e)}")
        return None

# Generate bot response based on context
def generate_bot_response(user_input, user_name):
    user_input_lower = user_input.lower()
    
    # Check for greetings
    if any(word in user_input_lower for word in ["hello", "hi", "hey", "hola"]):
        return random.choice(context2.RESPONSE_TEMPLATES["greeting"]).format(name=user_name)
    
    # Check for symptoms
    elif any(word in user_input_lower for word in ["symptom", "pain", "hurt", "headache", "fever", 
                                                 "nausea", "dizzy", "cough", "cold", "ache"]):
        return random.choice(context2.RESPONSE_TEMPLATES["symptoms"])
    
    # Check for appointments
    elif any(word in user_input_lower for word in ["appointment", "schedule", "doctor", "see a", "meeting"]):
        return random.choice(context2.RESPONSE_TEMPLATES["appointment"])
    
    # Check for prescriptions
    elif any(word in user_input_lower for word in ["prescription", "medication", "refill", "pill", "medicine", "drug"]):
        return random.choice(context2.RESPONSE_TEMPLATES["prescription"])
    
    # Check for thanks
    elif any(word in user_input_lower for word in ["thank", "thanks", "thank you", "appreciate"]):
        return random.choice(context2.RESPONSE_TEMPLATES["thanks"]).format(name=user_name)
    
    # Check for goodbye
    elif any(word in user_input_lower for word in ["bye", "goodbye", "end", "quit", "exit", "see you"]):
        return random.choice(context2.RESPONSE_TEMPLATES["goodbye"]).format(name=user_name)
    
    # Fallback response
    else:
        return context2.RESPONSE_TEMPLATES["fallback"]

# ------------------- Streamlit App -------------------

st.set_page_config(page_title="Medical Chatbot", page_icon="🩺", layout="wide")

st.title("🩺 Medical Chatbot with Face Recognition")

# Initialize session state
if 'chat_active' not in st.session_state:
    st.session_state.chat_active = False
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'user_recognized' not in st.session_state:
    st.session_state.user_recognized = False
if 'users_db' not in st.session_state:
    st.session_state.users_db = load_all_users()

# Use the session state version of the DB
users_db = st.session_state.users_db

# Sidebar for user management
with st.sidebar:
    st.header("User Authentication")
    
    uploaded_image = st.file_uploader("Upload your face image", type=["jpg", "jpeg", "png"], key="image_uploader")
    name = st.text_input("Enter your name (if new user)", key="name_input")
    
    process_image = st.button("Process Image & Login/Register", type="primary")

# Main content area
col1, col2 = st.columns([1, 2])

with col1:
    st.header("Face Recognition")
    
    if process_image and uploaded_image:
        with st.spinner("Processing image and recognizing face..."):
            embedding, temp_image_path = get_embedding(uploaded_image)
            
            if embedding is None:
                st.error("❌ No face detected in the image. Please try another image.")
            else:
                user_id = recognize_user(embedding, users_db)
                
                if user_id:
                    st.session_state.current_user = user_id
                    st.session_state.user_recognized = True
                    user_data = users_db[user_id]
                    st.success(f"✅ Welcome back {user_data['name']}!")
                    
                    # Display user profile
                    if 'image_base64' in user_data:
                        try:
                            image_data = base64.b64decode(user_data['image_base64'])
                            image = Image.open(io.BytesIO(image_data))
                            st.image(image, caption="Your Profile Image", use_column_width=True)
                        except:
                            st.warning("Could not load profile image.")
                    
                    # Start fresh conversation
                    welcome_msg = random.choice(context2.RESPONSE_TEMPLATES["greeting"]).format(name=user_data['name'])
                    st.session_state.chat_messages = [("Bot", welcome_msg)]
                    
                else:
                    if name:
                        new_id = f"user_{len(users_db) + 1}_{datetime.now().strftime('%H%M%S')}"
                        save_user(new_id, name, embedding, temp_image_path)
                        st.success(f"🎉 New user registered: {name}")
                        
                        # Reload the database
                        st.session_state.users_db = load_all_users()
                        users_db = st.session_state.users_db
                        st.session_state.current_user = new_id
                        st.session_state.user_recognized = True
                        
                        # Start welcome conversation
                        welcome_msg = f"Hello {name}! I'm {context2.BOT_NAME}, your medical assistant. How can I help you today?"
                        st.session_state.chat_messages = [("Bot", welcome_msg)]
                        
                    else:
                        st.warning("⚠️ Unknown user. Please enter your name to register.")
        
        # Clean up temporary file
        if 'temp_image_path' in locals() and os.path.exists(temp_image_path):
            os.remove(temp_image_path)

with col2:
    st.header("Chat with MediBot")
    
    if st.session_state.user_recognized and st.session_state.current_user:
        user_data = users_db[st.session_state.current_user]
        
        # Display chat messages
        chat_container = st.container()
        with chat_container:
            for sender, message in st.session_state.chat_messages:
                if sender == "Bot":
                    st.chat_message("assistant").markdown(f"**{context2.BOT_NAME}:** {message}")
                else:
                    st.chat_message("user").markdown(f"**You:** {message}")
        
        # Chat input
        user_input = st.chat_input("Type your message here...")
        
        if user_input:
            # Add user message to chat
            st.session_state.chat_messages.append(("You", user_input))
            
            # Generate and add bot response
            bot_response = generate_bot_response(user_input, user_data['name'])
            st.session_state.chat_messages.append(("Bot", bot_response))
            
            st.rerun()
        
        # Conversation management buttons
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 Save Conversation", help="Save this conversation to your history"):
                if add_conversation(st.session_state.current_user, st.session_state.chat_messages):
                    st.success("Conversation saved successfully!")
                    st.session_state.users_db = load_all_users()
                else:
                    st.error("Could not save conversation.")
        
        with col_btn2:
            if st.button("🔄 New Conversation", help="Start a fresh conversation"):
                welcome_msg = random.choice(context2.RESPONSE_TEMPLATES["greeting"]).format(name=user_data['name'])
                st.session_state.chat_messages = [("Bot", welcome_msg)]
                st.rerun()
    
    else:
        st.info("👆 Please upload your face image and authenticate to start chatting with MediBot.")

# Display conversation history in sidebar
if st.session_state.user_recognized and st.session_state.current_user:
    user_data = users_db[st.session_state.current_user]
    
    with st.sidebar:
        st.divider()
        st.subheader("Conversation History")
        
        if 'conversations' in user_data and user_data['conversations']:
            for i, conv in enumerate(reversed(user_data['conversations'])):
                date_str = datetime.fromisoformat(conv['timestamp']).strftime("%b %d, %Y %H:%M")
                if st.button(f"🗨️ {date_str}", key=f"hist_{i}"):
                    st.session_state.chat_messages = conv['messages']
                    st.rerun()
        else:
            st.write("No previous conversations yet.")