
# 🗣️ Jarvis: AI Voice Assistant (CustomTkinter, Gemini, TTS)

## Project Overview

**Jarvis** is a powerful, desktop-based AI Voice Assistant built entirely in Python. It features a modern, dark-themed GUI using CustomTkinter and operates on a multi-threaded architecture to ensure the interface remains responsive while the assistant listens for commands or generates responses.

The core strength of Jarvis lies in its deep integration with system utilities, web automation, and Google's advanced **Gemini AI** for conversational intelligence.

### Key Features ✨

  * **🎙️ Voice Command & Interruption:** Uses the `speech_recognition` library to process voice input. Features non-blocking, interruptible speech, allowing the user to say "cancel" or "stop talking" at any time.
  * **🧠 Generative AI:** Integrated with the **Gemini 1.5 Flash API** to handle complex, conversational, and factual queries beyond simple commands.
  * **💡 Emotional TTS:** Modulates the speech rate and volume using `pyttsx3` to convey different tones (e.g., *excited* greetings, *worried* error reports).
  * **⚙️ System Control:** Control system volume (`pyautogui`) and launch applications (VS Code, Chrome, Notepad) directly from voice commands.
  * **🌐 Web Automation:** Uses **Selenium** for controlled browsing, enabling precise Google searches and maintaining a persistent browser session.
  * **📰 Information Retrieval:** Fetch and read the latest global news headlines (News API) and summarize topics from Wikipedia.

-----

## 🛠️ Setup and Installation

### Prerequisites

  * Python 3.x
  * A stable internet connection (required for Gemini, Speech Recognition, and News APIs)

### Step 1: Clone the Repository & Install Dependencies

Clone this repository and install all required Python libraries.

```bash
git clone [YOUR_REPO_URL]
cd [REPO_FOLDER_NAME]
pip install -r requirements.txt
```

### Step 2: API Configuration

The assistant relies on two external APIs. Create a file named **`.env`** in the root directory of the project and add your confidential keys:

| Variable | Source | Purpose |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) | Powers the `ai_chat` conversational feature. |
| `NEWS_API_KEY` | [News API](https://newsapi.org/) | Fetches live global headlines. |
| `NEWS_API_URL` | *(Pre-set)* | The API endpoint for fetching news. |

**`.env` Example:**

```ini
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
NEWS_API_KEY="YOUR_NEWS_API_KEY_HERE"
NEWS_API_URL="://newsapi.org/v2/top-headlines"
```

### Step 3: Local Code Configuration ⚠️

You **must** modify the Python file (`your_main_file_name.py`) to align with your local system.

1.  **Microphone Index:** Find and set the correct device index for your primary microphone in the global configuration section.

    ```python
    # Change this index to match your system's microphone device number
    MIC_DEVICE_INDEX = 0
    ```

2.  **Software Paths:** Update the paths within the `JarvisApp.__init__` method to match your Windows username and installation locations.

    ```python
    # Update "YourUsername" to your actual Windows username
    self.software_paths = {
        "visual studio code": "C:\\Users\\YourUsername\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
        # ... (update other paths as necessary)
    }
    ```

-----

## ▶️ Usage

1.  Ensure all setup steps are complete.

2.  Run the application:

    ```bash
    python your_main_file_name.py
    ```

3.  Click the **"Start Listening"** button. The central status light will begin **pulsing yellow** when Jarvis is passively waiting for a command.

### Example Voice Commands

| Category | Example Commands |
| :--- | :--- |
| **Information** | "What time is it?" / "Tell me a joke" / "What's the news?" |
| **Web Search** | "Search Google for the latest stock prices" / "Open YouTube" / "Open Gmail" |
| **System Control** | "Volume up" / "Mute the system" |
| **Application Launch** | "Open Visual Studio Code" / "Start Chrome" / "Open Notepad" |
| **AI Chat** | "What is the largest moon in the solar system?" / "Explain quantum computing to me." |
| **Control** | "Stop talking" / "Cancel" / "Exit" |

-----

## 💻 Technical Architecture Highlights

| Component | Responsibility | Implementation Details |
| :--- | :--- | :--- |
| **GUI & Threading** | Keeps the UI responsive while voice processing runs. | Uses **`threading.Thread`** for the `run_jarvis` loop, preventing GUI freezes. |
| **Emotional Speech** | Adds personality by altering voice parameters. | **`speak_emotionally`** adjusts `pyttsx3` properties (`rate`, `volume`) before calling `speak_interruptible`. |
| **Animation** | Provides visual readiness feedback. | **`animate_status_pulse`** uses CustomTkinter's `root.after` method for a non-blocking, recursive color change loop.  |
| **Session Management** | Ensures resources are reused efficiently. | The Chrome browser is initialized once (`_init_chrome`) and the **`self.driver`** object is reused across all web commands. |

-----

## ⚠️ Known Limitations and Future Improvements

  * **Non-Portable Paths:** The reliance on hardcoded Windows user paths severely limits cross-platform compatibility. **Future Goal:** Use `os.path.expanduser('~')` or relative paths for better portability.
  * **Asynchronous TTS State:** The emotional properties are reset immediately after the non-blocking call, which can potentially lead to the next unrelated prompt using the 'reset' settings before the emotional speech finishes. This is an inherent challenge with `pyttsx3` when using non-blocking output with immediate property reset.
  * **Error Handling:** While some API errors are handled, a more comprehensive `try...except` block in `run_jarvis` with automatic resource cleanup would improve stability against unexpected crashes.
  * **Selenium Cleanup:** The browser instance and Selenium driver should be explicitly closed using a `try...finally` structure in `run_jarvis` to guarantee processes are terminated even on error.
