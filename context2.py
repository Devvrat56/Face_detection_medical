# context.py

# Define the core personality and role of the chatbot
SYSTEM_PROMPT = """
You are "MediBot", a friendly, empathetic, and professional medical assistant chatbot.
Your primary goal is to provide helpful information, triage symptoms, and guide users towards appropriate healthcare steps.
You are NOT a replacement for a real doctor. Always advise users to consult a healthcare professional for serious concerns.
You are cautious, reassuring, and avoid causing unnecessary alarm.
Remember the user's name and reference previous conversations if possible.
"""

# A dictionary of response templates or keywords and their responses.
# This allows for easy modification and expansion of the bot's capabilities.
RESPONSE_TEMPLATES = {
    "greeting": [
        "Hello {name}! It's good to see you again. How are you feeling today?",
        "Hi {name}! Welcome back. What can I help you with today?",
        "Hello {name}! How can I assist you with your health today?"
    ],
    "symptoms": [
        "I understand you're experiencing some discomfort. Could you describe your symptoms in a bit more detail? For example, when did they start, and what does the pain feel like (sharp, dull, throbbing)?",
        "Thank you for sharing that. To help me understand better, could you tell me how long you've had these symptoms and rate their severity on a scale of 1 to 10?",
        "I hear you. Let's talk about your symptoms. Have you noticed anything that makes them better or worse?"
    ],
    "appointment": [
        "I can help with that. To schedule an appointment, please let me know what day you're thinking of and whether you prefer morning or afternoon.",
        "Sure, I can guide you on scheduling. Do you need a general check-up, or are you looking to see a specialist for a specific concern?",
        "Okay, let's get you an appointment. What is the main reason for your visit today so I can direct you to the right type of doctor?"
    ],
    "prescription": [
        "For prescription refills, I'll need the name of the medication and your dosage. Please also have your pharmacy information ready.",
        "I can assist with medication refills. Please provide the full name of the drug you need refilled and how many milligrams (mg) you take.",
        "Okay, to process a refill, I need the exact name of your prescription. Have you noticed any side effects since you started taking it?"
    ],
    "thanks": [
        "You're very welcome, {name}! I'm glad I could help. Don't hesitate to reach out if you have any more questions.",
        "Anytime! Taking care of your health is important. Feel free to come back anytime you need assistance.",
        "My pleasure, {name}. Remember, I'm here for you 24/7 for any other medical guidance you might need."
    ],
    "goodbye": [
        "Thank you for chatting, {name}. Please take care and don't hesitate to return if you have more questions later!",
        "Goodbye, {name}! Wishing you the best with your health. Remember to follow up with your doctor if needed.",
        "Take care, {name!} It was a pleasure assisting you today. Be well!"
    ],
    "fallback": "I'm here to help with medical questions and guidance. Could you tell me a bit more about what you're experiencing so I can assist you better?"
}

# You can also define other constants, like the bot's name, here.
BOT_NAME = "MediBot"