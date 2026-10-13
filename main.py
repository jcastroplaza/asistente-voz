 import os
import json
import threading
import time
import urllib.request
import urllib.parse
import speech_recognition as sr

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import mainthread

# Integración nativa con Android mediante Pyjnius
try:
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent = autoclass('android.content.Intent')
    String = autoclass('java.lang.String')
    Uri = autoclass('android.net.Uri')
    TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
    Locale = autoclass('java.util.Locale')
    MediaStore = autoclass('android.provider.MediaStore')
    IS_ANDROID = True
except Exception:
    IS_ANDROID = False

# Reemplaza esta cadena con tu clave de Google AI Studio (aistudio.google.com)
GEMINI_API_KEY = "TU_CLAVE_DE_API_AQUI"


class GeminiAI:
    """Procesa cualquier consulta utilizando la API de Inteligencia Artificial."""

    @staticmethod
    def ask(prompt: str) -> str:
        if GEMINI_API_KEY == "TU_CLAVE_DE_API_AQUI" or not GEMINI_API_KEY:
            return "Por favor, configura tu clave de API de Gemini para habilitar mi inteligencia completa."

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [{
                "parts": [{"text": f"Eres un asistente de voz inteligente para Android. Responde de forma clara, directa y concisa en un máximo de 2 o 3 oraciones a lo siguiente: {prompt}"}]
            }]
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"Error en API Gemini: {e}")
            return "Ocurrió un problema de conexión al procesar tu solicitud con la IA."


class AndroidBridge:
    """Clase encargada de ejecutar acciones nativas en Android (Voz, WhatsApp, Llamadas, Cámara, etc.)."""

    def __init__(self):
        self.tts = None
        if IS_ANDROID:
            self.activity = PythonActivity.mActivity
            self.init_tts()

    def init_tts(self):
        """Inicializa la síntesis de voz nativa de Android."""
        class TTSListener(autoclass('android.speech.tts.TextToSpeech$OnInitListener')):
            def __init__(self, bridge):
                super().__init__()
                self.bridge = bridge

            def onInit(self, status):
                if status == TextToSpeech.SUCCESS and self.bridge.tts:
                    self.bridge.tts.setLanguage(Locale("es", "ES"))

        self.listener = TTSListener(self)
        self.tts = TextToSpeech(self.activity, self.listener)

    def speak(self, text: str):
        """Responde en voz alta."""
        print(f"[Asistente]: {text}")
        if IS_ANDROID and self.tts:
            self.tts.speak(text, TextToSpeech.QUEUE_FLUSH, None, None)

    def send_whatsapp(self, phone_number: str, text_message: str):
        """Abre WhatsApp con número y mensaje prellenados."""
        if IS_ANDROID:
            url = f"https://api.whatsapp.com/send?phone={phone_number}&text={Uri.encode(text_message)}"
            intent = Intent(Intent.ACTION_VIEW)
            intent.setData(Uri.parse(url))
            self.activity.startActivity(intent)

    def send_sms(self, phone_number: str, text_message: str):
        """Abre la app de mensajes SMS predeterminada."""
        if IS_ANDROID:
            intent = Intent(Intent.ACTION_VIEW)
            intent.setData(Uri.parse(f"smsto:{phone_number}"))
            intent.putExtra("sms_body", text_message)
            self.activity.startActivity(intent)

    def share_video(self, video_url: str):
        """Abre el menú para compartir enlaces de video."""
        if IS_ANDROID:
            intent = Intent(Intent.ACTION_SEND)
            intent.setType("text/plain")
            intent.putExtra(Intent.EXTRA_TEXT, video_url)
            chooser = Intent.createChooser(intent, String("Compartir video vía..."))
            self.activity.startActivity(chooser)

    def make_call(self, phone_number: str):
        """Abre el marcador telefónico."""
        if IS_ANDROID:
            intent = Intent(Intent.ACTION_DIAL)
            intent.setData(Uri.parse(f"tel:{phone_number}"))
            self.activity.startActivity(intent)

    def open_camera(self):
        """Abre la cámara para tomar fotos."""
        if IS_ANDROID:
            intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
            self.activity.startActivity(intent)

    def record_video(self):
        """Abre la cámara en modo grabación de video."""
        if IS_ANDROID:
            intent = Intent(MediaStore.ACTION_VIDEO_CAPTURE)
            self.activity.startActivity(intent)

    def record_audio(self):
        """Abre la grabadora de voz de Android."""
        if IS_ANDROID:
            intent = Intent(MediaStore.Audio.Media.RECORD_SOUND_ACTION)
            self.activity.startActivity(intent)


