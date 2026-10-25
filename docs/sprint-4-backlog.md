# Sprint 4 Backlog — Managed Generation وBeta Credits

## 1. افتراضات التخطيط

هذه الخطة مبنية على وضع الريبو الحالي، حيث إن مسار التوليد يعتمد على BYOK ومفاتيح داخل `provider_keys`. هدف السبرنت هو نقل النظام إلى **Managed Generation** بمفتاح backend، تشغيل توليد الصور والكابشنز، إضافة حد مجاني مؤقت، وتسجيل الاستهلاك والتكلفة دون تفعيل الدفع.

لأن أسماء أعضاء الفريق غير موجودة في ملفات المشروع، تم توزيع العمل حسب الأدوار التي استخدمها الفريق سابقًا. يستبدل قائد الفريق أسماء الأدوار بأسماء الأشخاص الفعلية دون تغيير المسؤوليات أو ترتيب التنفيذ.

### الأدوار

| الرمز | الدور | المسؤولية الأساسية |
|---|---|---|
| PO | Samar / Product & Integration Owner | تثبيت قرارات المنتج، قبول السيناريوهات، إدارة الأولويات، اختبار المسار الكامل |
| BE | Backend & AI Engineer | managed provider، generation/caption APIs، errors، idempotency |
| DB | Database & Supabase Engineer | migrations، credit ledger، usage، RLS، Storage، RPCs |
| FE | Frontend Engineer | إزالة BYOK من الواجهة، عرض الرصيد والخطة والحالات |
| QA | QA & DevOps Engineer | test matrix، staging، smoke tests، secrets، deploy، monitoring |

## 2. قرار Beta قبل بدء التنفيذ

في Beta نستخدم خطة واحدة فقط اسمها `Beta`. يحصل المستخدم على **10 image credits شهريًا**. كل توليد صورة يستهلك credit واحدًا. الكابشن الأول للصورة الناجحة يكون داخل العملية نفسها ولا يخصم رصيدًا إضافيًا في النسخة الأولى؛ أما regenerate للكابشن فيُسجّل كاستهلاك داخلي منفصل، لكن لا يُخصم من المستخدم خلال Beta إلا إذا قرر الفريق غير ذلك قبل بدء T3. هذا القرار يمنع أن تصبح تجربة الاستخدام مربكة.

لا يوجد دفع، ولا Stripe، ولا مطالبة ببيانات مالية. مع ذلك، تُبنى الجداول باسم plans/subscriptions/credit ledger بحيث يمكن إضافة الدفع لاحقًا دون إعادة تصميم النظام.

حدود الحماية المقترحة: 10 image generations لكل مستخدم في فترة الخطة، 3 طلبات توليد في الدقيقة لكل مستخدم، وطلب توليد واحد نشط لكل Brand. هذه الحدود مستقلة عن بعضها: الرصيد يحمي التكلفة الشهرية، والـ rate limit يحمي الخدمة من الضغط، وقفل الطلب يمنع double-click والتزامن.

## 3. ملخص الجهد والمدة

التقديرات أدناه هي **وقت عمل فعلي** وليست مدة تقويمية. مدة السبرنت المقترحة عشرة أيام عمل، مع تشغيل أجزاء متوازية بعد إنهاء العقود الأساسية.

| المسار | المسؤول | ساعات العمل | مدة تقويمية متوقعة | الناتج |
|---|---|---:|---:|---|
| Product/Integration | PO | 18–24 ساعة | موزعة على كامل السبرنت | قرارات، قبول، smoke test، توثيق |
| Managed backend | BE | 34–42 ساعة | 6–7 أيام | توليد صورة وكابشن بدون BYOK |
| Database/Storage | DB | 32–40 ساعة | 5–6 أيام | schema، ledger، usage، storage policies |
| Frontend | FE | 26–34 ساعة | 5–6 أيام | UX جديد بدون مفاتيح |
| QA/DevOps | QA | 28–36 ساعة | 6–8 أيام | staging، tests، deploy، failure matrix |
| مراجعة مشتركة | الجميع | 12–16 ساعة جماعية | يومان متداخلان | إصلاحات وقرار release |

