# Twinquiry — Türkçe başlangıç

Twinquiry, aynı soruyu Claude ve Codex'e ayrı ayrı sorar, sonra modellerin birbirinin yanıtını eleştirmesini sağlar. Araştırma, teknik planlama ve model yanıtlarını karşılaştırma için kullanılır.

Bu repo bir skill paketi değil, **Python ile çalışan bir terminal aracıdır**. Claude Code veya Codex içinden aracı çalıştırmasını isteyebilirsin; normal terminalden de kullanabilirsin. Araştırma sırasında uygulama kodu üretmez.

## İlk deneme: hesap veya model kotası gerekmez

Python 3.10 veya üstüyle:

```bash
git clone https://github.com/eyupcimen/twinquiry.git
cd twinquiry
python3 -m twinquiry init sessions/deneme --question examples/question.md --source examples/requirements.md
python3 -m twinquiry run sessions/deneme --demo
```

Sonuç `sessions/deneme/report.md` dosyasındadır. Bu demo sentetik cevaplarla çalışır; gerçek araştırma veya model performansı kanıtı değildir. Windows'ta `python3` yerine `python` kullan.

## Gerçek araştırma

1. Claude Code ve Codex CLI kurulu ve hesaplarına bağlı olmalı.
2. `python3 -m twinquiry doctor` ile komut uyumluluğunu kontrol et.
3. Araştırma sorunu bir Markdown dosyasına yaz. Amacını, kısıtlarını, bildiklerini ve henüz karar vermediğin konuları belirt.
4. Varsa kaynak metinlerini ayrı dosyalara koy; bağlantılarını ve erişim tarihlerini de ekle.
5. Yeni bir araştırma başlat:

```bash
python3 -m twinquiry init sessions/arastirma --question examples/question.md --source examples/requirements.md --rounds 4
python3 -m twinquiry run sessions/arastirma --codex-model gpt-6-astra --claude-model sonnet
```

Buradaki dosya ve model isimlerini kendi seçimlerinle değiştir. Modelin planına dahil olduğunu ayrıca doğrula. Araç abonelik kotasını veya ek ücretli model erişimini garanti edemez.

Claude'un izin sorularını atlama seçeneğini açıkça kullanmak istersen `run` komutuna `--claude-skip-permissions` ekle. Bu seçenek Claude'a `--dangerously-skip-permissions` geçirir; araştırma araç listesini genişletmez.

## Tur ne demek?

İki bağımsız ilk cevaptan sonra bir turda **iki inceleme** yapılır: Claude, Codex'in cevabını; Codex, Claude'un cevabını inceler. Gerekirse ikisi de kendi cevabını düzeltir ve sonraki tur başlar.

Dört tur üst sınırdır. Erken onay varsa süreç biter. Dört tur en fazla **16 başarılı model çağrısı** demektir. Son turda kalan itirazlar gizlenmez. Eksik kanıt veya önemli kullanıcı kararı varsa sonuç `blocked` olabilir.

`--mode compare` yalnızca ilk cevapları ve karşılıklı incelemeyi toplar; cevapları değiştirmez. Modelleri aynı girdiler üzerinde kıyaslamak için uygundur.

`init` komutunda `--web` kullanırsan güncel web araştırmasına izin verilir. Modeller farklı kaynaklar bulabileceği için bu, aynı kanıta dayalı kontrollü bir karşılaştırma değildir.

## Sonuç nasıl okunur?

Rapor her iki cevabı, güçlü yanları, itirazları ve açık soruları içerir. `mutual_approval`, iki cevabın da karşı modelin incelemesinden geçtiğini söyler; cevapların aynı olduğu veya doğruluğunun kanıtlandığı anlamına gelmez.

Araştırma dosyaları yereldir ve Git tarafından yok sayılır. Repo public olsa bile kişisel araştırmaların otomatik olarak GitHub'a yüklenmez. Ancak gönderdiğin soru ve kaynak metinleri seçtiğin iki model sağlayıcısına iletilir.

İş yarıda kesilirse aynı `run` komutunu aynı seçeneklerle tekrar ver. Tamamlanan aşamalar tekrar çalışmaz; başarısız çağrıyı yeniden denemek tekrar kota tüketebilir.
