# 90-second demo script

Target: 85–90 seconds of speech, one screen, no dead air. Numbers are the real
ones from `data/nasa/analysis/evidence_cards.json` and `docs/acceptance_report.json`.

## Before you start (2 minutes, off camera)

```bash
cd backend && python run.py            # app on http://127.0.0.1:8000/app/
python warm_cache.py                   # so no click waits on a cold job
```

Open `http://127.0.0.1:8000/app/?lang=ar&region=nile_corridor&variable=air_temperature&autorun=1`
and leave it loaded. If the venue network fails, open
`dist/offline/index.html` — same screen, precomputed, banner says offline.

## Script

| Time | On screen | Say (Arabic) |
|---|---|---|
| 0–8s | Map of the Nile corridor, cells coloured | «كل تقرير عن المناخ بيقول: المتوسط ارتفع. إحنا بنسأل سؤال تاني: **المتوسط ده بيخفي إيه؟**» |
| 8–20s | Point at the grid + legend | «دي خلايا NASA حقيقية — MERRA-2 بحرارة الهواء، GLDAS برطوبة التربة، GPM بالمطر، وMODIS بالغطاء النباتي. أربع متغيرات × ثلاث نوافذ × ٢٤ سنة، من غير أي استيفاء.» |
| 20–35s | Card: +0.0309 K/yr, CI, p=0.00525 | «وادي النيل: التغير المقدّر **+0.031 درجة في السنة**، مجال ثقة من +0.0096 إلى +0.0528، وقيمة p = 0.005. ده تحت الحد المجمّد 0.05 — دليل ضد فرضية عدم الاتجاه، **مش احتمال إن الاتجاه حقيقي**.» |
| 35–50s | Chart + Spin It rows | «السلسلة الشهرية والخط الأزرق محسوبين على الخادم. ولو غيّرنا الفترة، Spin It بتعرض ١١ نافذة مسجّلة مسبقًا — عشان محدش يختار نافذة بعد ما يشوف النتيجة.» |
| 50–62s | Click «قارن النوافذ» | «نفس المتغير، نفس الطريقة: النيل +0.031 وp=0.005، المغرب +0.031 بس p=0.158 **غير حاسم**، الساحل −0.013 وp=0.21. يعني الاتجاه مش واحد في كل مكان — وده بالظبط اللي المتوسط بيخفيه.» |
| 62–74s | Reality Check: press «ارتفاع» | «Reality Check: توقعت ارتفاع؟ البيانات تدعم التوقع في النيل، ومش بتدعمه في الساحل. ومفيش هنا أي كلمة عن «السبب».» |
| 74–85s | Click «الإيصال JSON» | «وكل رقم معاه إيصال: بصمات البيانات، أرقام الـgranules، إعدادات الطريقة، والـseed. أي حد يقدر يعيد نفس الحساب.» |
| 85–90s | Close on the map | «كاشف الاتجاهات: مش بنقول لك الدنيا بتسخن — بنوريك **فين** و**بأي دليل**، وبنسيبك تشك في استنتاجك.» |

## If something breaks on stage

1. **Server died** → open `dist/offline/index.html`. Everything still works; the banner states it is a precomputed snapshot.
2. **Cold analysis is slow (4–5s)** → say the number out loud: «التحليل بياخد أربع ثواني على بيانات ٢٤ سنة». Do not pretend it is instant.
3. **A variable fails** → switch to `air_temperature` in the Nile window; it is the case with the strongest evidence and the clearest wording.

## Things you must NOT say

- «٩٥٪ احتمال إن الاتجاه حقيقي» — wrong reading of a p-value.
- «البيانات بتثبت إن السبب هو…» — no causal claim.
- «NDVI معناها المحصول» — it is a greenness index.
- «صفر رطوبة» for a missing cell — missing is not zero.