**التقدير الكلي:** 138–176 ساعة موزعة على الفريق، وليس على شخص واحد. إذا كان الفريق يعمل part-time، فالمدة الواقعية 10–12 يوم عمل. إذا كان شخص واحد ينفذ كل شيء، فالتقدير يصبح 4–5 أسابيع، وهذا غير مناسب لسبرنت قصيرة.

## 4. Backlog تفصيلي

### Phase 0 — تثبيت العقد والبيئة

#### S4-001 — تثبيت قرارات Beta والعقود

**المسؤول:** PO، بمراجعة BE وDB وFE وQA.  
**التقدير:** 3 ساعات PO + ساعتان مراجعة مشتركة.  
**الأولوية:** P0.  
**الاعتماديات:** لا يوجد.

**التفاصيل:** تثبيت provider الأول، model names، عدد credits، هل الكابشن داخل العملية، حدود rate limit، سياسة إرجاع الرصيد عند الفشل، retention للصور، أسماء env vars، ورسائل الواجهة العربية والإنجليزية. تحديث `docs/sprint-4-plan.md` بهذا القرار.

**معيار التسليم:** لا توجد قرارات مفتوحة تمنع backend أو database من العمل، وكل الفريق يعرف ما الذي يعتبر نجاحًا وفشلًا.

#### S4-002 — تجهيز staging secrets وprovider smoke check

**المسؤول:** QA، بمساعدة BE.  
**التقدير:** 4–6 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-001.

**التفاصيل:** إضافة أسرار backend فقط، التأكد أنها لا تصل إلى frontend build، فحص صلاحية key والموديل والحساب، وتجهيز staging database/storage. لا يتم طباعة السر في logs.

**معيار التسليم:** health check يثبت أن الإعدادات موجودة دون كشف قيمتها، وprovider test يعيد استجابة فعلية أو خطأ موحدًا قابلًا للتشخيص.

### Phase 1 — Managed Generation

#### S4-010 — Backend managed provider configuration

**المسؤول:** BE.  
**التقدير:** 6–8 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-001، S4-002.

**الملفات المتوقعة:** `backend/app/config.py`، خدمة provider جديدة، `.env.example`.

**التفاصيل:** إضافة `MANAGED_IMAGE_PROVIDER`, `MANAGED_IMAGE_MODEL`, `MANAGED_TEXT_PROVIDER`, `MANAGED_TEXT_MODEL` ومفاتيح server-side. إنشاء resolver لا يقرأ provider أو key من request body. توحيد image/text provider interface. منع تسريب السر في exception أو log.

**معيار التسليم:** اختبار يثبت أن request لا يستطيع تغيير `api_key` أو `model`، وأن backend يختار الإعدادات من environment فقط.

#### S4-011 — تحويل image generation إلى Managed Generation

**المسؤول:** BE.  
**التقدير:** 10–12 ساعة.  
**الأولوية:** P0.  
**الاعتماديات:** S4-010.

**التفاصيل:** تعديل `POST /brands/{brand_id}/generate` بحيث لا يعتمد على `provider_keys` ولا يحتاج provider من المستخدم. يبقى provider/model في سجل generation كـ metadata يحدده backend. الحفاظ على prompt composer، watermark، resize، وحالات `pending/processing/succeeded/failed`.

**معيار التسليم:** مستخدم بلا أي provider key يستطيع إنشاء صورة من خلال request لا يحتوي credential. المستخدم لا يستطيع تغيير provider/model بالتلاعب بالـ JSON.

#### S4-012 — تحويل caption generation إلى Managed Generation

**المسؤول:** BE.  
**التقدير:** 6–8 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-010، ويفضل S4-011.

**التفاصيل:** تعديل caption endpoint ليستخدم managed text provider، مع المحافظة على وراثة اللغة والمنصة والـ brief من generation. فصل فشل الكابشن عن نجاح الصورة.

**معيار التسليم:** يمكن إنشاء caption لصورة ناجحة بلا provider key للمستخدم، وفشل الكابشن لا يغير حالة الصورة إلى failed.

#### S4-013 — حفظ caption history

**المسؤول:** DB مع BE.  
**التقدير:** DB 4 ساعات، BE 5–6 ساعات.  
**الأولوية:** P1.  
**الاعتماديات:** S4-012.

