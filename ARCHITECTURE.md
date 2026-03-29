# KULE RADAR: Sistem Mimarisi ve Entegrasyon Vizyonu
**Sürüm:** 1.0.0
**Proje Tipi:** TV Dashboard (Kültür ve Momentum Motoru) & Kule Komuta Merkezi

## 1. Mimari Felsefe ve Kapsam
Kule Radar, bir "ekran projesi" değil, insan psikolojisini manipüle ederek takımı gönüllü olarak OpenProject ekosistemine entegre etmeyi amaçlayan bir **Truva Atı**'dır. 

Sistem; kısa vadeli (Quick & Dirty) çözümleri reddeder. "Geçici" lokal veritabanı (JSON) kullanılsa dahi, arka planda (Backend) "Adapter (Adaptör) Tasarım Deseni" kullanılarak sistemin her an dış bir API'ye (OpenProject) bağlanabileceği kurumsal bir temel üzerine inşa edilmiştir.

## 2. Sistem Bileşenleri (Ayrıştırılmış Mimari - SoC)

### 2.1. Sunucu Katmanı (Backend)
- **Teknoloji:** Python FastAPI (Yüksek performanslı, asenkron, tip korumalı).
- **Tasarım Deseni (Repository/Adapter Pattern):** Veri çekme ve yazma işlemleri doğrudan dosya yollarına (file paths) bağlanmaz. `IDataAdapter` isimli bir soyutlama (abstraction) kullanılır. 
  - *Faz 1 (Mevcut):* `MockJSONAdapter` çalışır.
  - *Faz 2 (Gelecek):* `OpenProjectAdapter` yazılır ve sisteme enjekte edilir.

### 2.2. Veri Güvenliği ve Bütünlüğü
- **Concurrency (Eşzamanlılık) Kontrolü:** Admin panelinden veri yazılırken, TV'nin veriyi okuduğu ana denk gelip `dashboard_data.json` dosyasının bozulmasını (corruption) engellemek için **Atomic File Replace** (Atomik Dosya Değiştirme) stratejisi uygulanır. Veri önce gizli bir `.tmp` dosyasına yazılır, ardından anında asıl JSON ile yer değiştirilir.

### 2.3. Sunum Katmanı (TV Frontend - index.html)
- **Paradigma:** Durumsuz (Stateless) ve Otonom Tüketici.
- **Teknoloji:** Vanilla JS (veya hafif bir State Machine) ve TailwindCSS.
- **İşleyiş:** - Asla tam sayfa yenileme (F5/Reload) yapılmaz.
  - `fetch()` API ile sadece değişen veriler alınır. (Polling mechanism).
  - Ekrandaki projeler CSS Donanım Hızlandırması (Hardware Acceleration - `transform`, `opacity`) kullanılarak saniyede 60 kare (60fps) pürüzsüzlüğünde slayt olarak akar. DOM'u yoran `margin/left` gibi animasyonlar KESİNLİKLE yasaktır.

### 2.4. Yönetim Katmanı (Admin SPA - admin.html)
- **Paradigma:** Tek Sayfa Uygulaması (Single Page Application).
- **Güvenlik:** Rota (Endpoint) seviyesinde temel kimlik doğrulama (Basic Auth veya JWT) ile korunur. Yetkisiz IP'lerin veya personelin "Kule" verilerini değiştirmesi engellenir.
- **Veri Girişi:** İlişkisel tablolar yoktur. Form verisi doğrudan JSON ağacını manipüle edecek şekilde (Payload olarak) Backend'e iletilir.

## 3. Veri Kontratı (Data Interface)
TV Frontend'in Backend'den beklediği *kesin* ve *değiştirilemez* JSON şeması:

```json
{
  "system_status": 200,
  "last_updated": "ISO-8601-TIMESTAMP",
  "active_projects": [
    {
      "id": "OP-101",
      "name": "ezHEMS+ Veri Toplama",
      "deadline": "YYYY-MM-DD",
      "progress": 75,
      "status": "on_track | at_risk",
      "team": [
        {"name": "İsim", "role": "Rol", "avatar_url": "/static/..."}
      ]
    }
  ],
  "kitchen_heroes": [
    {
      "name": "İsim",
      "achievement": "Başarı Metni",
      "avatar_url": "/static/..."
    }
  ]
}