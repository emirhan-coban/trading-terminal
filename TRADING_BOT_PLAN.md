# NEXUS → Ücretsiz altyapılı trading bot planı

Tarih: 5 Eylül 2026. Kapsam: mevcut çalışma ağacının statik incelemesi ve uygulama planı. Uygulama kodu değiştirilmedi; testler çalıştırılmadı. Mevcut commit edilmemiş değişiklikler korundu.

## Karar ve maliyet sınırı

İlk ürün: tek kullanıcı için mevcut bilgisayarda çalışan, BTC/USDT ve ETH/USDT spot piyasalarını izleyen, 1 saatlik kapanmış mumlarla karar veren otomatik paper bot. Aynı motor daha sonra testnet ve isteğe bağlı gerçek hesap adaptörleriyle çalışacak. İlk sürüm kaldıraç, short, grid, martingale ve AI ile emir üretimi içermeyecek.

Yazılım lisansı, piyasa verisi aboneliği ve sunucu kirası için ek ödeme gerektirmeyen bir kurulum hedefleniyor. Mevcut bilgisayar, internet, depolama ve elektrik kullanılır. Bilgisayar kapalı veya uykudaysa yerel bot çalışmaz. Kesintisiz ücretsiz bulut hizmeti varsayılmayacak.

Gerçek işlemlerde sermaye, komisyon, alış-satış farkı ve kayma vardır; bunlar sıfır maliyetli yazılım ile ortadan kalkmaz. Ücretsiz ve risksiz test için sanal bakiye kullanılır. Bu plan kârlılık iddiası içermez.

## İncelenen mevcut yapı

| Bölüm | Mevcut durum | Dönüşümde kullanım |
|---|---|---|
| `frontend/components/TerminalWorkspace.tsx` | Next.js/React terminali, araştırma, paper emir ve backtest panelleri | Bot kontrol ve izleme ekranı |
| `backend/main.py`, `terminal/api.py` | FastAPI, `/api/v1`, REST ve WebSocket | Kontrol API'si ve salt okunur olay yayını |
| `terminal/providers.py` | Binance public REST, Yahoo/yfinance | Kripto adaptörü korunur; tarihsel veri genişletilir |
| `terminal/market_stream.py` | Trade, kline ve depth; yeniden bağlanma | Paylaşılan bağımsız veri tüketicisine taşınır |
| `terminal/backtest_engine.py` | MA, RSI, breakout, momentum, VWAP; komisyon/kayma | Ortak strateji motorunun test ortamı |
| `terminal/paper.py` | Sanal bakiye, emir, pozisyon, OCO/bracket ve kısmi dolum | Hataları düzeltilip ortak broker arayüzüne bağlanır |
| `terminal/brokers.py` | Broker sözleşmesi; gerçek işlem kapalı | Paper/testnet/live adaptörleri için başlangıç |
| `terminal/persistence.py` | Bellek veya Supabase | Yerel SQLite seçeneği eklenir |
| `terminal/worker.py` | Yalnızca 15 saniyelik quote cache güncellemesi | Ayrı bot çalışma servisi gerekir |
| `backend/tests` | Emir, backtest, veri ve kalıcılık testleri | Yeni davranışların regresyon temeli |

## Önce düzeltilmesi gereken noktalar