**التفاصيل:** إنشاء `generation_captions`، حفظ اللغة والمنصة والنص والـ hashtags والـ keywords والموديل وprompt version وtimestamps. إضافة read endpoint أو توسيع detail response حسب التصميم الحالي.

**معيار التسليم:** regenerate ينشئ سجلًا جديدًا ولا يمسح السجل القديم، والواجهة تستطيع عرض آخر caption محفوظ.

### Phase 2 — Database, Credits, Usage

#### S4-020 — Schema للخطط والاشتراكات

**المسؤول:** DB.  
**التقدير:** 6–8 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-001.

**الجداول:** `plans`, `subscriptions`.

**التفاصيل:** seed لخطة `beta` مع 10 credits، subscription تلقائي للمستخدم الجديد أو عند أول generation، status وperiod dates، وحقول Stripe nullable للمستقبل. عدم إضافة أي payment requirement.

**معيار التسليم:** كل مستخدم جديد أو قديم يمكن ربطه بخطة Beta واحدة فقط فعالة، ولا يمكن أن يحصل على خطتين فعالتين بالخطأ.

#### S4-021 — Credit ledger وatomic reserve

**المسؤول:** DB، مع BE للمسار.  
**التقدير:** 10–12 ساعة.  
**الأولوية:** P0.  
**الاعتماديات:** S4-020.

**الجداول/RPC:** `credit_ledger` مع RPC أو transaction للحجز الذري.

**التفاصيل:** عمليات `grant`, `reserve`, `consume`, `release`, `adjustment`، و`idempotency_key`. منع حجز credit إذا الرصيد غير كافٍ. معالجة طلبين متزامنين لنفس المستخدم دون negative balance.

**معيار التسليم:** اختبار concurrency أو equivalent database test يثبت أن آخر credit لا يُحجز مرتين، وإعادة نفس idempotency key لا تخصم مرتين.

#### S4-022 — Usage and cost records

**المسؤول:** DB مع BE.  
**التقدير:** 7–9 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-010، S4-021.

**الجداول:** `generation_usage`.

**التفاصيل:** تسجيل user، generation، operation، provider، model، status، credits charged، estimated provider cost، provider request ID، timestamps. لا نحفظ API key ولا raw authorization headers. يحدد BE متى يسجل reserve/consume/release.

**معيار التسليم:** كل محاولة توليد لها usage record حتى عند الفشل، ويمكن للإدارة معرفة هل الفشل قبل provider أم بعده.

#### S4-023 — Quota وrate limit في API

**المسؤول:** BE، مع QA.  
**التقدير:** 6–8 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-021.

**التفاصيل:** فحص الرصيد قبل التوليد، rate limit لكل user/IP، generation lock لكل Brand، ورسائل مستقلة لـ `INSUFFICIENT_CREDITS`, `RATE_LIMITED`, `GENERATION_IN_PROGRESS`.

**معيار التسليم:** تغيير brand ID لا يتجاوز quota، double-click لا يولد عمليتين، ورسالة الرصيد غير الكافي واضحة وقابلة للعرض في الواجهة.

#### S4-024 — Recovery للعمليات العالقة

**المسؤول:** BE + QA.  
**التقدير:** 5–7 ساعات.  
**الأولوية:** P1.  
**الاعتماديات:** S4-021، S4-022.

**التفاصيل:** timeout واضح، تحويل processing القديمة إلى failed، release للحجز مرة واحدة، وعدم ترك credit محجوزًا إلى الأبد. إذا لم نستخدم worker بعد، نبدأ endpoint/admin script آمن ثم نضيف job لاحقًا.

**معيار التسليم:** generation متوقفة منذ أكثر من threshold لا تبقى processing ولا تظل credits محجوزة بلا تفسير.

### Phase 3 — Storage and Security

#### S4-030 — Storage path وsigned URLs

**المسؤول:** DB، مع BE.  
**التقدير:** 8–10 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-011.

**التفاصيل:** اعتماد مسار `users/{user_id}/brands/{brand_id}/generations/{generation_id}/image.webp`، حفظ `image_path`، التحقق من MIME والحجم، إنشاء signed URLs قصيرة، وعدم الاعتماد على provider URL.

