import os
import subprocess
import shutil
import re
import zipfile
import sys
import requests
import glob
import platform
import tempfile

# Apktool üçün keçici qovluq yarat
APKTOOL_TMPDIR = os.path.join(os.getcwd(), "apktool-tmp")
os.makedirs(APKTOOL_TMPDIR, exist_ok=True)
os.environ['APKTOOL_TMPDIR'] = APKTOOL_TMPDIR
os.environ['TMPDIR'] = APKTOOL_TMPDIR

KEY = 42

def unescape_java_string(s):
    """Java string escape qaydalarına uyğun unescape et"""
    def unescape_unicode(match):
        try:
            return chr(int(match.group(1), 16))
        except:
            return match.group(0)
    
    s = re.sub(r'\\u([0-9a-fA-F]{4})', unescape_unicode, s)
    
    escape_map = {
        "\\\\": "\\", "\\n": "\n", "\\t": "\t", 
        "\\'": "'", '\\"': '"',
    }
    
    for escaped, unescaped in escape_map.items():
        s = s.replace(escaped, unescaped)
    
    return s

def xor_encrypt(s):
    unescaped = unescape_java_string(s)
    return ''.join(f'\\u{ord(c)^KEY:04x}' for c in unescaped)

def process_smali_file(path):
    if "Decoder.smali" in path:
        print(f"ℹ️ Decoder.smali not encrypted: {path}")
        return
        
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"⚠️ File could not be read.: {path} - {str(e)}")
        return

    new_lines = []
    changes_made = False
    for line in lines:
        match = re.match(r'(\s*)(const-string(?:\/jumbo)?)\s+(\w+),\s+"(.*)"', line)
        if match:
            indent, const_type, reg, text = match.groups()
            try:
                encrypted = xor_encrypt(text)
                new_lines.append(f'{indent}{const_type} {reg}, "{encrypted}"\n')
                new_lines.append(f'{indent}invoke-static {{{reg}}}, Lcom/modexy/Decoder;->decode(Ljava/lang/String;)Ljava/lang/String;\n')
                new_lines.append(f'{indent}move-result-object {reg}\n')
                changes_made = True
                print(f"🔒 Encrypted: {text}")
            except Exception as e:
                print(f"⚠️ Encryption error: {text} - {str(e)}")
                new_lines.append(line)
        else:
            new_lines.append(line)

    if changes_made:
        try:
            with open(path, 'w', encoding='utf-8', errors='ignore') as f:
                f.writelines(new_lines)
            print(f"✅ Changes written: {path}")
        except Exception as e:
            print(f"⚠️ File could not be written.: {path} - {str(e)}")
    else:
        print(f"ℹ️ No changes were made.: {path}")

def should_process_file(file_path, targets):
    """Faylın şifrələndiyini yoxlayın"""
    # Dekoder faylını heç vaxt şifrələməyin
    if "Decoder.smali" in file_path:
        return False
        
    # Check all targets
    for target in targets:
        # Package control (like com.example)
        if '/' in target.replace('.', '/') and f"/{target.replace('.', '/')}/" in file_path:
            return True
            
        # Tək sinif nəzarəti (məsələn, com.example.MyClass)
        class_path = target.replace('.', '/') + '.smali'
        if file_path.endswith(class_path):
            return True
            
    return False

def walk_directory(root_dir, targets):
    if not targets:
        print("⚠️ Warning: No encryption target has been set!")
        return
        
    smali_count = 0
    processed_count = 0
    
    for dirpath, _, filenames in os.walk(root_dir):
        for file in filenames:
            if file.endswith('.smali'):
                smali_count += 1
                full_path = os.path.join(dirpath, file)
                
                if should_process_file(full_path, targets):
                    print(f"🎯 The target file is derived from: {full_path}")
                    process_smali_file(full_path)
                    processed_count += 1
                else:
                    print(f"ℹ️ File not included in encryption: {full_path}")
    
    print(f"🔍 Revealed: {smali_count} smali faylı")
    print(f"🔒 Encrypted files: {processed_count}")

