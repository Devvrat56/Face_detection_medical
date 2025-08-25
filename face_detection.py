import streamlit as st
import face_recognition
import numpy as np
import os, json
from pymongo import MongoClient
from bson import Binary
import pickle
from datetime import datetime

# MongoDB Atlas connection using environment variable
def get_database():
    # Get connection string from environment variable
    CONNECTION_STRING = os.environ.get("connection_string")
    if not CONNECTION_STRING:
        st.error("MongoDB connection string not found in environment variables")
        st.stop()
    
    try:
        client = MongoClient(CONNECTION_STRING)
        # Test the connection
        client.admin.command('ping')
        return client['medical_chatbot_db']
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {str(e)}")
        st.stop()

# Load patient database from MongoDB
def load_db():
    db = get_database()
    patients_collection = db['patients']
    patients = list(patients_collection.find({}))
    
    # Convert to dictionary format similar to the original JSON structure
    patients_dict = {}
    for patient in patients:
        patient_id = patient['patient_id']
        # Convert Binary embeddings back to lists
        embeddings = [pickle.loads(emb) for emb in patient.get('embeddings', [])]
        patients_dict[patient_id] = {
            "name": patient['name'],
            "embeddings": embeddings,
            "created_at": patient.get('created_at', datetime.now())
        }
    
    return patients_dict

# Save patient to MongoDB
def save_to_db(patient_id, name, embedding):
    db = get_database()
    patients_collection = db['patients']
    
    # Convert embedding to Binary for storage
    embedding_binary = Binary(pickle.dumps(embedding.tolist(), protocol=2))
    
    # Check if patient already exists
    existing_patient = patients_collection.find_one({'patient_id': patient_id})
    
    if existing_patient:
        # Update existing patient with new embedding
        patients_collection.update_one(
            {'patient_id': patient_id},
            {'$push': {'embeddings': embedding_binary}}
        )
    else:
        # Insert new patient
        patient_data = {
            'patient_id': patient_id,
            'name': name,
            'embeddings': [embedding_binary],
            'created_at': datetime.now()
        }
        patients_collection.insert_one(patient_data)

# Extract face embedding from uploaded image
def get_embedding(uploaded_image):
    try:
        image = face_recognition.load_image_file(uploaded_image)
        encodings = face_recognition.face_encodings(image)
        return encodings[0] if encodings else None
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None

# Compare embeddings
def recognize_user(embedding, db):
    known_embeddings, ids = [], []
    for pid, pdata in db.items():
        for emb in pdata["embeddings"]:
            known_embeddings.append(np.array(emb))
            ids.append(pid)

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

# Load patient database
try:
    db = load_db()
except Exception as e:
    st.error(f"Error loading database: {str(e)}")
    st.stop()

uploaded_image = st.file_uploader("Upload your face image", type=["jpg", "jpeg", "png"])
name = st.text_input("Enter your name (if new user)")

if uploaded_image:
    emb = get_embedding(uploaded_image)
    if emb is None:
        st.error("No face detected in the image. Try another one.")
    else:
        user_id = recognize_user(emb, db)
        if user_id:
            st.success(f"✅ Welcome back {db[user_id]['name']} (ID: {user_id})")
            st.session_state.current_user = user_id
        else:
            if name:
                new_id = f"P{len(db)+1:03d}"
                # Save to MongoDB
                try:
                    save_to_db(new_id, name, emb)
                    st.success(f"🎉 New user registered: {name} (ID: {new_id})")
                    # Reload the database to include the new user
                    db = load_db()
                    st.session_state.current_user = new_id
                except Exception as e:
                    st.error(f"Error saving to database: {str(e)}")
            else:
                st.warning("Unknown user. Please enter your name to register.")

# Chatbot functionality
if st.button("Start Chatbot Conversation") and 'current_user' in st.session_state:
    st.session_state.chat_active = True
    st.session_state.chat_messages = [("Bot", "Hello! How can I help you today?")]

if st.session_state.chat_active:
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
        
        # Simple bot responses
        if "symptom" in user_input.lower():
            bot_response = "I understand you're describing symptoms. Can you tell me more about when they started?"
        elif "appointment" in user_input.lower():
            bot_response = "I can help you schedule an appointment. What day would work best for you?"
        elif "prescription" in user_input.lower():
            bot_response = "For prescription refills, please provide your medication name and dosage."
        elif "thank" in user_input.lower():
            bot_response = "You're welcome! Is there anything else I can help with?"
        else:
            bot_response = "I'm here to help with medical questions. Can you tell me more about your concern?"
        
        # Add bot response to chat
        st.session_state.chat_messages.append(("Bot", bot_response))
        st.rerun()

if st.button("End Conversation") and st.session_state.chat_active:
    st.session_state.chat_active = False
    st.success("Conversation ended. Restart and upload the same image to test recognition.")
    st.rerun()