**معيار التسليم:** المستخدم يرى ويدownload صورة من signed URL، مستخدم آخر لا يستطيع تخمين أو قراءة object، وفشل storage لا يسجل generation ناجحة.

#### S4-031 — RLS وownership audit

**المسؤول:** DB.  
**التقدير:** 6–8 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-020 إلى S4-030.

**التفاصيل:** سياسات للجداول الجديدة، فحص ownership عبر user/brand/generation، منع authenticated من قراءة admin views، ومراجعة service-role usage داخل backend. إضافة tests لمحاولات cross-user/cross-brand.

**معيار التسليم:** لا يستطيع مستخدم قراءة credits أو captions أو images أو usage لمستخدم آخر بتغيير UUID.

#### S4-032 — Secrets and logging audit

**المسؤول:** QA/DevOps مع BE.  
**التقدير:** 4–6 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-010، S4-011.

**التفاصيل:** فحص logs، Docker/Render env، network requests، error responses، وfrontend bundles. البحث الآلي عن أسماء الأسرار أو Authorization headers.

**معيار التسليم:** لا يظهر المفتاح في browser network، compiled frontend، logs، database rows، أو رسائل الخطأ.

### Phase 4 — Frontend UX

#### S4-040 — إزالة BYOK من navigation والمسار العام

**المسؤول:** FE.  
**التقدير:** 6–8 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-001.

**التفاصيل:** إزالة رابط Keys، صفحة add key، provider selector، `use-active-keys`, رسائل “أضف مفتاحك”، وشرط `hasActiveKey`. legacy endpoint يمكن إبقاؤه مؤقتًا backend-only أو إرجاع `410 BYOK_DISABLED`.

**معيار التسليم:** لا يوجد اختيار بين BYOK وManaged في أي route أو component أو network request.

#### S4-041 — تحديث Generator UX

**المسؤول:** FE.  
**التقدير:** 7–9 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-011، S4-040.

**التفاصيل:** زر التوليد يعتمد على اكتمال brief فقط، إضافة نص “التوليد مُدار من TRENDY AI”، حالات loading/error/success، ورسائل quota/rate limit/provider failure. عدم عرض provider choice للمستخدم.

**معيار التسليم:** user journey من brief إلى image يعمل بدون صفحة keys، والرسائل العربية والإنجليزية مفهومة.

#### S4-042 — Plan and credits display

**المسؤول:** FE.  
**التقدير:** 6–8 ساعات.  
**الأولوية:** P1.  
**الاعتماديات:** S4-020، S4-021، S4-023.

**التفاصيل:** hook وendpoint لعرض الخطة والرصيد، بطاقة Beta، `remaining / total`, وحالة insufficient credits. لا زر دفع ولا checkout.

**معيار التسليم:** الرصيد يتحدث بعد success، لا يتغير بعد failed request الذي تم release له، وتظهر Beta بدل اشتراك مدفوع.

#### S4-043 — Caption history UI

**المسؤول:** FE.  
**التقدير:** 5–7 ساعات.  
**الأولوية:** P1.  
**الاعتماديات:** S4-013.

**التفاصيل:** عرض الكابشن المحفوظ، regenerate، copy، edit محلي قبل النسخ، وحالة فشل لا تخفي الصورة.

**معيار التسليم:** regenerate لا يعيد توليد الصورة، والنسخة السابقة لا تضيع.

### Phase 5 — Testing, Deployment, Acceptance

#### S4-050 — Backend automated tests

**المسؤول:** BE، مع QA.  
**التقدير:** 8–10 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-010 إلى S4-024.

**التغطية:** managed key resolution، body tampering، success/failure، quota، idempotency، rate limit، caption، provider errors، usage status، release/consume.

**معيار التسليم:** كل tests الجديدة تمر، والاختبارات القديمة لا تتراجع.

#### S4-051 — Database/RLS verification

**المسؤول:** DB + QA.  
**التقدير:** 6–8 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-020 إلى S4-032.

**التغطية:** migrations على staging، seed، atomic credit tests، cross-user access، storage policies، signed URL expiry.

**معيار التسليم:** `supabase db push` أو آلية المشروع تنجح، والـ schema الفعلي مطابق للكود.

#### S4-052 — Frontend lint/build/component tests

