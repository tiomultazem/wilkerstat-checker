# Audit Analisis Aksesibilitas Jaringan & Topologi IndiHome

**Tanggal:** 2026-11-01  
**Topologi Fisik:**
1. Server -> Hub 1 -> Hub 2 -> Router IndiHome (Kabel LAN)
2. Klien -> Router IndiHome (Wireless / Wi-Fi)

---

## 1. Klarifikasi Konseptual Jaringan

> [!IMPORTANT]
> **Koreksi Asumsi "Selain LAN":**  
> Perangkat nirkabel (Wi-Fi) yang terhubung ke router IndiHome yang sama dengan server kabel **tetap berada di dalam Local Area Network (LAN) yang sama** (satu subnet IP, umumnya `192.168.1.0/24`). Ini bukan koneksi WAN/Internet eksternal.

### Evaluasi Kode Aplikasi:
- Berkas [`app/config.py`](file:///c:/laragon/www/wilkerstat-checker/app/config.py):
  `HOST = "0.0.0.0"` dan `PORT = 11750`.
- Server WSGI (Waitress) di [`run.py`](file:///c:/laragon/www/wilkerstat-checker/run.py) telah mengikat (*bind*) ke seluruh antarmuka jaringan (`0.0.0.0`).
- **Kesimpulan Kode:** **Tidak memerlukan perubahan kode sumber sama sekali.** Masalah 100% berada pada lapisan jaringan (*networking*) dan sistem operasi (*OS security*).

---

## 2. Akar Masalah Pemblokiran Akses (Root Cause)

Kegagalan perangkat Wi-Fi mengakses server kabel disebabkan oleh dua proteksi:

### A. Windows Defender Firewall & Network Profile (Penyebab Utama #1)
1. **Network Profile "Public":** Saat server Windows terhubung ke router, Windows sering menetapkan profil jaringan sebagai *Public Network*. Pada profil ini, firewall memblokir seluruh koneksi TCP masuk (*inbound connection*) secara diam-diam.
2. **Port 11750 Belum Diizinkan:** Windows Firewall belum memiliki aturan *Inbound Rule* khusus untuk mengizinkan lalu lintas masuk pada port 11750 (TCP).

### B. AP Isolation / Client Isolation pada Router IndiHome (Penyebab Utama #2)
Sebagian besar ONT/Router bawaan IndiHome (ZTE F609, ZTE F670L, Huawei HG8245H5, Fiberhome):
- Memiliki fitur bernama **"AP Isolation"** atau **"SSID Isolation"** pada menu konfigurasi Wi-Fi.
- Jika fitur ini aktif, router secara sengaja mengisolasi klien Wi-Fi agar tidak dapat berkomunikasi dengan perangkat di port kabel LAN maupun sesama klien nirkabel demi alasan privasi publik.

### C. Kasus Khusus: Jika Benar-Benar Ingin Diakses dari Luar Rumah (Internet Eksternal)
Jika maksud "selain pake LAN" adalah diakses dari internet publik (seluler/luar jaringan rumah):
- IndiHome menggunakan **CGNAT (Carrier-Grade NAT)** dengan IP privat operator (`100.64.0.0/10` atau `10.x.x.x`).
- Port forwarding biasa di router **tidak akan bekerja**.
- Solusi standar industri yang tepat adalah memasang tunnel terenkripsi seperti **Cloudflare Tunnel (cloudflared)** atau **Tailscale**, bukan membuka port manual.

---

## 3. Matriks Tindakan Penyelesaian (Step-by-Step)

### Langkah 1: Buka Port 11750 di Windows Firewall Server
Jalankan perintah berikut di PowerShell (Administrator) pada PC server:

```powershell
New-NetFirewallRule -DisplayName "WilkerStat Checker LAN" -Direction Inbound -LocalPort 11750 -Protocol TCP -Action Allow -Profile Any
```

Pastikan juga profil jaringan diubah dari Public ke Private:
```powershell
Set-NetConnectionProfile -InterfaceAlias "Ethernet" -NetworkCategory Private
```

### Langkah 2: Verifikasi & Matikan AP Isolation di Router IndiHome
1. Buka browser, akses gateway router IndiHome (umumnya `http://192.168.1.1`).
2. Masuk ke menu **Network** -> **WLAN** -> **SSID Settings** (atau **Basic Settings**).
3. Cari opsi **"Enable SSID Isolation"** atau **"AP Isolation"** -> pastikan dalam kondisi **DISABLED / UNCHECKED**.
4. Simpan konfigurasi (*Apply*).

### Langkah 3: Pengujian Konektivitas
1. Cek IP lokal PC server (misal `192.168.1.50`) via `ipconfig`.
2. Buka browser di perangkat HP/laptop klien yang terhubung ke Wi-Fi IndiHome.
3. Akses alamat: `http://192.168.1.50:11750`.

