import streamlit as st
import face_recognition
import numpy as np
import os, json
import base64
from datetime import datetime

# Create storage directory if it doesn't exist
STORAGE_DIR = "user_storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

# Helper function to convert image to base64
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Helper function to save base64 as image
def base64_to_image(base64_str, output_path):
    with open(output_path, "wb") as image_file:
        image_file.write(base64.b64decode(base64_str))

# Load all user data from storage
def load_all_users():
    users = {}
    if os.path.exists(STORAGE_DIR):
        for filename in os.listdir(STORAGE_DIR):
            if filename.endswith('.json'):
                user_id = filename[:-5]  # Remove .json extension
                with open(os.path.join(STORAGE_DIR, filename), 'r') as f:
                    users[user_id] = json.load(f)
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
        
        user_data['conversations'].append({
            'timestamp': datetime.now().isoformat(),
            'messages': messages
        })
        
        with open(user_file, 'w') as f:
            json.dump(user_data, f, indent=4)

# Extract face embedding from uploaded image
def get_embedding(uploaded_image):
    # Save the uploaded image temporarily
    temp_path = os.path.join(STORAGE_DIR, 'temp_image.jpg')
    with open(temp_path, "wb") as f:
        f.write(uploaded_image.getbuffer())
    
    try:
        image = face_recognition.load_image_file(temp_path)
        encodings = face_recognition.face_encodings(image)
        return encodings[0] if encodings else None, temp_path
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None, temp_path

# Compare embeddings
def recognize_user(embedding, users_db):
    known_embeddings, ids = [], []
    for user_id, user_data in users_db.items():
        if 'embedding' in user_data:
            known_embeddings.append(np.array(user_data['embedding']))
            ids.append(user_id)

    if not known_embeddings:
        return None

    matches = face_recognition.compare_faces(known_embeddings, embedding)
    dist = face_recognition.face_distance(known_embeddings, embedding)

    if True in matches:
        match_index = np.argmin(dist)
        return ids[match_index]
    return None

# ------------------- Streamlit App -------------------

st.title("🩺 Medical Chatbot with Face Recognition")

# Initialize session state for chat
if 'chat_active' not in st.session_state:
    st.session_state.chat_active = False
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# Load all users
users_db = load_all_users()

uploaded_image = st.file_uploader("Upload your face image", type=["jpg", "jpeg", "png"])
name = st.text_input("Enter your name (if new user)")

if uploaded_image:
    emb, temp_image_path = get_embedding(uploaded_image)
    if emb is None:
        st.error("No face detected in the image. Try another one.")
    else:
        user_id = recognize_user(emb, users_db)
        if user_id:
            st.success(f"✅ Welcome back {users_db[user_id]['name']} (ID: {user_id})")
            st.session_state.current_user = user_id
            # Load any previous conversations
            if 'conversations' in users_db[user_id]:
                st.sidebar.subheader("Previous Conversations")
                for i, conv in enumerate(users_db[user_id]['conversations']):
                    if st.sidebar.button(f"Conversation {i+1} - {conv['timestamp'][:10]}", key=f"conv_{i}"):
                        st.session_state.chat_messages = conv['messages']
        else:
            if name:
                new_id = f"user_{len(users_db) + 1}"
                # Save new user
                save_user(new_id, name, emb, temp_image_path)
                st.success(f"🎉 New user registered: {name} (ID: {new_id})")
                # Reload the database to include the new user
                users_db = load_all_users()
                st.session_state.current_user = new_id
            else:
                st.warning("Unknown user. Please enter your name to register.")
    
    # Clean up temporary image
    if os.path.exists(temp_image_path):
        os.remove(temp_image_path)

# Chatbot functionality
if st.button("Start Chatbot Conversation") and st.session_state.current_user:
    st.session_state.chat_active = True
    st.session_state.chat_messages = [("Bot", "Hello! How can I help you today?")]

if st.session_state.chat_active and st.session_state.current_user:
    st.subheader("Chat with Medical Bot")
    
    # Display chat messages
    for sender, message in st.session_state.chat_messages:
        if sender == "Bot":
            st.info(f"💬 {sender}: {message}")
        else:
            st.write(f"👤 {sender}: {message}")
    
    # Chat input
    user_input = st.text_input("Your message:", key="chat_input")
    if user_input:
        # Add user message to chat
        st.session_state.chat_messages.append(("You", user_input))
        
        # Simple bot responses based on keywords
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ["hello", "hi", "hey"]):
            bot_response = "Hello! How can I assist you with your medical concerns today?"
        elif any(word in user_input_lower for word in ["symptom", "pain", "hurt"]):
            bot_response = "I understand you're describing symptoms. Can you tell me more about when they started and how severe they are?"
        elif any(word in user_input_lower for word in ["appointment", "schedule"]):
            bot_response = "I can help you schedule an appointment. What day would work best for you?"
        elif any(word in user_input_lower for word in ["prescription", "medication", "refill"]):
            bot_response = "For prescription refills, please provide your medication name and dosage."
        elif any(word in user_input_lower for word in ["thank", "thanks"]):
            bot_response = "You're welcome! Is there anything else I can help with?"
        elif any(word in user_input_lower for word in ["bye", "goodbye", "end"]):
            bot_response = "Thank you for chatting. Feel free to return if you have more questions. Take care!"
        else:
            bot_response = "I'm here to help with medical questions. Can you tell me more about your concern?"
        
        # Add bot response to chat
        st.session_state.chat_messages.append(("Bot", bot_response))
        st.rerun()

if st.button("End Conversation") and st.session_state.chat_active and st.session_state.current_user:
    # Save conversation before ending
    add_conversation(st.session_state.current_user, st.session_state.chat_messages)
    st.session_state.chat_active = False
    st.success("Conversation saved. Restart and upload the same image to continue later.")
    st.session_state.chat_messages = []
    st.rerun()

# Display user's image if available
if st.session_state.current_user and st.session_state.current_user in users_db:
    user_data = users_db[st.session_state.current_user]
    if 'image_base64' in user_data:
        # Display the user's image
        st.sidebar.subheader("Your Profile Image")
        st.sidebar.image(base64_to_image(user_data['image_base64'], os.path.join(STORAGE_DIR, "display_temp.jpg")), 
                         use_column_width=True)
        
        # Clean up temporary display image
        if os.path.exists(os.path.join(STORAGE_DIR, "display_temp.jpg")):
            os.remove(os.path.join(STORAGE_DIR, "display_temp.jpg"))