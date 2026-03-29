# Kule Radar

Bu proje, ofislerdeki ortak ekranlar ve televizyonlar için hazırlanmış bir durum takip (dashboard) uygulamasıdır. İçerisinde, verilerin yönetilebilmesi için bir admin paneli ile TV için optimize edilmiş dinamik bir arayüz bulunur. 

## Özellikler
- **TV Ekranı (Frontend):** Modern, koyu tema ağırlıklı, tam ekran çalışacak şekilde dizayn edilmiş arayüz. Ekranda veri periyodik olarak otomatik güncellenir.
- **Yönetim Paneli:** Aktif projelerin, çalışanların ve "Kitchen Heroes" gibi öne çıkan bilgilerin yönetildiği tarayıcı tabanlı panel. Sürükle bırak ile resim yükleme desteklenir.
- **Atomik Dosya Kaydı:** Projedeki anlık JSON verisinde okuma ve yazma işlemlerinin çakışıp dosyanın bozulmasını engellemek için tüm işlemler atomik şekilde yapılır. TV ekranında yarım veri yansımaz.
- **API ve Mimari:** FastAPI üzerine kurulu yapı, Adapter pattern mimarisine oturtulmuştur. İleride dış API entegrasyonu eklenebilir. Mimari detaylar için `ARCHITECTURE.md` dosyasına bakabilirsiniz.

## Kurulum ve Çalıştırma

Projeyi çalıştırdığınız bilgisayarı bir yerel sunucu (local server) haline getirip mekandaki diğer cihazlardan bağlanmak oldukça basittir.

### 1- Ortamın Ayarlanması ve Paketlerin Yüklenmesi
Projeyi sisteminizdeki diğer paketlerden izole çalıştırmak için öncelikle bir sanal ortam (virtual environment) oluşturup paketleri kurmanız önerilir:

```bash
# 1. Sanal ortam (venv) oluşturma
python -m venv env

# 2. Ortamı aktifleştirme (macOS/Linux için)
source env/bin/activate
# (Eğer Windows kullanırsan: env\Scripts\activate)

# 3. Gerekli kütüphaneleri yükleme
pip install -r requirements.txt
```

### 2- IP ve Port Ayarları
Projeyi dışarıdan erişilebilir yapmak için bir ayar dosyası kullanabilirsiniz. Kök dizindeki `.env.example` dosyasını kopyalayarak `.env` isimli yeni bir dosya yaratın:
```env
HOST=0.0.0.0
PORT=8000
```
> *İpucu:* `HOST=0.0.0.0` değeri, projenin bilgisayarınızın yerel IP adresi üzerinden ağdaki herkese açılmasını sağlar.

### 3- Projeyi Başlatma
Hazırlıklar tamamlandıktan sonra sunucuyu başlatmak için:
```bash
python main.py
```

### 4- Diğer Cihazlardan (TV, Telefon, Tablet) Erişim
Ağa bağlanan diğer cihazlarda tarayıcıyı açın ve projeyi ayağa kaldırdığınız bilgisayarın IP adresini girin (Örn: 192.168.1.45). Test etmek için:

- **Dashboard (TV için):** `http://<BILGISAYARINIZIN_IP_ADRESI>:8000/`
- **Yönetici Paneli:** `http://<BILGISAYARINIZIN_IP_ADRESI>:8000/static/admin.html`

Terminalden veya sistem ayarlarından IP adresinizi bulabilirsiniz (Örn: macOS'te `ifconfig` komutu işinize yarar).

## Özelleştirme (Logo Kullanımı)

TV ekranının (Dashboard) sol üst köşesinde şirketinizin veya projenizin logosunu göstermek isterseniz şu adımları izleyebilirsiniz:

1. Kullanılabilir formatta bir logonun (tercihen arka planı saydam) ismini `logo.png` olarak değiştirin.
2. Hazırladığınız dosyayı proje dizinindeki `static/img/` klasörünün içerisine bırakın. (Eğer `img` isimli bir klasör yoksa oluşturun).
3. Sayfayı yenilediğinizde (veya TV ekranı kendi döngüsünde yenilendiğinde) logonuz sol üstte otomatik olarak belirecektir.

*(Not: Sisteme bir logo yüklemezseniz görsel olarak bir hata ikonu çıkmaz, alan gizlenerek doğal görünüm korunur.)*
