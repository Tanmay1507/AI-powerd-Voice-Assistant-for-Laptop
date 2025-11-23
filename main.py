import os
import threading
from time import sleep
import webbrowser
import datetime
import logging
import customtkinter as ctk
import speech_recognition as sr
import pyttsx3
import pyautogui
import psutil
import requests
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import wikipedia
import random
import math
import pyjokes 


# --- Load Environment Variables for Security ---
load_dotenv()

# --- GLOBAL CONFIGURATION & SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 🛑 ACTION REQUIRED (STEP 1): Change this index for your Dell microphone 🛑
# Run the `check_mics.py` script I gave you to find the correct number for your Dell's microphone.
# It is probably 1 or 2, but you must check.
MIC_DEVICE_INDEX = 0 

# --- Gemini API Setup ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
if not GEMINI_API_KEY:
    logging.error("GEMINI_API_KEY not found. AI chat will not work.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# --- News API Setup ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
if not NEWS_API_KEY:
    logging.warning("NEWS_API_KEY not found. News functionality will be disabled.")


# --- Main Application Class ---
class JarvisApp:
    def __init__(self, root_widget):
        """Initializes the GUI, TTS engine, and core components."""
        self.root = root_widget
        self.root.title("AI Voice Assistant")
        self.root.geometry("900x700")

        self.driver = None  
        self.jarvis_thread = None
        self.stop_jarvis_event = threading.Event()
        self.pulse_job = None 
        
        # --- NEW: Speaking/Interrupt Flags ---
        self.is_speaking = False
        self.speak_thread = None

        self.status_light = None 
        self.listening_color = "#e74c3c" # Start as Red (Off)

        # 🛑 ACTION REQUIRED (STEP 2): Update "YourUsername" to your Dell laptop's Windows username 🛑
        # Find your username by opening File Explorer and going to "C:\Users\"
        # Change "YourUsername" below to match your folder name (e.g., "C:\\Users\\tanmaydell\\...")
        self.software_paths = {
            "visual studio code": "C:\\Users\\YourUsername\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
            "vscode": "C:\\Users\\YourUsername\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
            "notepad": "C:\\Windows\\System32\\notepad.exe",
            "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        }

        # --- Text-to-Speech Engine Setup ---
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 180)
            self.engine.setProperty('volume', 1.0)
            voices = self.engine.getProperty('voices')
            if len(voices) > 1:
                # You can change voices[1].id to voices[0].id to try the other default voice
                self.engine.setProperty('voice', voices[1].id) 
        except Exception as e:
            logging.error(f"Failed to initialize TTS engine: {e}")
            self.engine = None

        self._setup_gui()
        self.set_status_color(self.listening_color) 

    # --- EMOTION/TTS METHODS ---
    
    def speak_interruptible(self, text):
        """
        Handles the actual, non-blocking TTS. 
        It stops any ongoing speech before starting a new one.
        """
        if not self.engine:
            self.update_log("Error: TTS engine not initialized.")
            return

        # 1. Ensure any previous speech is stopped immediately
        self.stop_speech()

        # 2. Define the TTS task
        def tts_task():
            self.is_speaking = True
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                logging.error(f"TTS thread error: {e}")
            finally:
                self.is_speaking = False
                
        # 3. Execute the TTS task in a new thread
        self.update_log(f"Jarvis 🎧: {text}")
        self.speak_thread = threading.Thread(target=tts_task)
        self.speak_thread.daemon = True
        self.speak_thread.start()

    def stop_speech(self):
        """Stops the current TTS output immediately."""
        if self.engine and self.is_speaking:
            # pyttsx3.Engine.stop() is thread-safe for stopping speech
            self.engine.stop() 
            self.is_speaking = False
            if self.speak_thread and self.speak_thread.is_alive():
                # Wait briefly for the thread to clean up
                self.speak_thread.join(timeout=0.1) 
            self.update_log("Jarvis: Interrupted/Stopped talking.")


    def speak(self, text):
        """Standard method for text-to-speech."""
        if self.engine:
            self.speak_interruptible(text)
        else:
            self.update_log(f"Jarvis 🎧: {text}")

    def speak_emotionally(self, text, emotion="normal"):
        """
        Modulates speech rate and volume to simulate emotion, then calls the interruptible speak method.
        """
        if not self.engine:
            self.speak(text) 
            return

        original_rate = 180 
        original_volume = 1.0 

        if emotion == "excited":
            self.engine.setProperty('rate', original_rate + 40) 
            self.engine.setProperty('volume', 1.0) 
        elif emotion == "happy":
            self.engine.setProperty('rate', original_rate + 20) 
            self.engine.setProperty('volume', 1.0) 
        elif emotion == "worry":
            self.engine.setProperty('rate', original_rate - 40) 
            self.engine.setProperty('volume', 0.65) 
        else: # normal
            self.engine.setProperty('rate', original_rate) 
            self.engine.setProperty('volume', original_volume)

        # Use the non-blocking speak method
        self.speak_interruptible(text)

        # Reset engine properties (these reset before the speech finishes, but will apply to the NEXT speak)
        self.engine.setProperty('rate', 180)
        self.engine.setProperty('volume', 1.0)


    # --- GUI & ANIMATION METHODS ---
    def set_status_color(self, color_hex):
        """Changes the color of the status indicator light (thread-safe)."""
        if self.status_light:
            self.root.after(0, lambda: self.status_light.itemconfig(self.status_circle, fill=color_hex, outline=color_hex))

    def animate_status_pulse(self, step=0):
        """Recursively animates the status light (pulsing yellow) when ready for a command."""
        if self.stop_jarvis_event.is_set():
            return
        
        brightness = int(220 + 35 * math.sin(step / 30 * math.pi * 2)) 
        hex_color = f'#ff{brightness:02x}00' 
        
        self.set_status_color(hex_color)
        
        next_step = (step + 1) % 60
        self.pulse_job = self.root.after(25, lambda: self.animate_status_pulse(next_step))

    def stop_status_pulse(self):
        """Stops the recursive animation job."""
        if hasattr(self, 'pulse_job') and self.pulse_job is not None:
            self.root.after_cancel(self.pulse_job)
            self.pulse_job = None
    
    def _setup_gui(self):
        """Creates and configures the graphical user interface."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue") 

        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        title = ctk.CTkLabel(main_frame, text="AI Voice Assistant", font=("Arial", 32, "bold"), text_color="#E0E0E0")
        title.pack(pady=(20, 10))

        self.status_light = ctk.CTkCanvas(main_frame, width=20, height=20, bg="#2b2b2b", highlightthickness=0)
        self.status_circle = self.status_light.create_oval(5, 5, 15, 15, fill=self.listening_color, outline=self.listening_color)
        self.status_light.pack(pady=(0, 10))

        self.log_box = ctk.CTkTextbox(main_frame, font=("Consolas", 14), state="disabled", wrap="word", fg_color="#1e1e1e") 
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=20, fill="x", padx=10)

        self.start_btn = ctk.CTkButton(
            button_frame, text="Start Listening", command=self.start_jarvis_thread, 
            width=200, height=40, font=("Helvetica", 14, "bold"),
            fg_color="#2ecc71", hover_color="#27ae60" 
        )
        self.start_btn.pack(side="left", expand=True, padx=10)

        self.stop_btn = ctk.CTkButton(
            button_frame, text="Stop Listening", command=self.stop_jarvis, 
            width=200, height=40, font=("Helvetica", 14, "bold"), 
            state="disabled", fg_color="#e74c3c", hover_color="#c0392b"
        )
        self.stop_btn.pack(side="right", expand=True, padx=10)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_log(self, message):
        """Thread-safe method to update the GUI log box and console."""
        def _update():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", message + "\n")
            self.log_box.configure(state="disabled")
            self.log_box.see("end")
            logging.info(message) 
        self.root.after(0, _update)

    def take_command(self):
        """Listens for voice commands using the correct microphone device."""
        if self.stop_jarvis_event.is_set():
              return "stop"
              
        recognizer = sr.Recognizer()
        
        try:
            # Stop speaking so the microphone can listen cleanly
            self.stop_speech()
            
            with sr.Microphone(device_index=MIC_DEVICE_INDEX) as source:
                self.update_log(f"🎤 Listening on device {MIC_DEVICE_INDEX}...")
                recognizer.pause_threshold = 1.0
                recognizer.adjust_for_ambient_noise(source, duration=1)
                
                self.stop_status_pulse()
                self.set_status_color("#3498db") # Solid blue for listening
                
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            self.animate_status_pulse() # Restart pulse after listening attempt
            
        except ValueError:
            self.speak_emotionally("Error: Microphone index is incorrect. Please check MIC_DEVICE_INDEX in the code.", "worry")
            self.stop_status_pulse()
            return "None"
        except sr.WaitTimeoutError:
            self.update_log("Timeout waiting for speech.")
            self.animate_status_pulse()
            return "None"
        except Exception as e:
            self.speak_emotionally(f"Microphone error. Is PyAudio installed correctly? Error: {e}", "wory")
            self.stop_status_pulse()
            return "None"

        try:
            self.update_log("🧠 Recognizing...")
            query = recognizer.recognize_google(audio, language='en-in')
            self.update_log(f"🗣️ You said: {query}")
            return query.lower()
        except sr.UnknownValueError:
            print("Sorry, I didn't catch that. Please try again.", "worry")
            return "None"
        except sr.RequestError as e:
            self.speak_emotionally(f"Network error: {e}", "worry")
            return "None"

    # --- Utility and Command Functions ---
    
    def control_volume(self, action):
        """Controls system volume using pyautogui key presses."""
        try:
            if action == "increase":
                self.speak("Turning up the volume.")
                # Press the Volume Up key 5 times for a noticeable increase
                for _ in range(5):
                    pyautogui.press('volumeup')
            elif action == "decrease":
                self.speak("Turning down the volume.")
                # Press the Volume Down key 5 times
                for _ in range(5):
                    pyautogui.press('volumedown')
            elif action == "mute":
                self.speak("Muting the system.")
                pyautogui.press('volumemute')
            elif action == "unmute":
                self.speak("Unmuting the system.")
                pyautogui.press('volumemute') # Pressing it again toggles mute off
            else:
                self.speak_emotionally(f"Sorry, I don't know how to {action} the volume.", "worry")
        except Exception as e:
            self.speak_emotionally(f"I ran into an error trying to change the volume: {e}", "worry")
            
    # ... (other utility functions remain the same) ...

    def _init_chrome(self):
        """Initializes and returns a single, reusable Chrome browser instance."""
        if not self.driver:
            try:
                self.speak("Opening browser...")
                options = webdriver.ChromeOptions()
                options.add_argument("--start-maximized")
                options.add_argument("--log-level=3") 
                options.add_experimental_option("excludeSwitches", ["enable-logging"])
                self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            except Exception as e:
                self.speak_emotionally(f"Failed to open Chrome. Ensure Chrome is installed and updated: {e}", "worry")
                self.driver = None
        return self.driver
    
    def search_google(self, topic):
        """Uses Selenium to search Google in the running browser instance."""
        driver = self._init_chrome()
        if driver:
            try:
                self.speak(f"Searching Google for {topic}")
                driver.get("https.www.google.com/search?q=" + topic)
            except Exception as e:
                self.speak_emotionally(f"Failed to perform Google search: {e}", "worry")
                
    def get_news_headlines(self):
        """Fetches and speaks the top 3 news headlines using the News API."""
        global NEWS_API_KEY
        if not NEWS_API_KEY:
            self.speak_emotionally("News API key is not configured, sir.", "worry")
            return
        
        try:
            self.speak("Fetching the top news headlines for you.")
            url = f"https{os.getenv('NEWS_API_URL')}?country=us&apiKey={NEWS_API_KEY}" 
            
            response = requests.get(url, timeout=10)
            response.raise_for_status() 
            data = response.json()
            
            if data['status'] == 'ok' and data['totalResults'] > 0:
                headlines = [article['title'] for article in data['articles'][:3]]
                
                news_text = "Today's top headlines are: "
                for i, headline in enumerate(headlines):
                    clean_headline = headline.split(' - ')[0].replace(' | Reuters', '')
                    news_text += f"Number {i+1}. {clean_headline}. "
                
                self.speak_emotionally(news_text, "excited")
            else:
                self.speak_emotionally("I apologize, I couldn't find any recent news.", "worry")

        except requests.exceptions.RequestException as e:
            self.speak_emotionally(f"A network error occurred while fetching news: {e}", "worry")
        except Exception as e:
            self.speak_emotionally(f"An unexpected error occurred with the news feature: {e}", "worry")


    def close_browser(self):
        if self.driver:
            self.speak("Closing the browser.")
            self.driver.quit()
            self.driver = None
            
    def open_software(self, software_name):
        """Robustly opens a software application based on a predefined path."""
        path = self.software_paths.get(software_name.lower().strip())
        
        if path and os.path.exists(path):
            try:
                self.speak_emotionally("Launching application now, sir.", "happy") 
                os.startfile(path)
            except Exception as e:
                self.speak_emotionally(f"Sorry, I encountered an error while trying to open {software_name}: {e}", "worry")
        elif path:
              self.speak_emotionally(f"The file path for {software_name} is configured but the file does not exist. Please check your software paths.", "worry")
        else:
            self.speak(f"Sorry, I don't have a configured path for {software_name}.")

    def get_wikipedia_summary(self, topic):
        """Fetches and speaks a summary from Wikipedia."""
        try:
            self.speak("Searching Wikipedia...")
            summary = wikipedia.summary(topic, sentences=2, auto_suggest=True)
            self.speak_emotionally(f"According to Wikipedia: {summary}")
        except wikipedia.exceptions.PageError:
            self.speak_emotionally(f"Sorry, I couldn't find anything on Wikipedia about {topic}.", "worry")
        except Exception as e:
            self.speak_emotionally(f"An error occurred while accessing Wikipedia: {e}", "worry")

    def tell_joke(self):
        """Tells a random joke using the pyjokes library."""
        self.speak_emotionally(pyjokes.get_joke(), "happy")
        
    def ai_chat(self, prompt, speak_response=True):
        """
        Uses Google Gemini to generate a response.
        """
        global GEMINI_API_KEY 
        if not GEMINI_API_KEY:
            error_msg = "Gemini API key is not configured."
            self.speak_emotionally(error_msg, "worry")
            return error_msg
            
        try:
            # self.speak("Getting a quick response from Gemini...")
            
            system_prompt = "You are a helpful, brief, and concise voice assistant named Jarvis. Acting like best friend . My name is Tanmay"
            
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash", # Using 1.5-flash for speed
                system_instruction=system_prompt 
            ) 
            
            response = model.generate_content(
                contents=[prompt]
            )
            
            if speak_response:
                self.speak_emotionally(response.text)
                return None
            else:
                return response.text
                
        except Exception as e:
            error_msg = f"An error occurred with the Gemini API: {e}. Please check your internet connection and API key."
            self.speak_emotionally(error_msg, "worry")
            return error_msg
            
    # --- Main Jarvis Loop ---
    def run_jarvis(self):
        """The main loop that listens for and processes commands."""
        hour = datetime.datetime.now().hour
        greeting = "Good Morning sir!" if 0 <= hour < 12 else ("Good Afternoon sir!" if 12 <= hour < 18 else "Good Evening sir!")
        
        self.speak_emotionally(f"{greeting} I am Jarvis. How can I assist you today?", "excited")

        self.animate_status_pulse() 

        while not self.stop_jarvis_event.is_set():
            query = self.take_command()

            if query in ["None", "stop"]:
                continue
            
            # --- NEW: INTERRUPT COMMAND ---
            if "cancel" in query or "stop talking" in query or "interrupt" in query:
                self.stop_speech()
                self.speak("Command canceled. What's next?")
                continue # Go back to the top of the loop to listen again
            
            # --- Volume Controls ---
            elif "volume up" in query or "turn up the volume" in query:
                self.control_volume("increase")
            elif "volume down" in query or "turn down the volume" in query:
                self.control_volume("decrease")
            elif "mute" in query or "silence" in query:
                self.control_volume("mute")
            elif "unmute" in query:
                self.control_volume("unmute")
            
            # --- Navigation & Searching ---
            elif "open youtube" in query:
                self.speak("Opening YouTube")
                webbrowser.open("https://youtube.com")
            
            elif "search google for" in query:
                topic = query.replace("search google for", "").strip()
                self.search_google(topic)
                
            elif "open gmail" in query:
                self.speak("Opening Gmail")
                webbrowser.open("https://mail.google.com/")
            
            elif "what's the news" in query or "read the news" in query:
                self.get_news_headlines()
                
            elif query.startswith("open ") or query.startswith("start "):
                software_name = query.replace("open ", "").replace("start ", "").replace("jarvis ", "").strip()
                self.open_software(software_name)

            # --- Information and Fun Commands ---
            elif "wikipedia" in query:
                topic = query.split("wikipedia", 1)[-1].strip()
                if topic:
                    self.get_wikipedia_summary(topic)
            elif "joke" in query:
                self.tell_joke()
            elif "time" in query:
                current_time = datetime.datetime.now().strftime("%I:%M %p")
                self.speak(f"The current time is {current_time}")

           

            # --- Control Commands ---
            elif "exit" in query or "quit" in query:
                self.speak("Goodbye, sir! Have a great day.")
                self.stop_jarvis()
                break
                
            # --- General Query (Fallback to AI) ---
            # Updated logic to better catch general queries
            elif len(query.split()) > 2 or not any(kw in query for kw in ["open", "search", "wikipedia", "news", "volume", "mute", "joke", "time"]):
                reply = self.ai_chat(query, speak_response=False)
                if reply:
                    self.speak_emotionally(reply) 
            
            else:
                # This fallback might be reached less often with the improved logic above
                self.speak_emotionally("I'm not sure how to handle that command. Please be more specific.", "worry")


        self.stop_status_pulse() 
        self.close_browser()
        self.root.after(0, self.reset_gui)

    def start_jarvis_thread(self):
        """Starts the Jarvis main loop in a separate thread to keep the GUI responsive."""
        self.start_btn.configure(state="disabled", text="Initializing...") 
        self.stop_btn.configure(state="normal")
        self.stop_jarvis_event.clear()
        self.jarvis_thread = threading.Thread(target=self.run_jarvis, daemon=True)
        self.jarvis_thread.start()

    def stop_jarvis(self):
        """Stops the Jarvis thread safely."""
        self.stop_speech() # Ensure all speech stops
        if self.jarvis_thread and self.jarvis_thread.is_alive():
            self.update_log("Stopping Jarvis...")
            self.stop_jarvis_event.set()
        
        self.stop_status_pulse() 
        
    def reset_gui(self):
        """Resets the GUI buttons to their initial state."""
        self.start_btn.configure(state="normal", text="Start Listening") 
        self.stop_btn.configure(state="disabled")
    
    def on_closing(self):
        """Handles the application closing event."""
        self.stop_jarvis()
        sleep(0.5) 
        self.root.destroy()


# --- Main Execution ---
if __name__ == "__main__":
    root = ctk.CTk()
    app = JarvisApp(root)
    root.mainloop()