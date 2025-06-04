# Dex String Encryptor for Android APKs

![Android Security](https://img.shields.io/badge/Android-Security-brightgreen) 
![Termux Compatible](https://img.shields.io/badge/Termux-Compatible-blue)

This tool encrypts strings in specified classes/packages of an Android APK using XOR cipher and injects a native decoder method.

I did not encrypt the codes. If you want, you can add new features and optimizations by forking. But do not delete the credits, respect the work :D

---

<h3 align="center">
  🔐 <span style="color:#ff0070">Secure Your Code</span> — <span style="color:#00ffc2">Support the Project</span> ⭐
</h3>

<p align="center">
  If this project saved you time or helped your app stay protected,<br>
  consider <b>starring</b> it on GitHub and sharing with others.
</p>

<p align="center">
  <a href="https://github.com/dasqinnagiyev/Dex-Encryptor" target="_blank">
    <img src="https://img.shields.io/github/stars/dasqinnagiyev/Dex-Encryptor?style=for-the-badge&color=ff0070&label=Star%20on%20GitHub&logo=github" alt="GitHub stars">
  </a>
</p>

---

## Requirements for Termux

Install these packages in Termux:

```bash
pkg update && pkg upgrade
pkg install python openjdk-17 git wget unzip binutils libandroid-support
pip install requests
pkg install aapt apksigner
```

## Additional Tools Setup

### 1. Install Smali/Baksmali:
(If the smali and baksmali jar files here are not suitable, you can download the following)
```bash
wget https://bitbucket.org/JesusFreke/smali/downloads/baksmali-2.5.2.jar -O baksmali.jar
wget https://bitbucket.org/JesusFreke/smali/downloads/smali-2.5.2.jar -O smali.jar
```

### 2. Install Zipalign:
```bash
wget https://github.com/dasqinnagiyev/Dex-Encryptor/raw/refs/heads/main/zipalign
chmod +x zipalign
mv zipalign $PREFIX/bin/
```

### 3. Grant Storage Permission:
```bash
termux-setup-storage
```

## Usage Instructions

1. Run the script:
```bash
python D1.py
```

2. When prompted:
   - Enter path to APK file (e.g., `/storage/emulated/0/app.apk`)
   - Enter target packages/classes to encrypt (comma separated. And do not leave a space after the comma.):
     ```
     com.example.myapp,com.example.myapp.utils
     ```

## Features

- 🔒 XOR-based string encryption
- 📦 Automatic native library injection
- ✍️ APK signing with debug keystore
- 🎯 Selective encryption of specific packages
- 📱 Termux compatible

## Workflow

1. Extracts DEX files from APK
2. Decompiles to Smali using Baksmali
3. Injects decoder class (`com/modexy/Decoder.smali`)
4. Encrypts strings in target classes
5. Recompiles to DEX using Smali
6. Rebuilds APK with encrypted DEX files
7. Adds native libraries for decryption
8. Signs APK with debug keystore

## Output

The protected APK will be saved as:
```
<original_name>_protected.apk
```

## Troubleshooting

- If you get "Permission denied" errors, run:
  ```bash
  termux-chroot
  ```
  before executing the script

- For large APKs (>100MB), ensure you have sufficient storage

- If native libraries fail to download automatically:
  ```bash
  wget https://github.com/dasqinnagiyev/Dex-Encryptor/raw/main/native_libs.zip
  ```

## Notes

- The tool uses a debug keystore for signing (`debug.keystore`)
- For production use, replace with your own keystore
- Only strings in specified packages/classes will be encrypted
- Decoder.smali is automatically injected into your app

## Disclaimer

This tool is intended for educational purposes only. Always ensure you have proper authorization before modifying any APK.
