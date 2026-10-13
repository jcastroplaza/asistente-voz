[app]
title = AsistenteVoz
package.name = asistentevoz
package.domain = org.ejemplo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1

requirements = python3,kivy,pyjnius,SpeechRecognition,pyaudio

orientation = portrait
fullscreen = 0

# Permisos para Micrófono, Cámara, Llamadas, Internet, SMS y Almacenamiento
android.permissions = RECORD_AUDIO, INTERNET, ACCESS_NETWORK_STATE, SEND_SMS, CALL_PHONE, CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