**المسؤول:** FE + QA.  
**التقدير:** 5–7 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-040 إلى S4-043.

**معيار التسليم:** lint/build/tests تمر، ولا توجد imports أو routes ميتة من BYOK، والـ UI responsive بالعربي والإنجليزي.

#### S4-053 — End-to-end smoke test على staging

**المسؤول:** QA، PO يشارك في القبول.  
**التقدير:** 6–8 ساعات.  
**الأولوية:** P0.  
**الاعتماديات:** S4-050 إلى S4-052.

**السيناريو:** signup/login → create brand → complete kit → brief → generate image → save storage → generate caption → edit/copy → history → download → failed caption → retry → quota exhausted.

**معيار التسليم:** السيناريو كاملًا يعمل من متصفح نظيف وبـ account تجريبي، مع حفظ request IDs للفشل.

#### S4-054 — Release decision وhandover

**المسؤول:** PO، بموافقة QA وBE وDB وFE.  
**التقدير:** 4–6 ساعات.  
**الاعتماديات:** S4-053.

**التفاصيل:** مراجعة acceptance criteria، known issues، rollback plan، env checklist، وملاحظات التشغيل. لا يتم الإعلان عن الدفع أو الاشتراكات المدفوعة.

**معيار التسليم:** قرار واضح: Ready for Beta أو Blocked مع أسباب قابلة للتنفيذ.

## 5. توزيع المسؤولية النهائي

| المسار | منفذ رئيسي | مراجع | صاحب القرار/القبول |
|---|---|---|---|
| Provider config وimage/caption backend | BE | QA | PO |
| Plans/subscriptions/credits/usage | DB | BE وQA | PO |
| Storage وRLS | DB | QA وBE | PO |
| إزالة BYOK وواجهة التوليد | FE | QA | PO |
| Tests وstaging وdeployment | QA | جميع الفريق | PO |
| قرار Beta والرسائل والـ limits | PO | جميع الفريق | PO |

**قاعدة المسؤولية:** الشخص الرئيسي مسؤول عن الكود والاختبارات الخاصة بتاسكه، والمراجع لا يصبح منفذًا بديلًا. أي task بلا test أو acceptance evidence لا تعتبر مكتملة.

## 6. الجدول الزمني المقترح لعشرة أيام

| اليوم | العمل الأساسي | بوابة الخروج |
|---:|---|---|
| 1 | S4-001، S4-002، بدء S4-010 وS4-020 | العقود والـ secrets ثابتة |
| 2 | S4-010، S4-011، S4-020، بدء S4-040 | managed resolver وschema أولي |
| 3 | S4-011، S4-021، S4-030، S4-040 | image request لا يحتاج BYOK |
| 4 | S4-012، S4-022، S4-031، S4-041 | صورة وكابشن managed في بيئة test |
| 5 | S4-013، S4-023، S4-032، S4-042 | quota/usage/UI contract متصل |
| 6 | S4-024، S4-043، S4-050، S4-051 | recovery والاختبارات الأساسية |
| 7 | إصلاحات backend/database/frontend، S4-052 | build/lint/tests تمر |
| 8 | S4-053 smoke test أول | قائمة failures معروفة |
| 9 | إصلاحات smoke test وإعادة الاختبار | critical blockers مغلقة |
| 10 | S4-054، توثيق، قرار release | Ready for Beta أو Blocked |

## 7. ما هو مسؤوليتك أنتِ تحديدًا

مسؤوليتك ليست كتابة كل الكود. مسؤوليتك هي منع الفريق من بناء شيء تقني يعمل لكنه لا يطابق المنتج. لذلك عليكِ تثبيت القرارات التالية في اليوم الأول: 10 credits شهريًا، credit واحد للصورة، الكابشن الأول ضمن العملية، عدم وجود دفع، provider واحد في Beta، ورسائل Beta.

بعد ذلك تراجعين العقود لا تفاصيل implementation: body التوليد لا يحتوي key/provider/model، endpoint الرصيد واضح، الصورة لا تعتمد على رابط provider، وفشل الكابشن لا يمسح الصورة. في نهاية السبرنت أنتِ تنفذين user acceptance كاملًا من متصفح جديد، وتقررين هل المسار جاهز للـ Beta أم لا.