1. **Emir çalışması istemci isteklerine bağlı.** `api.py` içindeki quote isteği ve WebSocket akışı `paper_broker.process` çağırıyor. Tarayıcıdan bağımsız merkezi yürütücü yok. Birden fazla izleyicinin aynı olayları tekrar işlemesini de önlemek gerekiyor.
2. **Yeniden başlatma eksik.** `hydrate_paper` pozisyon ve bakiyeyi yükler; bekleyen emirleri çalışma belleğine getirmez. WebSocket üzerinden dolumda hesap ve pozisyon kalıcılığı REST emir yoluyla aynı bütünlükte güncellenmiyor. Bakiye, emir, dolum, pozisyon ve olay tek veritabanı işlemiyle kaydedilmeli.
3. **Backtest yıllıklaştırması hatalı varsayım kullanıyor.** Sharpe, Sortino ve CAGR hesabında 252 bar/yıl sabit. Kripto ve saatlik veride takvim/zaman aralığı dikkate alınmalı. Walk-forward yüzdeleri topluyor; birleşik performans sermaye eğrisi üzerinden hesaplanmalı. Test pencereleri geçmiş eğitim verisiyle indikatör ısınması almalı; geleceği görmemeli.
4. **Strateji durumu netleştirilmeli.** RSI kolunda sıfırla oluşturulmuş seri `ffill` ile pozisyon tutma davranışı kazanmıyor. Nötr bölgedeki çıkış ve yeniden girişler açık bir hedef pozisyon sözleşmesiyle tanımlanmalı. README'deki EMA iddiasına karşılık aktif `_signals` fonksiyonunda ayrı EMA stratejisi yok.
5. **Paper emir doğruluğu.** Stop-limit tetiklenince limit kontrolü yapılmadan yürütülüyor. Limit emirleri kayma nedeniyle limitin dışına dolabilir. Kullanılabilir hacim bir olayda birden çok emir arasında tüketilmiyor. Açık emirler için nakit/varlık rezervasyonu ve OCO kısmi dolum davranışı tanımlanmalı.
6. **Canlı veri disiplini.** Paper fiyat tazeliği 20 dakikaya kadar kabul ediliyor. Botun yeni emir tazelik eşiği daha sıkı ve yapılandırılabilir olmalı. REST mumlarında kapanış filtresi yok; WebSocket'teki `closed` bilgisi kullanılmalı. Eksik/tekrarlı mum, zaman birimi ve timeframe eşlemeleri doğrulanmalı.
7. **Yerel kurulum tam bağımsız değil.** Backend yerel kullanıcı destekliyor ancak `frontend/lib/supabase.ts` istemciyi ortam değişkenleriyle koşulsuz oluşturuyor. SQLite seçeneğine ek olarak Supabase anahtarı olmadan açılan yerel giriş modu gerekiyor.
8. **Çoklu varlık muhasebesi hazır sayılmamalı.** Paper motoru kullanıcı başına tek nakit havuzu kullanıyor. İlk bot tek USDT hesapla sınırlandırılır; forex/futures için teminat, kontrat çarpanı, kur, short ve finansman modelleri ayrıca geliştirilir.

## Piyasa seçimi

| Piyasa | Bu projedeki uygunluk | Karar |
|---|---|---|
| Kripto spot | Canlı Binance bağlantısı ve spot benzeri paper muhasebesi mevcut; kamuya açık geçmiş veri bulunuyor | İlk sürüm |
| Forex | EUR/USD kimliği var fakat veri Yahoo adaptöründen geliyor; broker fiyatı, spread, seans ve finansman entegrasyonu eksik | Broker ve hesap uygunluğu belirlendikten sonra ikinci aşama |
| Endeks | SPX gösterge verisi var; göstergeyi doğrudan alıp satacak emir ürünü yok | Önce ETF/futures/CFD ürünü ve broker seçilmeli; üçüncü aşama |