class RecipeManager:
    """Gestiona el almacenamiento y búsqueda de recetas en el almacenamiento interno."""

    def __init__(self, storage_path):
        self.file_path = os.path.join(storage_path, "recetas.json")
        self.recipes = self.load_recipes()

    def load_recipes(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_recipe(self, title: str, content: str):
        self.recipes[title.lower()] = content
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.recipes, f, ensure_ascii=False, indent=2)
        return f"Receta '{title}' guardada correctamente."

    def list_recipes(self):
        if not self.recipes:
            return "Aún no tienes recetas guardadas."
        return "Tus recetas guardadas son: " + ", ".join(self.recipes.keys())


class VoiceAssistantApp(App):
    def build(self):
        self.bridge = AndroidBridge()
        self.listening = False
        self.wake_word = "oye siri"

        user_dir = self.user_data_dir if IS_ANDROID else "."
        self.recipe_manager = RecipeManager(user_dir)
        self.last_ai_response = None

        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.status_label = Label(
            text="Presiona 'Iniciar Asistente' y di 'Oye Siri'",
            font_size='18sp',
            halign='center'
        )
        self.btn_toggle = Button(
            text="Iniciar Asistente",
            size_hint=(1, 0.25),
            background_color=(0.1, 0.5, 0.9, 1)
        )
        self.btn_toggle.bind(on_press=self.toggle_listening)

        layout.add_widget(self.status_label)
        layout.add_widget(self.btn_toggle)
        return layout

    def toggle_listening(self, instance):
        if not self.listening:
            self.listening = True
            self.btn_toggle.text = "Detener Asistente"
            self.update_status("Escuchando palabra clave ('Oye Siri')...")
            threading.Thread(target=self.listen_loop, daemon=True).start()
        else:
            self.listening = False
            self.btn_toggle.text = "Iniciar Asistente"
            self.update_status("Asistente detenido.")

    @mainthread
    def update_status(self, text):
        self.status_label.text = text

    def listen_loop(self):
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True

        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)

            while self.listening:
                try:
                    self.update_status("Escuchando 'Oye Siri'...")
                    audio = recognizer.listen(source, timeout=4, phrase_time_limit=4)
                    text = recognizer.recognize_google(audio, language="es-ES").lower()

                    if self.wake_word in text:
                        self.bridge.speak("¿En qué te puedo ayudar?")
                        self.update_status("¡Oye Siri detectado! Escuchando tu orden...")

                        order_audio = recognizer.listen(source, timeout=6, phrase_time_limit=8)
                        command = recognizer.recognize_google(order_audio, language="es-ES").lower()
                        self.process_command(command)

                except (sr.WaitTimeoutError, sr.UnknownValueError):
                    continue
                except Exception as e:
                    print(f"Error en bucle de voz: {e}")
                    time.sleep(1)

    def process_command(self, command: str):
        self.update_status(f"Procesando: '{command}'")

        # 1. Comandos directos de Android
        if "whatsapp" in command or "mensaje" in command:
            self.bridge.speak("Abriendo WhatsApp...")
            self.bridge.send_whatsapp("1234567890", "Mensaje enviado desde mi asistente de voz")

        elif "sms" in command:
            self.bridge.speak("Abriendo aplicación de SMS...")
            self.bridge.send_sms("1234567890", "Mensaje SMS enviado por voz")

        elif "llamar" in command or "llama" in command:
            self.bridge.speak("Abriendo el marcador telefónico...")
            self.bridge.make_call("1234567890")

        elif "grabar video" in command:
            self.bridge.speak("Abriendo la cámara en modo video...")
            self.bridge.record_video()

        elif "camara" in command or "cámara" in command or "foto" in command:
            self.bridge.speak("Abriendo la cámara...")
            self.bridge.open_camera()

        elif "grabar audio" in command or "nota de voz" in command:
            self.bridge.speak("Abriendo la grabadora de voz...")
            self.bridge.record_audio()

        elif "compartir video" in command:
            self.bridge.speak("Abriendo el menú para compartir...")
            self.bridge.share_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        elif "guardar receta" in command:
            if self.last_ai_response:
                nombre = command.replace("guardar receta", "").strip() or "Receta de cocina"
                msg = self.recipe_manager.save_recipe(nombre, self.last_ai_response)
                self.bridge.speak(msg)
            else:
                self.bridge.speak("Primero consulta o pide una receta para poder guardarla.")

        elif "mis recetas" in command or "ver recetas" in command:
            recetas_txt = self.recipe_manager.list_recipes()
            self.bridge.speak(recetas_txt)

        # 2. Consultas abiertas procesadas con la Inteligencia Artificial
        else:
            self.update_status("Consultando con la Inteligencia Artificial...")
            ai_response = GeminiAI.ask(command)
            self.last_ai_response = ai_response
            self.bridge.speak(ai_response)


if __name__ == '__main__':
    VoiceAssistantApp().run()
     
        