### مهام PO المحددة

| المهمة | الوقت | التسليم |
|---|---:|---|
| تثبيت قرارات المنتج والـ limits | 3 ساعات | S4-001 مكتمل |
| كتابة/اعتماد النصوص العربية والإنجليزية | 2–3 ساعات | copy approved |
| مراجعة API contracts والـ error codes | 2 ساعات | contract sign-off |
| مراجعة UX بدون BYOK | 2 ساعات | no-BYOK checklist |
| تنفيذ smoke test كامل | 4–5 ساعات | acceptance evidence |
| مراجعة known issues وقرار الإصدار | 2–3 ساعات | release decision |
| **الإجمالي** | **15–18 ساعة** | موزعة على 10 أيام |

## 8. Dependencies التي يجب عدم كسرها

لا يبدأ FE بإزالة شرط المفتاح قبل أن يثبت BE managed endpoint في staging؛ وإلا ستصبح الواجهة تسمح بالتوليد بينما backend يرفضه. لا يبدأ usage خصم الرصيد قبل وجود generation ID وidempotency contract. لا يعلن QA نجاح الصورة قبل التأكد من أنها محفوظة في Storage. ولا يبدأ أي عمل على الدفع الآن، لأن ذلك خارج هدف السبرنت وسيزيد المخاطر دون فائدة مباشرة.

العقد المركزي هو: **managed provider → generation ID → reserve credit → provider call → storage → consume/release → usage record → response**. أي تغيير في هذه السلسلة يجب أن يراجعه BE وDB وQA معًا.

## 9. Definition of Done للسبرنت

تعتبر Sprint 4 منتهية فقط عندما يحقق النظام جميع النقاط التالية:

1. لا توجد واجهة لإضافة API key ولا اختيار BYOK.
2. التوليد يعمل بمفتاح backend فقط، ولا يظهر المفتاح في browser أو logs.
3. الخطة Beta والرصيد ظاهرين، وحدّ 10 image credits مطبق فعليًا.
4. reserve/consume/release وidempotency تمنع الخصم المكرر أو الرصيد السالب.
5. كل generation لها usage record، بما في ذلك الفشل.
6. الصور محفوظة في Storage مع signed URLs وownership صحيح.
7. caption محفوظ، قابل للنسخ والتعديل وإعادة التوليد دون إعادة توليد الصورة.
8. rate limit وgeneration lock موجودان.
9. اختبارات backend/database/frontend تمر.
10. smoke test كامل على staging ينجح.
11. لا يوجد checkout أو تحصيل دفع أو نص يوهم بأن الدفع مفعّل.
12. يوجد rollback واضح إذا فشل provider أو migration.

## 10. المخاطر والاحتياط

| الخطر | الاحتمال | الأثر | الإجراء |
|---|---:|---:|---|
| provider key صالح لكن الحساب بلا credits | متوسط | عالٍ | smoke check، error mapping، admin alert |
| فشل التخزين بعد نجاح provider | متوسط | عالٍ | لا تسجل success قبل storage، وتعامل مع cleanup |
| double-click يخصم مرتين | عالٍ | عالٍ | idempotency + lock |
| migration/RLS غير مطبقة على staging | متوسط | عالٍ | DB verification قبل E2E |
| حذف BYOK يكسر client قديم | متوسط | متوسط | 410 واضح أو backward-compatible window |
| اختلاف Arabic/English copy | منخفض | متوسط | PO يراجع النصوص قبل merge |
| توسع النطاق إلى Stripe | عالٍ | عالٍ | إبقاء الدفع خارج السبرنت رسميًا |
| استمرار processing بلا نهاية | متوسط | عالٍ | timeout + recovery |

## 11. قاعدة تقدير الوقت

هذه التقديرات تفترض أن authentication، brand CRUD، generation history، Supabase Storage، والـ provider adapters الحالية قابلة لإعادة الاستخدام. إذا ظهر أن provider نفسه لا يعمل بسبب model/account/endpoint، فهذا ليس task صغيرًا؛ يضاف **Spike مستقل من 4–8 ساعات** قبل مواصلة التنفيذ، ولا نخلط إصلاح provider مع تطوير quota حتى لا يصبح سبب التأخير غير واضح.
