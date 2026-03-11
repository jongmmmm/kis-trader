[app]
title = KIS 자동매매
package.name = kistrader
package.domain = org.kis
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0

requirements = python3,kivy,pyjnius,android,certifi,urllib3

# Android 설정
android.permissions = INTERNET,USE_BIOMETRIC,USE_FINGERPRINT,ACCESS_NETWORK_STATE
android.api = 33
android.minapi = 28
android.ndk = 25b
android.accept_sdk_license = True
android.arch = arm64-v8a

# 아이콘/스플래시
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

# gradle 의존성 (BiometricPrompt)
android.gradle_dependencies = androidx.biometric:biometric:1.1.0,androidx.fragment:fragment:1.5.7

# orientation
orientation = portrait
fullscreen = 0

# 로그
log_level = 2

[buildozer]
log_level = 2
warn_on_root = 1
