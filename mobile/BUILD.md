# KIS 자동매매 Android 앱 빌드 가이드




## 사전 준비

```bash
# buildozer 설치
pip install buildozer

# 필수 패키지 (Ubuntu/Debian)
sudo apt install -y python3-pip build-essential git \
    python3-setuptools python3-venv \
    openjdk-17-jdk unzip zip \
    autoconf libtool pkg-config \
    zlib1g-dev libncurses5-dev libncursesw5-dev \
    libtinfo5 cmake libffi-dev libssl-dev
```

## APK 빌드

```bash
cd /home/pois/kis-trader/mobile
buildozer android debug
```

첫 빌드는 Android SDK/NDK 다운로드로 30분+ 소요.
빌드 완료 후 `bin/` 폴더에 APK 생성.

## 핸드폰에 설치

```bash
# USB 연결 후
buildozer android deploy

# 또는 APK 파일을 직접 전송
adb install bin/kistrader-1.0.0-arm64-v8a-debug.apk
```

## 서버 주소 변경

`main.py` 상단의 `SERVER_URL` 수정:
```python
SERVER_URL = "https://pois2000.duckdns.org:6001"
```
