import pyaudio
import wave
import speech_recognition as sr
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, font
import openai  # Make sure to install this

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Set up OpenAI API (make sure to replace with your own API key)
openai.api_key = 'MYKEY'

# Get list of devices
def get_device_list():
    device_count = audio.get_device_count()
    devices = []
    for i in range(device_count):
        device_info = audio.get_device_info_by_index(i)
        if device_info['maxInputChannels'] > 0:  # Check if it's an input device
            devices.append((device_info['name'], i))  # Add the device name and index to the list
    return devices

# Record audio
def record_audio(device_index):
    FORMAT = pyaudio.paInt16
    CHANNELS = 1  # Set to mono
    RATE = 44100
    CHUNK = 1024
    OUTPUT_FILENAME = "recording.wav"

    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, input_device_index=device_index, frames_per_buffer=CHUNK)
    frames = []

    # This loop is meant for fixed recording time, but if you implement dynamic stopping, you'll have to modify it.
    for _ in range(0, int(RATE / CHUNK * 10)):  
        data = stream.read(CHUNK)
        frames.append(data)

    stream.stop_stream()
    stream.close()

    with wave.open(OUTPUT_FILENAME, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    recognizer = sr.Recognizer()
    with sr.AudioFile("recording.wav") as source:
        audio_data = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio_data)
            # Send to GPT model
            messages = [
            {"role": "user", "content": f"As a therapist and, respond in a human-like, helpful and non-judgemental way to: '{text}'. Respond with advice and ask follow-up questions regarding their concerns. Do not act as an AI model, and never respond by saying you cannot help or anything similar."}
            ]
            response = openai.ChatCompletion.create(model="gpt-4", messages=messages, max_tokens=150, temperature=0.3)
            gpt_response = response.choices[0].message['content'].strip()
            return text, gpt_response

        except sr.UnknownValueError:
            return "Could not understand the audio.", None
        except sr.RequestError:
            return "API unavailable.", None


# Button to start recording
def on_record():
    selected_device_name = device_var.get()
    device_index = [device[1] for device in devices if device[0] == selected_device_name][0]
    text, response = record_audio(device_index)  # Store the text and response

    if text is None or "Could not understand" in text:
        messagebox.showerror("Error", text)  # Display error message
    else:
        messagebox.showinfo("Info", "Recording completed!")
        # Format the text to show "Me:" followed by the text and then "Therapist:" followed by the GPT response.
        formatted_text = f"Me: {text}\n\nTherapist: {response}\n\n"
        response_text.insert(tk.END, formatted_text)

# GUI
root = tk.Tk()
root.title("Audio Recorder")
root.geometry('600x400')

style = ttk.Style()
style.theme_use('clam')

default_font = font.nametofont("TkDefaultFont")
default_font.configure(size=12)

mainframe = ttk.Frame(root, padding="20")
mainframe.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=20, pady=20)
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

# Dropdown menu for devices
devices = get_device_list()
device_names = [device[0] for device in devices]
device_var = tk.StringVar(root)
device_var.set(device_names[0])  # default value
device_dropdown = ttk.Combobox(mainframe, textvariable=device_var, values=device_names, state="readonly", font=("Arial", 12))
device_dropdown.grid(column=1, row=1, sticky=(tk.W, tk.E), pady=10)

ttk.Label(mainframe, text="Select Device:", font=("Arial", 12)).grid(column=0, row=1, sticky=tk.W)
record_button = ttk.Button(mainframe, text="Record", command=on_record, style='TButton')
record_button.grid(column=1, row=2, pady=20)

response_text = tk.Text(mainframe, width=50, height=10, font=("Arial", 12))
response_text.grid(column=0, row=3, columnspan=2, pady=20)

root.mainloop()