def create_debug_keystore():
    if not os.path.exists("debug.keystore"):
        print("🔑 Creating debug keystore...")
        subprocess.run([
            "keytool", "-genkey", "-v", "-keystore", "debug.keystore",
            "-storepass", "android", "-alias", "modexy.org",
            "-keypass", "android", "-keyalg", "RSA", "-keysize", "2048",
            "-validity", "10000", "-dname", "O=ModExy.org,C=AZ"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("🔑 Debug keystore already available")

def run_baksmali(dex_path, output_dir):
    baksmali_jar = os.path.join(os.getcwd(), "baksmali.jar")
    if not os.path.exists(baksmali_jar):
        print(f"❌ {baksmali_jar} not found!")
        return False

    cmd = ["java", "-jar", baksmali_jar, "d", dex_path, "-o", output_dir]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        print(f"❌ Baksmali error: {result.stdout}")
        return False
    return True

def run_smali(smali_dir, output_dex):
    smali_jar = os.path.join(os.getcwd(), "smali.jar")
    if not os.path.exists(smali_jar):
        print(f"❌ {smali_jar} not found!")
        return False

    cmd = ["java", "-jar", smali_jar, "a", smali_dir, "-o", output_dex]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        print(f"❌ Smali error: {result.stdout}")
        return False
    return True

def extract_dex_files(apk_path, output_dir):
    dex_files = []
    with zipfile.ZipFile(apk_path, 'r') as zipf:
        for name in zipf.namelist():
            if name.startswith('classes') and name.endswith('.dex'):
                output_path = os.path.join(output_dir, name)
                with open(output_path, 'wb') as f:
                    f.write(zipf.read(name))
                dex_files.append(output_path)
                print(f"📦 {name} extracted")
    return dex_files

def main():
    print("📦 DEX Protect Tool - ModExy.org")

    apk_path = input("Enter the path to the APK file: ").strip()
    if not os.path.exists(apk_path):
        print(f"❌ File not found: {apk_path}")
        return

    targets_input = input("Targets to encrypt (separate with commas, e.g. com.modexy.org, com.modexy.org.Utils): ").strip()
    targets = [t.strip() for t in targets_input.split(",") if t.strip()]
    
    if not targets:
        print("⚠️ Warning: No encryption target set!")

    base_name = os.path.basename(apk_path).replace('.apk', '')
    output_apk = f"{base_name}_protected.apk"
    temp_dir = "temp_dex_processing"
    os.makedirs(temp_dir, exist_ok=True)

    # 1. APK-dan DEX fayllarını çıxart
    dex_files = extract_dex_files(apk_path, temp_dir)
    if not dex_files:
        print("❌ DEX file not found!")
        return

    # 2. Hər bir DEX faylını decompile et (baksmali)
    smali_dirs = []
    for i, dex_path in enumerate(dex_files):
        smali_dir = os.path.join(temp_dir, f"smali_{i}")
        os.makedirs(smali_dir, exist_ok=True)
        if not run_baksmali(dex_path, smali_dir):
            print(f"❌ {dex_path} could not be decompiled")
            return
        smali_dirs.append(smali_dir)

    # 3. Decoder.smali faylını ilk smali qovluğuna əlavə et
    if smali_dirs:
        decoder_dir = os.path.join(smali_dirs[0], "com", "modexy")
        os.makedirs(decoder_dir, exist_ok=True)
        decoder_smali = os.path.join(decoder_dir, "Decoder.smali")
        with open(decoder_smali, "w", encoding='utf-8') as f:
            f.write(""".class public Lcom/modexy/Decoder;
.super Ljava/lang/Object;

.method static constructor <clinit>()V
    .registers 1
    const-string v0, "dasqin"
    invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V
    return-void
.end method

.method public static native decode(Ljava/lang/String;)Ljava/lang/String;
.end method
""")
        print(f"✅ Decoder.smali file added: {decoder_smali}")

    # 4. Bütün smali qovluqlarını emal et (şifrələ)
    for smali_dir in smali_dirs:
        print(f"🔍 Scanning for encryption: {smali_dir}")
        walk_directory(smali_dir, targets)

    # 5. Hər bir smali qovluğunu yenidən DEX faylına çevir
    new_dex_files = []
    for i, smali_dir in enumerate(smali_dirs):
        dex_output = os.path.join(temp_dir, f"classes{'' if i==0 else i+1}.dex")
        if not run_smali(smali_dir, dex_output):
            print(f"❌ {smali_dir} Could not convert to DEX file")
            return
        new_dex_files.append(dex_output)

    # 6. APK-nı yenidən qurmaq
    print("🏗️ Rebuilding APK...")
    temp_apk = tempfile.NamedTemporaryFile(delete=False).name
    
    with zipfile.ZipFile(apk_path, 'r') as orig_zip, \
         zipfile.ZipFile(temp_apk, 'w') as new_zip:
        
        for item in orig_zip.infolist():
            if item.filename.startswith('classes') and item.filename.endswith('.dex'):
                print(f"🗑️ Deleted: {item.filename}")
                continue
            data = orig_zip.read(item.filename)
            new_zip.writestr(item, data)
    
    with zipfile.ZipFile(temp_apk, 'a') as new_zip:
        for dex_path in new_dex_files:
            dex_name = os.path.basename(dex_path)
            new_zip.write(dex_path, dex_name)
            print(f"➕ Added: {dex_name}")

    # Native kitabxanaları əlavə et
    native_zip = "native_libs.zip"
    if not os.path.exists(native_zip):
        print("\n❌ native_libs.zip not found! Downloading...")
        try:
            url = "https://github.com/dasqinnagiyev/Dex-Encryptor/raw/refs/heads/main/native_libs.zip"
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192
            
            with open(native_zip, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"📥 Downloading: {percent:.1f}%", end='\r')
            print("\n✅ native_libs.zip successfully downloaded")
        except Exception as e:
            print(f"❌ Download error: {str(e)}")
            print("Please download manually:")
            print("wget https://github.com/dasqinnagiyev/Dex-Encryptor/raw/refs/heads/main/native_libs.zip")
            return
    
    temp_libs = "temp_libs"
    os.makedirs(temp_libs, exist_ok=True)
    with zipfile.ZipFile(native_zip, 'r') as zip_ref:
        zip_ref.extractall(temp_libs)
    
    with zipfile.ZipFile(temp_apk, 'a') as zipf:
        for arch in ["armeabi-v7a", "arm64-v8a", "x86", "x86_64"]:
            src = os.path.join(temp_libs, "native_libs", arch)
            if os.path.exists(src):
                for root, dirs, files in os.walk(src):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, src)
                        zip_path = os.path.join("lib", arch, rel_path)
                        zipf.write(full_path, zip_path)
                print(f"  - {arch} libraries added for architecture")
            else:
                print(f"⚠️ {arch} No library found for architecture")

    shutil.move(temp_apk, output_apk)

    # 7. APK-nı imzala
    create_debug_keystore()
    
    print("✍️ APK is signed...")
    aligned_apk = f"aligned_{output_apk}"
    
    try:
        print("🔧 Zipaligned...")
        subprocess.run(["zipalign", "-v", "4", output_apk, aligned_apk], check=True)
        
        print("🔏 Signing...")
        subprocess.run([
            "apksigner", "sign", 
            "--ks", "debug.keystore",
            "--ks-pass", "pass:android",
            aligned_apk
        ], check=True)
        
        os.remove(output_apk)
        os.rename(aligned_apk, output_apk)
        print(f"\n✅ Signed APK: {output_apk}")
    except Exception as e:
        print(f"⚠️ Signing error: {str(e)}")
        print("For manual signing:")
        print(f"zipalign -v 4 {output_apk} aligned_{output_apk}")
        print(f"apksigner sign --ks debug.keystore --ks-pass pass:android aligned_{output_apk}")
        print(f"mv aligned_{output_apk} {output_apk}")
        return

    # Təmizlik
    shutil.rmtree(temp_dir, ignore_errors=True)
    shutil.rmtree(temp_libs, ignore_errors=True)
    shutil.rmtree(APKTOOL_TMPDIR, ignore_errors=True)
    
    if os.path.exists(output_apk):
        size = os.path.getsize(output_apk)
        size_mb = size / (1024 * 1024)
        print(f"Output file: {output_apk}")
        print(f"File size: {size} bayt ({size_mb:.2f} MB)")
    else:
        print("❌ Output file not created!")

if __name__ == "__main__":
    main()