Binance public veri uçları kimlik doğrulaması gerektirmeyen veri erişimi sunuyor. Tarihsel arşiv günlük/aylık dosyalar sağlıyor; arşivde 2025 ve sonrası spot zaman damgalarının mikrosaniye olması içe aktarımda dikkate alınmalı. Kaynaklar: [Binance REST belgeleri](https://developers.binance.com/en/docs/products/spot/rest-api), [resmî tarihsel veri deposu](https://github.com/binance/binance-public-data).

Forex için OANDA v20 belgelerinde demo/gerçek hesap ve token koşulları var; bu, kullanıcı için hesap açılabildiği veya her bölgede erişimin ücretsiz olduğu anlamına gelmez. Broker fiyat akışı seçimi hesap erişimi doğrulandıktan sonra yapılır. Kaynaklar: [OANDA giriş](https://developer.oanda.com/rest-live-v20/introduction/), [demo ortamı](https://developer.oanda.com/rest-live-v20/development-guide/).

Endeks vadeli işlemlerinde gerçek zamanlı veri lisans ve ücretleri ayrıca değerlendirilir; ücretsiz terminal verisini emir verisi olarak varsaymayız. Kaynak: [CME piyasa verisi politikaları](https://www.cmegroup.com/market-data/license-data/market-data-policy-education-center.html).

## Hedef mimari

Akış: veri → kapanmış mum → strateji → hedef pozisyon → risk kontrolü → emir niyeti → broker → dolum → kalıcı kayıt → terminal.

- Python/FastAPI ve mevcut React arayüzü korunur.
- `terminal/bot/runner.py`: bağımsız olay döngüsü, heartbeat, duraklatma ve toparlanma.
- `terminal/bot/strategies.py`: backtest/paper/testnet/live için ortak ve sürümlü strateji sözleşmesi.
- `terminal/bot/risk.py`: pozisyon büyüklüğü, günlük zarar ve toplam maruziyet sınırları.
- `terminal/bot/execution.py`: emir durum makinesi, tekrarları önleme, iptal ve broker mutabakatı.
- `terminal/bot/storage.py`: SQLite WAL; konfigürasyon, çalışma geçmişi, mum imleci, sinyal, emir, dolum, bakiye, pozisyon ve olay kayıtları.
- `terminal/bot/api.py`: oluşturma, başlatma, duraklatma, durdurma, durum ve olay uçları.
- Yerel kurulumda tek emir yazıcısı ve süreç kilidi kullanılır. UI/API değişiklikleri bu yazıcıya komut verir; izleme bağlantıları emir yürütmez.
- `(bot_id, strategy_version, instrument_id, timeframe, candle_close_time, action)` benzersizliği sinyal tekrarını önler. Emir niyeti gönderimden önce kaydedilir. Yanıt alınamayan emir körlemesine tekrar gönderilmez; kalıcı istemci emir kimliğiyle brokerden sorgulanır.
- İlk sürümde Redis ve Supabase zorunlu olmaz. LLM/Gemini çağrısı emir hattında yer almaz. Yerel API yalnız localhost üzerinde çalışır; hesap anahtarları frontend'e ve kayıtlara taşınmaz.

## Uygulama sırası ve bitiş ölçütleri

### 1. Temeli düzelt ve kalıcılaştır

Yukarıdaki paper/backtest hatalarını düzelt; SQLite ve yerel giriş modunu ekle. Para ve miktar işlemlerinde Decimal, borsa adım/büyüklük sınırları kullan. Mevcut testleri çalıştır ve yeni hata senaryolarını ekle.

**Bitiş ölçütü:** yeniden başlatmadan sonra bakiye, pozisyon ve açık emir aynı; stop-limit limit dışında dolmuyor; işlem kayıtları yarım kalmıyor.

### 2. Tarihsel veri ve ortak strateji

BTC/USDT ve ETH/USDT için mümkünse en az iki yıllık 1h veri yükle; checksum, UTC, eksik mum ve yinelenen kayıt kontrolü yap. Son 1000 mum sınırını arşiv/sayfalama ile kaldır. Tek referans strateji olarak mevcut MA kesişimini ortak motorla çalıştır; aynı veri dizisi aynı sinyalleri üretmeli.

İlk parametreler deney başlangıcıdır, kazandırdığı kabul edilmez. Eğitim, doğrulama ve son dokunulmamış test dönemini zaman sırasıyla ayır. Ücret ve kaymayı yükselten stres senaryolarını; nakitte kalma ve al-tut karşılaştırmasını raporla. Son test sonucu görüldükten sonra o döneme göre ayar yapma.

**Bitiş ölçütü:** kapanmamış mum emir üretmiyor; backtest ve kayıtlı veri tekrar oynatımı aynı sinyalleri veriyor; metrikler gerçek zaman aralığına uygun.

### 3. Tarayıcıdan bağımsız paper bot

Ortak veri tüketicisi, mum kapanışı işleme, risk motoru ve paper brokeri bağla. Kopuşta eksik mumları tamamla; geçmiş mumları indikatörleri toparlamak için kullan, gecikmiş giriş emirlerini peş peşe gönderme.

Başlangıç risk konfigürasyonu paper deneyidir: pozisyon başına en fazla %10 sermaye, toplam %20 maruziyet; stop mesafesine göre işlem başına en fazla %0,25 planlanan kayıp; günlük %1 kayıpta yeni girişleri durdur. Pozisyon büyüklüğü nakit ve borsa minimumlarıyla sınırlandırılır. Fiyat sıçramalarında gerçekleşen kayıp stop hedefini aşabilir.

**Bitiş ölçütü:** tarayıcı kapalıyken çalışıyor; aynı mum iki kez geldiğinde tek emir; ikinci süreç açıldığında ikinci yazıcı başlamıyor; eski veri yeni girişleri durduruyor; stop/koruyucu çıkışlar yeni giriş duraklatmasından bağımsız işliyor.

### 4. Bot kontrol ekranı ve gözlem

Terminale bot listesi, paper/testnet/live rozeti, strateji ayarı, son sinyal gerekçesi, veri zamanı, heartbeat, net K/Z, düşüş, emirler ve hata kaydı ekle. “Yeni girişleri duraklat”, “botu durdur” ve “pozisyonları kapat” ayrı davranışlardır; stop korumalarının hangi durumda devam ettiği açıkça gösterilir.

**Bitiş ölçütü:** emir nedeni ve uygulanan risk kontrolü kayıttan açıklanabiliyor. En az 2–4 haftalık paper gözlem hedeflenir; yeterli işlem oluşmazsa süre uzatılır. Bu süre tek başına strateji başarısını kanıtlamaz.

### 5. Testnet emir entegrasyonu

İmzalı emir, iptal, bakiye, açık emir, kullanıcı dolum akışı ve yeniden başlatma mutabakatını ekle. Minimum emir tutarı ve miktar/fiyat adımları güncel borsa bilgisinden alınır. Zaman aşımı, oran limiti, kısmi dolum, iptal/dolum yarışı ve kopuş senaryoları test edilir.

Testnet sanal varlık kullanır ve dönemsel sıfırlanabilir. Sıfırlanma algılandığında bot durup hesap durumunu yeniden kurmalı. Testnet performansı gerçek piyasa kârlılığı ölçümü olarak kullanılmaz. Kaynak: [Binance Spot Test Network](https://github.com/binance/binance-spot-api-docs/blob/master/testnet/general-info.md).

**Bitiş ölçütü:** gönderim cevabı kaybolduğunda tekrar emir oluşmuyor; borsa ve yerel kayıtlar uzlaşıyor; testnet sıfırlanması açıklanabilir biçimde işleniyor.

### 6. İsteğe bağlı gerçek hesap

Yalnız ayrı bir canlı kullanım talebi ve uygun hesap sağlandığında etkinleştirilir. Anahtarlar yerel güvenli depoda tutulur; yalnız gerekli işlem izinleri kullanılır, para çekme yetkisi verilmez. Koruyucu emirler desteklendiğinde borsada tutulur; bilgisayar kapanınca yerel stop çalışacağı varsayılmaz. Gerçek komisyonlar hesaptan alınır ve muhasebeye işlenir. İlk çalışma tek parite ve borsa minimumlarına uygun sınırlı bakiye ile yapılır.

**Bitiş ölçütü:** açık emir, bakiye ve dolum mutabakatı; çalışan risk durdurucusu; kesinti/başlatma prosedürü; canlı hesabın ücret, ürün ve erişim koşulları doğrulanmış.

## Sonraki genişleme

Forex için önce demo broker adaptörü, bid/ask fiyatlama, 24/5 takvim, rollover/finansman, lot ve teminat modeli. Endeksler için seçilen ETF/futures/CFD'nin gerçek ürün kimliği, takvim, kontrat çarpanı, vade/roll ve veri hakları. Bu aşamalar spot botun güvenilir çalışması kanıtlandıktan sonra ayrı kapsam olarak ele alınır.

İlk geliştirilecek somut paket: **SQLite kalıcılığı + paper/backtest doğruluk düzeltmeleri + bağımsız 1h kripto paper runner**. Ücretsiz altyapı hedefi için en kısa ve denetlenebilir yol budur.
