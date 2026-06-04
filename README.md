# Tubes Jaringan Komputer 
## Implementasi Client-Proxy-Server (Socket Python)

## Struktur File

```
├── webserver.py   ← Web Server (TCP:8000 HTTP + UDP:9000 Echo)
├── proxy.py       ← Proxy Server (TCP:8080, forward + cache)
├── client.py      ← Client (TCP HTTP via Proxy + UDP QoS Pinger)
├── index.html     ← Halaman utama
├── page.html      ← Halaman cache test
├── about.html     ← Halaman about
└── README.md      ← Panduan
```

Perhatian: Tidak boleh ada file Python tambahan. Semua kode ada di 3 file di atas.

## Cara Menjalankan

Urutan penting: jalankan webserver → proxy → client di 3 terminal berbeda.

### 1. Jalankan Web Server dulu
```bash
python webserver.py
```
Harusnya keluar output seperti ini:
```
[MAIN] Web Server berjalan di 0.0.0.0:8000 (HTTP)
[UDP ] UDP Echo Server berjalan di 0.0.0.0:9000
```

### 2. Buka terminal baru, jalankan Proxy
```bash
python proxy.py
```
Output:
```
[PROXY] Listening : 0.0.0.0:8080
[PROXY] Forward → : 127.0.0.1:8000
```

### 3. Terminal ketiga untuk Client

**Mode TCP** (request via proxy):
```bash
python client.py --mode tcp
python client.py --mode tcp --url /page.html --count 3
```

**Mode UDP** (test QoS pinger):
```bash
python client.py --mode udp
python client.py --mode udp --count 20
```

**Atau jalankan keduanya** (both):
```bash
python client.py --mode both
```

**Multi-client simulation** (simulasi beban dengan thread konkuren, minimal 5 client):
```bash
python client.py --mode multi --clients 5
```

## Topologi Jaringan

Karena kelompok 2 orang dan co-located (satu laptop):
```
Laptop B (Client)               Laptop A (Proxy + Web Server)
    client.py ────TCP:8080───► proxy.py
                                    │
                              TCP:8000
                                    │
                              webserver.py
                              (UDP:9000)
```
Jika hanya punya 1 laptop, pakai localhost 127.0.0.1 untuk semua.

## Konfigurasi IP

Bagian atas client.py:
```python
PROXY_HOST  = "192.168.1.11"   # IP Laptop A
SERVER_HOST = "192.168.1.11"   # UDP server
```

Di proxy.py:
```python
SERVER_HOST = "127.0.0.1"      # Co-located
```

Alternatif: pakai argumen command line saat jalankan:
```bash
python client.py --mode tcp --proxy-host 192.168.1.11
python client.py --mode udp --server-host 192.168.1.11
```

## Fitur yang Sudah Diimplementasikan

- TCP HTTP Server (GET saja)
- Error handling: 404, 500, 405
- UDP Echo Server
- Threading untuk concurrent connections
- Proxy forwarding ke server
- In-memory caching (thread-safe)
- X-Cache header menunjukkan HIT/MISS
- Client bisa kirim HTTP request via proxy
- UDP QoS testing (pinger)
- Hitung RTT, Jitter, Packet Loss, Throughput
- Mode multi-client (concurrent load)
- Logging lengkap dengan timestamp
- **CSV export untuk hasil test** (TCP, UDP, Multi-client)
- **File logging** untuk webserver dan proxy

## Test Cases

1. **Direct ke web server** (bypass proxy)
   ```bash
   python client.py --mode tcp --proxy-host 127.0.0.1 --proxy-port 8000 --url /index.html
   ```

2. **Test cache** - request yang sama dua kali harus lebih cepat (HIT)
   ```bash
   python client.py --mode tcp --url /page.html
   python client.py --mode tcp --url /page.html
   ```

3. **Test 404**
   ```bash
   python client.py --mode tcp --url /missing.html
   ```

4. **Test UDP echo**
   ```bash
   python client.py --mode udp --count 10
   ```

5. **Test concurrent clients** (min 5)
   ```bash
   python client.py --mode multi --clients 5
   ```

## Troubleshooting

- **Connection refused** → webserver atau proxy belum dijalankan. Cek urutan: webserver → proxy → client
- **Timeout UDP** → firewall mungkin block UDP, atau server crash. Coba nonaktifkan firewall dulu
- **Cache tidak bekerja** → proxy belum aktif. Pastikan proxy.py running
- **HTML kosong/error** → parsing HTTP header salah. Cek format request harus `GET /path HTTP/1.1\r\n\r\n`
- **Multi-client blocked** → thread tidak start dengan benar. Seharusnya sudah ditangani di code

## QoS Metrics

- **RTT** = T_recv − T_send
- **Packet Loss** = (paket_hilang / total) × 100%
- **Jitter** = standard deviation dari delta RTT
- **Throughput** = total_bytes × 8 / durasi (bits per second)

## Deliverables

Kumpulkan screenshot untuk:
- webserver.py log saat menerima request
- proxy.py log menunjukkan cache HIT dan MISS
- client.py mode tcp output (HTML render)
- client.py mode udp output (QoS stats)
- client.py mode multi dengan 5 clients
- Wireshark packet capture filter: `tcp.port==8000 || tcp.port==8080 || udp.port==9000`

## Output Files

Setiap test akan menghasilkan file CSV dengan hasil:
- **TCP Mode**: `tcp_results_YYYYMMDD_HHMMSS.csv` - Hasil request (status, cache, RTT, ukuran)
- **UDP Mode**: `udp_results_YYYYMMDD_HHMMSS.csv` - Statistik QoS (RTT, jitter, packet loss, throughput)
- **Multi-Client**: `multi_client_results_YYYYMMDD_HHMMSS.csv` - Hasil dari setiap client

Log files (real-time):
- **webserver.log** - Catatan semua request HTTP dan UDP echo
- **proxy.log** - Catatan semua request proxy, cache HIT/MISS, error