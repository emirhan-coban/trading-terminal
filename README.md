# NEXUS — Global Multi-Asset Trading Terminal v3

Kripto, ABD hisseleri, BIST hisseleri ve endeksler için araştırma ve paper-trading terminali. Ücretsiz veri kaynaklarının gecikme ve güncellik durumu her API yanıtında açıkça taşınır. Gerçek emir göndermez.

## Çalışan v3 çekirdeği

- Kanonik `instrument_id`: `crypto:binance:btcusdt`, `stock:xnas:aapl`, `stock:xist:thyao`
- Binance canlı kripto ve yfinance gecikmeli hisse/endeks adaptörleri
- `/api/v1` altında arama, quote, gerçek timeframe mumları, provider health ve websocket quote akışı
- Komisyon, kayma, buying power ve stale-data korumalı paper market emirleri
- Edge-triggered fiyat/değişim/hacim alarmları ve alarm olay geçmişi
- Çoklu varlık screener API'si ve enstrümana bağlı araştırma/journal notları
- Bekleyen limit/stop emirlerinde quote ile tetikleme ve emir iptali
- Sonraki bar açılışında işlem yapan maliyetli backtest motoru
- Profesyonel yoğun masaüstü çalışma alanı, komut paleti ve mobil uyarlama
- Supabase için kullanıcı izolasyonlu v3 şeması ve RLS politikaları
- Supabase token doğrulama katmanı (`REQUIRE_AUTH=true` ile zorunlu)
- Redis quote cache, sağlayıcı kesintisinde stale fallback ve arka plan quote worker'ı
- Supabase repository ile paper hesap/emir/pozisyon, alarm ve journal kalıcılığı
- Hisseler için değerleme/büyüme/kârlılık özeti, kripto için piyasa değeri/FDV/arz araştırma paneli
- Çoklu varlık temel veri karşılaştırma API'si ve SEC/KAP belge geçişleri
- Çeyreklik/yıllık gelir tablosu, bilanço ve nakit akışı özetleri
- Temettü/split kurumsal aksiyonları ve enstrüman bazlı kaynaklı haber akışı
- Eksik fiyat/kur bilgisini sıfır saymayan çoklu para birimli yatırım portföyü
- RSI, göreli hacim, momentum, volatilite ve trend metrikli gelişmiş screener
- Kaydedilebilir taramalar ve indikatör tabanlı edge-triggered alarmlar
- Portföy volatilite, drawdown, VaR, Sharpe, beta ve korelasyon analitiği
- Veri dışında iddia üretmeyen Gemini özeti ve deterministik AI fallback'i
- Tarayıcı ve portföy panellerinden enstrüman → araştırma → alarm → paper trade geçişi
- MA/EMA, RSI reversion, breakout, momentum ve VWAP reclaim stratejileri
- In/out-of-sample optimizasyon, walk-forward ve overfitting uyarıları
- CAGR, Sharpe, Sortino, Calmar, drawdown, expectancy, profit factor ve turnover
- Paper işlem günlüğü için gerçekleşen K/Z, maliyet ve enstrüman bazlı performans analitiği
- Binance trade/kline/depth websocket akışı, reconnect/backoff ve depth sequence resync
- ETF, forex ve emtia kanonik kimlikleri; ücretli veri ve broker adaptör sözleşmeleri
- Gerçek para emirlerini fail-closed tutan broker capability katmanı

## Yerel geliştirme

```bash
cd backend && ../.venv/bin/python -m uvicorn main:app --reload --port 8000
cd frontend && npm run dev
```

API dokümantasyonu: `http://localhost:8000/docs`

Başlıca v3 kaynakları: `/api/v1/instruments`, `/market`, `/screeners`, `/alerts`,
`/paper`, `/research/notes`, `/backtests` ve `/providers/health`.

## Doğrulama

```bash
./.venv/bin/python -m pytest backend/tests -q
cd frontend && npm test && npm run lint && npm run build
```

## Veri ve güvenlik

- Kripto: Binance public REST; `live` olarak etiketlenir.
- Hisse/endeks: yfinance; `delayed` olarak etiketlenir ve day-trading SLA'sı yoktur.
- `backend/schema_v3.sql` yeni kurulum şemasıdır. Uygulamadan önce Supabase projesinde gözden geçirilmelidir.
- Yerel geliştirmedeki paper kayıtları process belleğindedir; yeniden başlatmada silinir. Şema kalıcı paper emirleri için hazırdır.
- Production auth bağlantısında Supabase JWT doğrulaması zorunludur; local API kullanıcı kimliğini geliştirme kullanıcısına sabitler.
- Production ortamında `REQUIRE_AUTH=true` kullanılmalıdır; anonim local mod yalnız geliştirme içindir.
- Kalıcı çalışma için `PERSISTENCE=supabase` ve `backend/schema_v3.sql` şeması kullanılır.

Eski v2 modülleri geçiş referansı olarak `backend/` altında durur ancak v3 API tarafından kullanılmaz.
